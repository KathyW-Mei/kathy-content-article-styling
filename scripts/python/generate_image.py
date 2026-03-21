#!/usr/bin/env python3
"""
配图生成脚本 - 垫图模式 + Gemini 3 Pro

使用 google-genai SDK 调用 Gemini 3 Pro Image Preview
"""

import argparse
import base64
import json
import sys
import time
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types


# ============================================================
# 配置
# ============================================================

MODEL_ID = "gemini-3-pro-image-preview"
DEFAULT_TIMEOUT_MS = 120000
MAX_RETRIES = 3
RETRY_DELAYS = [30, 60, 120]
REQUEST_INTERVAL = 5

# Gemini API 支持的 aspect_ratio 值
# 完整列表: 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16
SUPPORTED_RATIOS = ["21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"]

# 非标准比例到支持比例的映射
RATIO_FALLBACK = {
    "2.35:1": "21:9",   # 微信公众号封面 → 21:9（最接近 2.33）
    "2:1": "16:9",      # 2:1 → 16:9
}

# 全局日志文件句柄
_log_file = None


# ============================================================
# 日志
# ============================================================

def init_log(log_path: Optional[Path]) -> None:
    """初始化日志文件"""
    global _log_file
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _log_file = open(log_path, "w", encoding="utf-8")


def close_log() -> None:
    """关闭日志文件"""
    global _log_file
    if _log_file:
        _log_file.close()
        _log_file = None


def log(message: str) -> None:
    """日志输出（同时写入 stderr 和日志文件）"""
    print(message, file=sys.stderr)
    if _log_file:
        _log_file.write(message + "\n")
        _log_file.flush()


# ============================================================
# 风格管理
# ============================================================

def load_styles(skill_dir: Path) -> dict:
    """加载风格索引"""
    styles_file = skill_dir / "reference" / "images" / "styles.json"
    return json.loads(styles_file.read_text(encoding="utf-8"))


def find_cover_style(styles_data: dict, style_id: str) -> Optional[dict]:
    """查找封面风格"""
    for style in styles_data.get("cover_styles", []):
        if style["id"] == style_id:
            return style
    return None


def find_main_style(styles_data: dict, style_id: str) -> Optional[dict]:
    """查找主图风格"""
    for style in styles_data.get("main_styles", []):
        if style["id"] == style_id:
            return style
    return None


def get_reference_image(skill_dir: Path, style: dict) -> Optional[Path]:
    """获取垫图路径"""
    filename = style.get("file")
    if not filename:
        return None
    image_path = skill_dir / "reference" / "images" / filename
    return image_path if image_path.exists() else None


# ============================================================
# Gemini 客户端
# ============================================================

def build_client(api_key: str, timeout_ms: int) -> genai.Client:
    """初始化 Gemini Client"""
    try:
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )
    except Exception:
        log("  ⚠ 未能设置超时参数，使用默认客户端")
        return genai.Client(api_key=api_key)


def resolution_to_size(resolution: str) -> str:
    """
    分辨率转换为 Gemini image_size

    Gemini 支持: 1K, 2K, 4K（必须大写）
    实际像素由 API 根据 aspect_ratio 自动计算
    """
    w = int(resolution.split("x")[0])
    if w >= 3000:
        return "4K"
    if w >= 2000:
        return "2K"
    return "1K"


def normalize_aspect_ratio(aspect: str) -> str:
    """
    将非标准比例映射到 Gemini 支持的比例

    Gemini API 支持: 1:1, 16:9, 9:16, 4:3, 3:4
    非标准比例（如 2.35:1）需要映射到最接近的支持值
    """
    if aspect in SUPPORTED_RATIOS:
        return aspect

    # 查找预定义映射
    if aspect in RATIO_FALLBACK:
        return RATIO_FALLBACK[aspect]

    # 动态计算最接近的支持比例
    try:
        parts = aspect.split(":")
        ratio = float(parts[0]) / float(parts[1])

        # 计算各支持比例的宽高比
        supported_values = {
            "21:9": 21/9,    # 2.33
            "16:9": 16/9,    # 1.78
            "3:2": 3/2,      # 1.50
            "4:3": 4/3,      # 1.33
            "5:4": 5/4,      # 1.25
            "1:1": 1.0,
            "4:5": 4/5,      # 0.80
            "3:4": 3/4,      # 0.75
            "2:3": 2/3,      # 0.67
            "9:16": 9/16,    # 0.56
        }

        # 找最接近的
        closest = min(supported_values.keys(),
                      key=lambda k: abs(supported_values[k] - ratio))
        return closest
    except (ValueError, ZeroDivisionError):
        return "16:9"  # 默认回退


# ============================================================
# 图像生成
# ============================================================

def get_language_constraint(language: str) -> str:
    """生成语言约束提示词"""
    if language == "zh":
        return """[LANGUAGE REQUIREMENT - CRITICAL]
If any text appears, it MUST be in Simplified Chinese (简体中文).
这是强制要求：
- 如需出现标题、标签、图标文字，必须是简体中文
- 禁止出现任何英文文字，除非是不可翻译的专有名词（如 API、URL）
- 即使专有名词也应尽量使用中文对应词
- 违反此规则将导致图片不可用
"""
    return """[LANGUAGE REQUIREMENT]
If any text appears, it MUST be in English.
- Titles, labels, and annotations must be in English
- Use clear, professional English terminology
"""


def generate_with_reference(
    client: genai.Client,
    ref_image_path: Path,
    topic: str,
    aspect_ratio: str,
    image_size: str,
    language: str = "zh",
    section_content: str = "",
    key_points: list[str] = None,
    visual_suggestion: str = ""
) -> Optional[bytes]:
    """使用垫图生成配图"""
    ref_bytes = ref_image_path.read_bytes()
    suffix = ref_image_path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"

    log(f"    [DEBUG] ref_path={ref_image_path}")
    log(f"    [DEBUG] ref_kb={len(ref_bytes) / 1024:.1f}")

    language_constraint = get_language_constraint(language)

    # 格式化 key_points
    key_points_formatted = ""
    if key_points:
        key_points_formatted = "\n".join(f"- {point}" for point in key_points)

    # 单一模板，动态追加非空字段
    prompt = f"""[CRITICAL INSTRUCTION]
The attached image is ONLY a VISUAL STYLE reference.
DO NOT copy any text, labels, topics, or subject matter from the reference image.
The reference image's content is COMPLETELY UNRELATED to what you need to create.

[WHAT TO LEARN FROM REFERENCE]
✓ Color palette and gradients
✓ Illustration technique (hand-drawn, flat, 3D, etc.)
✓ Layout structure and composition approach
✓ Visual decoration style (borders, backgrounds, icons aesthetic)

[WHAT TO IGNORE FROM REFERENCE]
✗ ALL text and labels in the reference
✗ The specific topic or subject matter
✗ Any domain-specific elements (finance, medical, etc.)

[YOUR ACTUAL TASK]
Create an illustration about: {topic}
"""
    if key_points_formatted:
        prompt += f"\nKey Points to visualize:\n{key_points_formatted}\n"

    if section_content:
        prompt += f"\nContent Summary:\n{section_content}\n"

    if visual_suggestion:
        prompt += f"\nVisual Direction:\n{visual_suggestion}\n"

    prompt += f"""
{language_constraint}

[OUTPUT REQUIREMENTS]
- Create a NEW illustration that matches the reference's VISUAL STYLE
- The content must be 100% about: {topic}
- Use visual metaphors appropriate for the article's technical topic
- Avoid text; if text is necessary, follow the language requirement
- No watermarks
- No photorealistic human faces
- Professional quality for article illustration
"""

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=image_size,
        ),
    )

    for attempt in range(MAX_RETRIES):
        try:
            log(f"    [GEN] attempt={attempt + 1}/{MAX_RETRIES} mode=reference")

            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[
                    types.Part.from_bytes(data=ref_bytes, mime_type=mime),
                    prompt
                ],
                config=config,
            )

            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        if part.inline_data.mime_type.startswith("image/"):
                            return part.inline_data.data

            log(f"    ✗ 响应中无图片数据")
            return None

        except Exception as e:
            error_msg = str(e)
            if "RATE_LIMIT" in error_msg or "429" in error_msg:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                log(f"    ⚠ 速率限制，等待 {delay}s...")
                time.sleep(delay)
                continue
            if "CONTENT_FILTERED" in error_msg or "safety" in error_msg.lower():
                log(f"    ✗ 内容被过滤")
                return None
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                log(f"    ⚠ 错误: {error_msg[:100]}，等待 {delay}s...")
                time.sleep(delay)
            else:
                log(f"    ✗ 生成失败: {error_msg[:100]}")
                return None

    return None


def generate_image(
    client: genai.Client,
    skill_dir: Path,
    style: dict,
    topic: str,
    platform: dict,
    language: str = "zh",
    section_content: str = "",
    key_points: list[str] = None,
    visual_suggestion: str = ""
) -> Optional[bytes]:
    """生成配图（垫图模式）"""
    ref_path = get_reference_image(skill_dir, style)
    raw_aspect = platform.get("aspect", "16:9")
    aspect_ratio = normalize_aspect_ratio(raw_aspect)
    resolution = platform.get("resolution", "1280x720")
    image_size = resolution_to_size(resolution)

    if not ref_path:
        log(f"  [ERROR] 无垫图，跳过生成")
        return None

    # 记录比例转换信息
    if raw_aspect != aspect_ratio:
        log(f"  [RATIO] {raw_aspect} → {aspect_ratio} (API 兼容转换)")
    log(f"  [MODE] reference_image={ref_path.name}")
    return generate_with_reference(
        client, ref_path, topic, aspect_ratio, image_size, language,
        section_content=section_content,
        key_points=key_points,
        visual_suggestion=visual_suggestion
    )


# ============================================================
# 凭证加载
# ============================================================

def load_api_key(skill_dir: Path) -> Optional[str]:
    """加载 Gemini API Key"""
    # 1. Skill 凭证目录
    cred_path = skill_dir / "credentials" / "gemini.json"
    if cred_path.exists():
        cred = json.loads(cred_path.read_text(encoding="utf-8"))
        api_key = cred.get("auth", {}).get("token") or cred.get("auth", {}).get("api_key")
        if api_key:
            return api_key

    return None


# ============================================================
# 主函数
# ============================================================

def main(run_dir: Path, skill_dir: Path) -> dict:
    """主函数"""
    try:
        run_name = run_dir.name
        log(f"[RUN] run_dir={run_dir}")
        # 1. 读取配置
        config_path = run_dir / "state" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        analysis_path = run_dir / "step02-analyze" / "analysis.json"
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))

        # 支持解耦的封面/主图风格
        params = config.get("params", {})
        cover_style_id = params.get("cover_style_id") or params.get("style_id")
        main_style_id = params.get("main_style_id") or params.get("style_id")
        language = analysis.get("metadata", {}).get("language", "zh")
        log(f"[INFO] run={run_name} cover_style={cover_style_id} main_style={main_style_id} language={language}")

        # 2. 加载风格
        styles_data = load_styles(skill_dir)
        defaults = styles_data.get("defaults", {})

        # 查找封面风格
        cover_style = find_cover_style(styles_data, cover_style_id)
        if not cover_style:
            default_cover = defaults.get("cover", "gradient-tech")
            cover_style = find_cover_style(styles_data, default_cover)
            if not cover_style:
                return {"ok": False, "err": f"Cover style not found: {cover_style_id}"}
            log(f"[WARN] 封面风格 {cover_style_id} 不存在，使用默认: {default_cover}")

        # 查找主图风格
        main_style = find_main_style(styles_data, main_style_id)
        if not main_style:
            default_main = defaults.get("main", "info-card")
            main_style = find_main_style(styles_data, default_main)
            if not main_style:
                return {"ok": False, "err": f"Main style not found: {main_style_id}"}
            log(f"[WARN] 主图风格 {main_style_id} 不存在，使用默认: {default_main}")

        log(f"[INFO] cover_style_id={cover_style['id']} cover_style_name={cover_style['name']}")
        log(f"[INFO] main_style_id={main_style['id']} main_style_name={main_style['name']}")

        # 2.1 校验参考图存在性（不做回退）
        cover_config = analysis.get("cover")
        if cover_config:
            cover_ref = get_reference_image(skill_dir, cover_style)
            if not cover_ref:
                return {"ok": False, "err": f"Missing cover reference image for style: {cover_style['id']}"}
        if analysis.get("illustrations"):
            main_ref = get_reference_image(skill_dir, main_style)
            if not main_ref:
                return {"ok": False, "err": f"Missing main reference image for style: {main_style['id']}"}

        # 3. 加载凭证
        api_key = load_api_key(skill_dir)
        if not api_key:
            return {"ok": False, "err": "No API key found"}

        client = build_client(api_key, DEFAULT_TIMEOUT_MS)
        log(f"[INFO] 模型: {MODEL_ID}")

        # 4. 创建输出目录
        output_dir = run_dir / "step03-generate"
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {"cover": None, "illustrations": []}

        # 5. 生成封面
        cover_config = analysis.get("cover")
        if cover_config:
            log(f"\n[COVER] run={run_name} topic={cover_config['topic']}")

            image_data = generate_image(
                client=client,
                skill_dir=skill_dir,
                style=cover_style,
                topic=cover_config["topic"],
                platform=cover_config["platform"],
                language=language,
                section_content=cover_config.get("section_content", ""),
                key_points=cover_config.get("key_points", []),
                visual_suggestion=cover_config.get("visual_suggestion", "")
            )

            if image_data:
                filename = "00-cover.png"
                output_path = output_dir / filename
                if isinstance(image_data, str):
                    image_data = base64.b64decode(image_data)
                output_path.write_bytes(image_data)
                results["cover"] = {"file": filename, "ok": True}
                log(f"  ✓ 保存: {filename} ({len(image_data) / 1024:.1f} KB)")
            else:
                results["cover"] = {"file": None, "ok": False, "err": "Generation failed"}
                log(f"  ✗ 封面生成失败")

            time.sleep(REQUEST_INTERVAL)

        # 6. 生成主图
        illustrations = analysis.get("illustrations", [])

        for illust in illustrations:
            idx = illust["index"]
            section_id = illust["section_id"]
            topic = illust["topic"]
            platform = illust["platform"]
            section_content = illust.get("section_content", "")
            key_points = illust.get("key_points", [])
            visual_suggestion = illust.get("visual_suggestion", "")

            log(f"\n[MAIN] run={run_name} index={idx}/{len(illustrations)} section_id={section_id} topic={topic}")
            if section_content:
                log(f"  [CONTEXT] section_content={section_content[:50]}...")
            if visual_suggestion:
                log(f"  [CONTEXT] visual_suggestion={visual_suggestion[:50]}...")

            image_data = generate_image(
                client=client,
                skill_dir=skill_dir,
                style=main_style,
                topic=topic,
                platform=platform,
                language=language,
                section_content=section_content,
                key_points=key_points,
                visual_suggestion=visual_suggestion
            )

            if image_data:
                filename = f"{idx:02d}-{section_id}.png"
                output_path = output_dir / filename
                if isinstance(image_data, str):
                    image_data = base64.b64decode(image_data)
                output_path.write_bytes(image_data)
                results["illustrations"].append({
                    "index": idx,
                    "file": filename,
                    "ok": True
                })
                log(f"  ✓ 保存: {filename} ({len(image_data) / 1024:.1f} KB)")
            else:
                results["illustrations"].append({
                    "index": idx,
                    "file": None,
                    "ok": False,
                    "err": "Generation failed"
                })
                log(f"  ✗ 主图 {idx} 生成失败")

            if idx < len(illustrations):
                time.sleep(REQUEST_INTERVAL)

        # 7. 统计结果
        cover_ok = 1 if results["cover"] and results["cover"]["ok"] else 0
        main_ok = sum(1 for r in results["illustrations"] if r["ok"])
        total = 1 + len(illustrations) if cover_config else len(illustrations)

        results["stats"] = {
            "total": total,
            "success": cover_ok + main_ok,
            "failed": total - cover_ok - main_ok
        }
        results["ok"] = True

        log(f"\n[DONE] 成功: {cover_ok + main_ok}/{total}")
        return results

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "err": str(e)[:200]}


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="配图生成脚本")
    parser.add_argument("--run-dir", type=Path, required=True, help="运行目录")
    parser.add_argument("--skill-dir", type=Path, required=True, help="Skill 目录")
    parser.add_argument("--log-file", type=Path, help="日志文件路径")
    args = parser.parse_args()

    # 初始化日志
    init_log(args.log_file)

    try:
        result = main(args.run_dir, args.skill_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        close_log()
