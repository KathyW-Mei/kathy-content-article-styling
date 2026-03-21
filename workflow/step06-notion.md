# Step 06: 发布到 Notion

## 概述

| 项目 | 内容 |
|------|------|
| **执行者** | Python 脚本 |
| **输入** | `step03-generate/*.png` + `output/*.md` |
| **输出** | Notion 页面（含嵌入图片） |

---

## 职责

1. 将 step03 生成的图片上传到 Discord CDN，获得公开图片 URL
2. 读取 output/ 下的文章 Markdown（已含图片占位符）
3. 在 Notion 数据库创建新页面，嵌入图片和文章正文

**依赖**：
- `credentials/notion.json`（Notion Integration Token + 数据库 ID）
- Discord Bot Token（读取自 `~/.openclaw/openclaw.json`，无需额外配置）
- `requests` 库（`pip3 install requests --break-system-packages`）

---

## 执行流程

### 1. 运行发布脚本

```bash
SKILL_DIR=$(python3 -c "import json; print(json.load(open('$RUN_DIR/state/config.json'))['directories']['skill_dir'])")

python3 \
  "$SKILL_DIR/scripts/python/publish_to_notion.py" \
  --run-dir "$RUN_DIR" \
  --skill-dir "$SKILL_DIR"
```

### 2. 脚本逻辑

#### 2.1 上传图片到 Discord CDN

```python
# 从 openclaw.json 读取 Bot Token
# 上传每张 PNG 到 xhs 频道
# 返回 https://cdn.discordapp.com/attachments/... 格式的公开 URL
```

#### 2.2 Markdown → Notion 块

- `# 标题` → heading_1
- `## 标题` → heading_2
- `### 标题` → heading_3
- `![alt](img.png)` → image block（URL 替换为 CDN 链接）
- `---` → divider
- 普通文本 → paragraph

#### 2.3 创建 Notion 页面

写入数据库「1、小红书笔记人工智能」：
- `标题` 字段：文章标题
- `笔记内容` 字段：纯文本摘要（前 2000 字）
- 页面 body：完整文章 + 嵌入图片

---

## 脚本输出（stdout JSON）

```json
{
  "ok": true,
  "notion_url": "https://www.notion.so/xxx",
  "total_images": 6,
  "uploaded_images": 6
}
```

---

## 前置条件

step05-insert.md 已运行，`{run_dir}/output/*.md` 存在。
若 output/ 为空，脚本自动回退到原始文档路径。

---

## 错误处理

| 错误 | 处理 |
|------|------|
| Discord 上传失败 | 记录错误，继续处理其余图片 |
| Notion Token 无效 | 报错退出 |
| 数据库未授权 | 提示用户在 Notion 给 Integration 添加权限 |
| requests 未安装 | `pip3 install requests --break-system-packages` |

---

## 输出

| 内容 | 位置 |
|------|------|
| Discord CDN URL 记录 | `{run_dir}/step04-upload/urls.json` |
| Notion 页面 | 数据库「1、小红书笔记人工智能」 |

---

## 进度更新

更新 `state/progress.json`：

```json
{
  "step": 6,
  "checkpoint": "6b",
  "status": "published",
  "notion_url": "https://www.notion.so/xxx",
  "updated_at": "2026-01-29T10:30:00Z",
  "recovery_hint": "流程完成，Notion 页面已创建"
}
```

---

## 验证检查点

| 编号 | 检查项 | 通过标准 |
|------|--------|----------|
| 6a | 图片上传 | `urls.json` success > 0 |
| 6b | Notion 页面创建 | stdout 包含 `notion_url` |

---

## 下一步

在 Notion 审阅文章 → 手动搬运到小红书（复制文字 + 下载图片上传）
