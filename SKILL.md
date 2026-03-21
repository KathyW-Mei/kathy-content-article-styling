---
name: xiangyu-content-article-styling
description: 为 Markdown 文档生成 AI 风格配图（封面+主图），垫图模式。适用于文章添加插图，或当用户说「配图」「垫图」时
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
---

# 文章风格配图

> 垫图模式 · 多平台适配 · 三模式云存储（COS/R2/本地）

---

## 触发条件

| 关键词 | 动作 |
|--------|------|
| 「配图」「垫图」 | 执行完整配图流程 |
| 「文章配图」「添加插图」 | 执行完整配图流程 |

## 执行模式

| 选项 | 说明 |
|------|------|
| ✅ 自动执行 | 触发后自动执行全流程，完成后报告结果 |

## 执行规范（必须遵守）

1. **先读后做**：执行 Step N 前，先 Read `workflow/stepNN-*.md`
2. **逐步执行**：按 01→02→03→04→05 顺序，不跳步
3. **脚本优先**：Gemini 调用使用 `scripts/python/*.py`
4. **进度持久化**：维护 `state/config.json` + `state/progress.json`

---

## 工作流（5 步）

| Step | 职责 | 执行者 | 文档 | 输入 | 输出 |
|------|------|--------|------|------|------|
| 01 | 初始化 | 主 Agent | `workflow/step01-init.md` | 用户触发 | `state/config.json` + `state/progress.json` |
| 02 | 分析文档 | 主 Agent | `workflow/step02-analyze.md` | 配置 + 文档 | `step02-analyze/analysis.json` |
| 03 | 配图生成 | 脚本 | `workflow/step03-generate.md` | analysis.json + 垫图 | `step03-generate/*.png` |
| 04 | 图片上传 | 脚本 | `workflow/step04-upload.md` | *.png + storage_mode | `step04-upload/urls.json` |
| 05 | 插入文档 | 主 Agent | `workflow/step05-insert.md` | urls.json | `output/{doc}.md` |

---

## 数据流

### 第一阶段：初始化

```
用户输入
    ↓ Step 01: 初始化
state/
├── config.json
└── progress.json
```

### 第二阶段：分析与生成

```
state/config.json
    ↓ Step 02: 分析文档
step02-analyze/
└── analysis.json
    ↓ Step 03: 生成配图
step03-generate/
├── 00-cover.png
└── 01-*.png
```

### 第三阶段：上传与写回

```
step03-generate/
    ↓ Step 04: R2 上传
step04-upload/
└── urls.json
    ↓ Step 05: 插入文档
output/
└── {doc}.md
```

---

## 上下文管理

| 规则 | 说明 |
|------|------|
| 最小读取 | 主 Agent 仅读取配置与必要输入文件 |
| 脚本优先 | 确定性操作全部交给脚本 |
| 进度可恢复 | `state/progress.json` 持久化 checkpoint |

---

## 存储模式

| 模式 | 说明 | 输出 URL 格式 | 适用场景 |
|------|------|--------------|----------|
| `canvas` | OpenClaw 内置（默认） | `https://kathy.zeabur.app/__openclaw__/canvas/images/xxx.png` | OpenClaw/Zeabur 部署 |
| `cos` | 腾讯云 COS | `https://bucket.cos.region.myqcloud.com/images/xxx.png` | 国内访问快 |
| `r2` | Cloudflare R2 | `https://pub-xxx.r2.dev/images/xxx.png` | 全球 CDN 加速 |
| `local` | 本地存储 | `./images/xxx.png` | 离线使用、本地预览 |

---

## 内置风格

### 封面风格（cover_styles）

| ID | 名称 | 适用场景 |
|----|------|---------|
| gradient-tech | 渐变科技 | 科技产品、AI 主题 |
| news-press | 新闻报刊 | 新闻资讯、时事评论 |
| notebook-doodle | 笔记本涂鸦 | 教程、攻略 |
| sketch-doodle | 简笔涂鸦 | 小红书、轻松教程 |

### 主图风格（main_styles）

| ID | 名称 | 适用场景 |
|----|------|---------|
| info-card | 信息卡片 | 介绍性文章、人物专访 |
| knowledge-theory | 知识理论 | 学术科普、传播学/心理学 |
| infographic | 信息图表 | 数据分析、政策解读 |
| gradient-tech | 渐变科技 | 科技产品、AI 主题 |
| edu-illustration | 科普插画 | 教育、学科知识 |
| notebook-doodle | 笔记本涂鸦 | 教程、攻略 |
| sketch-doodle | 简笔涂鸦 | 小红书、轻松教程 |

---

## 平台规格

| 平台 | 封面比例 | 封面分辨率 | 主图比例 | 主图分辨率 |
|------|----------|-----------|----------|-----------|
| X/Twitter | 21:9 | 1890×810 | 16:9 | 1280×720 |
| 微信公众号 | 21:9 | 1890×810 | 16:9 | 1280×720 |
| 小红书 | 3:4 | 1080×1440 | 3:4 | 1080×1440 |
| 抖音 | 9:16 | 1080×1920 | 9:16 | 1080×1920 |

> **注**：21:9 (2.33) 是 Gemini 3 Pro 支持的最宽比例，接近微信公众号 2.35:1 需求，避免封面文字被裁切

---

## 垫图管理

### 目录结构

```
reference/images/
├── styles.json              # 风格索引
├── cover-gradient-tech.png  # 封面垫图
├── cover-news-press.png
├── cover-notebook-doodle.jpg
├── cover-sketch-doodle.jpg
├── main-info-card.jpg       # 主图垫图
├── main-knowledge-theory.jpg
├── main-infographic.jpg
├── main-gradient-tech.jpg
├── main-edu-illustration.jpg
├── main-notebook-doodle.png
└── main-sketch-doodle.jpg
```

### styles.json 结构

```json
{
  "cover_styles": [
    {"id": "gradient-tech", "name": "渐变科技", "file": "cover-gradient-tech.png"}
  ],
  "main_styles": [
    {"id": "info-card", "name": "信息卡片", "file": "main-info-card.jpg"}
  ],
  "defaults": {
    "cover": "gradient-tech",
    "main": "info-card"
  }
}
```

### 添加新风格

1. 将垫图放入 `reference/images/` 目录（PNG/JPG）
2. 更新 `styles.json`：
   - 封面风格 → `cover_styles`
   - 主图风格 → `main_styles`

### 命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 封面 | `cover-{style-id}.{ext}` | `cover-gradient-tech.png` |
| 主图 | `main-{style-id}.{ext}` | `main-info-card.jpg` |

---

## 输出目录

```
{skill_dir}/runs/{keyword}-{YYYYMMDD-HHmmss}/
├── state/config.json
├── state/progress.json
├── step02-analyze/analysis.json
├── step03-generate/
│   ├── 00-cover.png
│   ├── 01-*.png
│   └── ...
├── step04-upload/urls.json
└── output/{doc}.md
```

---

## 参考资料

| 文件 | 路径 | 用途 |
|------|------|------|
| 风格索引 | `reference/images/styles.json` | 风格配置 |
| 平台规格 | `reference/definitions/platforms.json` | 平台分辨率 |
| 垫图库 | `reference/images/*.{png,jpg}` | 风格参考图 |
| 生成脚本 | `scripts/python/generate_image.py` | 核心生成逻辑 |
| 路由脚本 | `scripts/shell/upload-router.sh` | 统一上传入口 |
| COS 上传 | `scripts/shell/upload-to-cos.sh` | 腾讯云 COS 上传 |
| R2 上传 | `scripts/shell/upload-to-r2.sh` | Cloudflare R2 上传 |

---

## 凭证

| 凭证文件 | 用途 | 必须 |
|----------|------|------|
| `credentials/gemini.json` | Gemini API 调用 | ✅ |
| `credentials/cos.json` | 腾讯云 COS 上传 | COS 模式必须 |
| `credentials/r2.json` | Cloudflare R2 上传 | R2 模式必须 |
