# Step 04: 图片上传

## 概述

| 项目 | 内容 |
|------|------|
| **执行者** | Shell 脚本 |
| **输入** | `step03-generate/*.png` |
| **输出** | `step04-upload/urls.json` |

---

## 职责

根据存储模式，将生成的 PNG 文件上传到指定位置。

**支持四种存储模式**：

| 模式 | 说明 | 输出 URL 格式 |
|------|------|--------------|
| `canvas` | OpenClaw 内置画布（Zeabur 部署推荐） | `https://kathy.zeabur.app/__openclaw__/canvas/images/xxx.png` |
| `cos` | 腾讯云 COS | `https://bucket.cos.region.myqcloud.com/images/xxx.png` |
| `r2` | Cloudflare R2 | `https://pub-xxx.r2.dev/images/xxx.png` |
| `local` | 本地存储 | `./images/xxx.png` |

**依赖**：
- `canvas`：无需凭证，OpenClaw 自带（**Zeabur 部署默认**）
- `credentials/cos.json`（COS 模式）
- `credentials/r2.json`（R2 模式）
- `jq`

---

## 执行流程

### 1. 读取存储模式

```bash
export RUN_DIR
KEYWORD=$(jq -r '.document.keyword' "$RUN_DIR/state/config.json")
STORAGE_MODE=$(jq -r '.params.storage_mode' "$RUN_DIR/state/config.json")
RUN_NAME=$(basename "$RUN_DIR")
OUTPUT_DIR="$RUN_DIR/output"
```

### 2a. canvas 模式（OpenClaw/Zeabur 默认）

```bash
CANVAS_DIR="/home/node/.openclaw/canvas/images/${RUN_NAME}"
mkdir -p "$CANVAS_DIR"

for png in "$RUN_DIR"/step03-generate/*.png; do
  filename=$(basename "$png")
  cp "$png" "$CANVAS_DIR/$filename"
  echo "$filename -> https://kathy.zeabur.app/__openclaw__/canvas/images/${RUN_NAME}/$filename"
done
```

### 2b. COS/R2 模式

**注意**：Shell 脚本统一用 `bash` 前缀调用，避免文件权限问题。

```bash
SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/workspace-xhs/skills/kathy-content-article-styling}"
declare -A URLS

for png in "$RUN_DIR"/step03-generate/*.png; do
  filename=$(basename "$png")
  target_filename="doc-style-${KEYWORD}-${filename}"

  url=$(bash "$SKILL_DIR/scripts/shell/upload-router.sh" \
    "$STORAGE_MODE" \
    "$png" \
    "$target_filename" \
    "$OUTPUT_DIR")

  URLS["$filename"]="$url"
  echo "$filename -> $url"
done
```

### 3. 记录 URL 映射

创建 `step04-upload/urls.json`：

```json
{
  "storage_mode": "cos",
  "uploads": [
    {
      "local": "01-overview.png",
      "target_filename": "doc-style-ai-tools-01-overview.png",
      "url": "https://<COS_BUCKET_HOST>/images/doc-style-ai-tools-01-overview.png"
    },
    {
      "local": "02-workflow.png",
      "target_filename": "doc-style-ai-tools-02-workflow.png",
      "url": "https://<COS_BUCKET_HOST>/images/doc-style-ai-tools-02-workflow.png"
    }
  ],
  "uploaded_at": "2026-01-29T10:20:00Z",
  "total": 5,
  "success": 5
}
```

**本地模式示例**：

```json
{
  "storage_mode": "local",
  "uploads": [
    {
      "local": "01-overview.png",
      "target_filename": "doc-style-ai-tools-01-overview.png",
      "url": "./images/doc-style-ai-tools-01-overview.png"
    }
  ],
  "uploaded_at": "2026-01-29T10:20:00Z",
  "total": 5,
  "success": 5
}
```

---

## 错误处理

| 错误 | 处理 |
|------|------|
| COS/R2 上传失败 | 重试 3 次 |
| 文件不存在 | 跳过并记录 |
| 签名失败 | 重新生成时间戳 |
| 未知存储模式 | 报错退出 |

---

## 输出

| 文件 | 路径 | 内容 |
|------|------|------|
| URL 映射 | `{run_dir}/step04-upload/urls.json` | 图片 URL 记录 |
| 本地图片 | `{run_dir}/output/images/*.png` | 仅 local 模式 |

---

## 进度更新

更新 `state/progress.json`：

```json
{
  "step": 4,
  "checkpoint": "4b",
  "status": "uploaded",
  "storage_mode": "cos",
  "updated_at": "2026-01-29T10:20:00Z",
  "recovery_hint": "继续 Step 05 插入文档"
}
```

---

## 验证检查点

| 编号 | 检查项 | 通过标准 |
|------|--------|----------|
| 4a | urls.json 写入 | 文件存在且 JSON 可解析 |
| 4b | 上传成功数 | success == total |
| 4c | URL 可用 | 公开链接非空（云存储）/ 相对路径存在（本地） |

---

## 下一步

执行 `workflow/step05-insert.md`
