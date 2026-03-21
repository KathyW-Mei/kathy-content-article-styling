# Step 01: 初始化

## 概述

| 项目 | 内容 |
|------|------|
| **执行者** | 主 Agent |
| **输入** | 用户触发 + 参数收集 |
| **输出** | `state/config.json` + 运行目录 |

---

## 职责

收集用户输入，创建运行目录，初始化配置。

---

## 执行流程

### 1. 询问参数（封面/主图风格解耦）

使用 `AskUserQuestion` 收集参数。**注意**：封面风格和主图风格独立选择。

**第一轮询问**（5 个问题）：

```json
{
  "questions": [
    {
      "header": "文章路径",
      "question": "要配图的文章路径是？",
      "multiSelect": false,
      "options": [
        {"label": "输入完整路径 (Recommended)", "description": "如 /Users/xxx/article.md，或直接拖拽文件"},
        {"label": "当前目录 README.md", "description": "示例路径"}
      ]
    },
    {
      "header": "目标平台",
      "question": "发布到哪个平台？",
      "multiSelect": false,
      "options": [
        {"label": "X / Twitter (Recommended)", "description": "封面 16:9，主图 16:9"},
        {"label": "微信公众号", "description": "封面 2.35:1，主图 16:9"},
        {"label": "小红书", "description": "封面 3:4，主图 3:4"},
        {"label": "抖音", "description": "封面 9:16，主图 9:16"}
      ]
    },
    {
      "header": "主图数量",
      "question": "需要生成多少张主图？",
      "multiSelect": false,
      "options": [
        {"label": "3 张 (Recommended)", "description": "标准配置，覆盖核心章节"},
        {"label": "5 张", "description": "丰富配置"},
        {"label": "8 张", "description": "完整配置"},
        {"label": "auto", "description": "根据文章结构自动决定"}
      ]
    },
    {
      "header": "封面风格",
      "question": "选择封面风格？（输入编号如 cover5 可选更多风格）",
      "multiSelect": false,
      "options": [
        {"label": "[cover1] 渐变科技 (Recommended)", "description": "蓝紫渐变、3D 玻璃质感，适合科技产品/AI 主题"},
        {"label": "[cover2] 新闻报刊", "description": "报纸版式、红黑配色，适合新闻资讯"},
        {"label": "[cover3] 笔记本涂鸦", "description": "线圈本背景、彩色手写字，适合教程/攻略"},
        {"label": "[cover4] 简笔涂鸦", "description": "手绘简笔画、黄色高亮，适合小红书/教程类"}
      ]
    },
    {
      "header": "存储模式",
      "question": "图片上传到哪里？",
      "multiSelect": false,
      "options": [
        {"label": "OpenClaw Canvas (Recommended)", "description": "OpenClaw 内置存储，Zeabur 部署无需额外配置"},
        {"label": "腾讯云 COS", "description": "国内访问快"},
        {"label": "R2 云存储", "description": "Cloudflare R2，全球 CDN 加速"},
        {"label": "本地存储", "description": "不上传，图片存放在输出目录"}
      ]
    }
  ]
}
```

**第二轮询问**（主图风格）：

```json
{
  "questions": [
    {
      "header": "主图风格",
      "question": "选择主图风格？（输入编号如 main5 可选更多风格）",
      "multiSelect": false,
      "options": [
        {"label": "[main1] 信息卡片 (Recommended)", "description": "卡片式布局、中央人物、周围信息块，适合介绍性文章"},
        {"label": "[main2] 知识理论", "description": "传播学/心理学理论可视化，螺旋/漏斗结构，适合学术科普"},
        {"label": "[main3] 信息图表", "description": "知识图谱、流程可视化，适合数据分析和政策解读"},
        {"label": "[main4] 渐变科技", "description": "蓝紫渐变、3D 玻璃质感，适合科技产品/AI 主题"}
      ]
    }
  ]
}
```

**动态风格选项**：
- 从 `reference/images/styles.json` 读取 `cover_styles` 和 `main_styles`
- 封面风格只显示 `cover_styles` 数组中的选项
- 主图风格只显示 `main_styles` 数组中的选项
- 检查每个风格的垫图文件是否存在

### 2. 解析用户答案

| 选项 | 映射值 |
|------|--------|
| "X / Twitter" | `platform: "x"` |
| "微信公众号" | `platform: "wechat"` |
| "小红书" | `platform: "xiaohongshu"` |
| "抖音" | `platform: "douyin"` |
| "3 张" | `main_count: 3` |
| "5 张" | `main_count: 5` |
| "8 张" | `main_count: 8` |
| "auto" | `main_count: "auto"` |
| **封面风格** | |
| "[cover1] 渐变科技" | `cover_style_id: "gradient-tech"` |
| "[cover2] 新闻报刊" | `cover_style_id: "news-press"` |
| "[cover3] 笔记本涂鸦" | `cover_style_id: "notebook-doodle"` |
| "[cover4] 简笔涂鸦" | `cover_style_id: "sketch-doodle"` |
| "[cover5] 暖色3D" | `cover_style_id: "warm-3d"` |
| "[cover6] 漫画黄" | `cover_style_id: "comic-yellow"` |
| **主图风格** | |
| "[main1] 信息卡片" | `main_style_id: "info-card"` |
| "[main2] 知识理论" | `main_style_id: "knowledge-theory"` |
| "[main3] 信息图表" | `main_style_id: "infographic"` |
| "[main4] 渐变科技" | `main_style_id: "gradient-tech"` |
| "[main5] 科普插画" | `main_style_id: "edu-illustration"` |
| "[main6] 笔记本涂鸦" | `main_style_id: "notebook-doodle"` |
| "[main7] 简笔涂鸦" | `main_style_id: "sketch-doodle"` |
| "[main8] 水彩手帐" | `main_style_id: "watercolor-journal"` |
| **存储模式** | |
| "OpenClaw Canvas" | `storage_mode: "canvas"` |
| "腾讯云 COS" | `storage_mode: "cos"` |
| "R2 云存储" | `storage_mode: "r2"` |
| "本地存储" | `storage_mode: "local"` |

### 3. 验证文档

```bash
# 检查文件存在且为 Markdown
if [ -f "$DOC_PATH" ] && [[ "$DOC_PATH" == *.md ]]; then
  echo "文档验证通过"
fi
```

### 4. 生成 keyword

从文档标题或一级标题提取 keyword：

1. 读取文档第一个 `# ` 标题
2. 提取核心词汇
3. 转为英文 slug（小写、连字符分隔）
4. 限制 20 字符

### 5. 创建运行目录

```bash
# 自动检测运行环境，确定 SKILL_DIR
if [ -d "/home/node/.openclaw" ]; then
  # OpenClaw/Zeabur 环境：找当前 agent workspace 下的 skill
  SKILL_DIR=$(find /home/node/.openclaw/workspace-*/skills/kathy-content-article-styling -maxdepth 0 -type d 2>/dev/null | head -1)
else
  # Claude Code 本地环境
  SKILL_DIR="$HOME/.claude/skills/xiangyu-content-article-styling"
fi

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RUN_DIR="$SKILL_DIR/runs/${KEYWORD}-${TIMESTAMP}"

mkdir -p "$RUN_DIR"/{state,step02-analyze,step03-generate,step04-upload,output}
```

### 6. 加载平台配置

从 `reference/definitions/platforms.json` 读取平台规格：

```python
platform_config = platforms[platform_id]
# 例如 platform_id = "x"
# platform_config = {
#   "name": "X/Twitter",
#   "cover": {"aspect": "16:9", "resolution": "1600x900"},
#   "main": {"aspect": "16:9", "resolution": "1280x720"}
# }
```

### 7. 保存配置

写入 `state/config.json`：

```json
{
  "document": {
    "path": "/absolute/path/to/doc.md",
    "title": "文档标题",
    "keyword": "doc-keyword"
  },
  "params": {
    "platform": "x",
    "main_count": 3,
    "cover_style_id": "gradient-tech",
    "main_style_id": "info-card",
    "storage_mode": "canvas"
  },
  "platform": {
    "name": "X/Twitter",
    "cover": {"aspect": "16:9", "resolution": "1600x900"},
    "main": {"aspect": "16:9", "resolution": "1280x720"}
  },
  "directories": {
    "run_dir": "/path/to/runs/keyword-timestamp",
    "skill_dir": "/home/node/.openclaw/workspace-xhs/skills/kathy-content-article-styling"
  },
  "created_at": "2026-01-29T10:00:00Z"
}
```

---

## 输出

| 文件 | 路径 | 内容 |
|------|------|------|
| 配置文件 | `{run_dir}/state/config.json` | 运行配置 |
| 进度文件 | `{run_dir}/state/progress.json` | 断点恢复 |

---

## 进度文件初始化

写入 `state/progress.json`：

```json
{
  "step": 1,
  "checkpoint": "1c",
  "status": "initialized",
  "run_dir": "/path/to/runs/keyword-timestamp",
  "updated_at": "2026-01-29T10:00:00Z",
  "recovery_hint": "重新读取 config.json 并继续 Step 02"
}
```

---

## 验证检查点

| 编号 | 检查项 | 通过标准 |
|------|--------|----------|
| 1a | 运行目录创建 | `{run_dir}/` 存在 |
| 1b | config.json 写入 | 文件存在且 JSON 可解析 |
| 1c | progress.json 初始化 | 文件存在且包含 recovery_hint |

---

## 下一步

执行 `workflow/step02-analyze.md`
