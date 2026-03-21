# Step 03: 配图生成

## 概述

| 项目 | 内容 |
|------|------|
| **执行者** | Python 脚本 |
| **输入** | `step02-analyze/analysis.json` + 风格垫图 |
| **输出** | `step03-generate/*.png` |

---

## 职责

调用 Gemini 图像生成 API，使用垫图模式生成风格一致的封面和主图。

---

## 核心逻辑：垫图 + 内容 → Gemini

---

## 执行流程

### 1. 运行生成脚本

**注意**：Shell 脚本统一用 `bash` 前缀调用，避免文件权限问题。

```bash
SKILL_DIR="$HOME/.claude/skills/xiangyu-content-article-styling"
mkdir -p "$RUN_DIR/logs"

# 用 bash 前缀调用，避免权限问题
bash "$SKILL_DIR/scripts/shell/precheck.sh" "$RUN_DIR"

"$SKILL_DIR/scripts/python/.venv/bin/python" \
  "$SKILL_DIR/scripts/python/generate_image.py" \
  --run-dir "$RUN_DIR" \
  --skill-dir "$SKILL_DIR" \
  --log-file "$RUN_DIR/logs/generate.log"
```

### 1.1 日志输出

日志同时写入 stderr 和 `{run_dir}/logs/generate.log`，包含：
- 垫图调试信息：路径、大小、MIME 类型
- 生成状态：每张图片的尝试次数和结果
- 错误详情：API 错误、超时、内容过滤等

### 2. 脚本逻辑

#### 2.1 加载垫图

```python
def get_reference_image(style_id: str, image_type: str) -> Path | None:
    """
    style_id: "gradient-tech" | "info-card"
    image_type: "cover" | "main"
    返回: reference/images/{file}
    """
    styles = load_styles()
    if image_type == "cover":
        style = find_cover_style(styles, style_id)
    else:
        style = find_main_style(styles, style_id)
    if not style:
        return None
    filename = style["file"]
    image_path = skill_dir / "reference" / "images" / filename
    return image_path if image_path.exists() else None
```

#### 2.2 垫图模式生成

```python
def generate_with_style(
    style_id: str,
    image_type: str,  # "cover" | "main"
    topic: str,
    context: str,
    platform: dict  # {"aspect": "16:9", "resolution": "1600x900"}
) -> bytes | None:
    """使用垫图生成风格一致的配图"""

    # 1. 加载参考图
    ref_image_path = get_reference_image(style_id, image_type)

    if ref_image_path:
        ref_image_b64 = load_image_base64(ref_image_path)

        # 2. 构建提示词
        prompt = f"""
[STYLE REFERENCE]
Use the attached image as the primary style reference.
Match its visual style, color palette, composition approach, and illustration technique.

[CONTENT TO ILLUSTRATE]
Topic: {topic}
Context: {context}

[REQUIREMENTS]
- Generate a NEW illustration that matches the reference style
- Adapt the content to show: {topic}
- Keep the same level of detail, color harmony, and visual language
- The result should look like it belongs to the same series as the reference

[TECHNICAL]
Aspect ratio: {platform['aspect']}
Resolution: {platform['resolution']}

[CONSTRAINTS]
- No text or watermarks in the image
- No photorealistic human faces
- Professional quality suitable for article illustration
"""

        # 3. 调用 Gemini（垫图 + 提示词）
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[
                {"inline_data": {"mime_type": "image/png", "data": ref_image_b64}},
                {"text": prompt}
            ],
            config={"response_modalities": ["IMAGE"]}
        )
    else:
        raise RuntimeError("Reference image missing; stop and fix style assets.")
```

### 3. 生成顺序

1. **封面**：使用 `cover_style_id` 对应的 `cover_styles[].file`
2. **主图 1-N**：使用 `main_style_id` 对应的 `main_styles[].file`

### 4. 输出文件

```
step03-generate/
├── 00-cover.png           # 封面
├── 01-installation.png    # 主图 1
├── 02-core-features.png   # 主图 2
└── 03-best-practices.png  # 主图 3
```

### 5. 结果 JSON

脚本输出 JSON 格式结果到 stdout：

```json
{
  "ok": true,
  "cover": {
    "file": "00-cover.png",
    "ok": true
  },
  "illustrations": [
    {"index": 1, "file": "01-installation.png", "ok": true},
    {"index": 2, "file": "02-core-features.png", "ok": true},
    {"index": 3, "file": "03-best-practices.png", "ok": true}
  ],
  "stats": {
    "total": 4,
    "success": 4,
    "failed": 0
  }
}
```

---

## 模型选择

| 模型 | ID | 说明 |
|------|-----|------|
| Pro | gemini-3-pro-image-preview | 高质量图像生成，支持垫图 |

---

## 失败处理提示

- 若结果 `success < total`，提示用户是否重试失败项（只重试失败图片）。

---

## 错误处理

| 错误 | 处理 |
|------|------|
| 垫图不存在 | 回退到纯提示词模式 |
| API 调用失败 | 重试 3 次 |
| 图像生成失败 | 记录错误，继续下一张 |
| 超时 | 120 秒超时，标记失败 |

---

## 输出

| 文件 | 路径 | 内容 |
|------|------|------|
| 封面 | `{run_dir}/step03-generate/00-cover.png` | 封面配图 |
| 主图 | `{run_dir}/step03-generate/NN-*.png` | 主图配图 |

---

## 进度更新

更新 `state/progress.json`：

```json
{
  "step": 3,
  "checkpoint": "3b",
  "status": "generated",
  "updated_at": "2026-01-29T10:12:00Z",
  "recovery_hint": "继续 Step 04 上传到 R2"
}
```

---

## 验证检查点

| 编号 | 检查项 | 通过标准 |
|------|--------|----------|
| 3a | 封面生成 | `00-cover.png` 存在或明确失败记录 |
| 3b | 主图生成 | 输出数量与 `analysis.json` 一致 |
| 3c | 日志写入 | `{run_dir}/logs/generate.log` 存在 |

---

## 下一步

执行 `workflow/step04-upload.md`
