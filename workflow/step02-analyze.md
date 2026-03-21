# Step 02: 分析文档

## 概述

| 项目 | 内容 |
|------|------|
| **执行者** | 主 Agent |
| **输入** | `state/config.json` + Markdown 文档 |
| **输出** | `step02-analyze/analysis.json` |

---

## 职责

分析 Markdown 文档结构，确定封面主题和主图配图位置。

---

## 执行流程

### 1. 读取配置

```python
config = json.loads(config_path.read_text())
doc_path = config["document"]["path"]
main_count = config["params"]["main_count"]
cover_style_id = config["params"]["cover_style_id"]
main_style_id = config["params"]["main_style_id"]
platform = config["platform"]
```

### 2. 读取文档

使用 Read 工具读取完整文档内容。

### 3. 检测文章语言

**重要**：根据文档内容自动检测语言，确保生成图片的文字与文章语言一致。

检测方法：

```python
# 统计中文字符占比
chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
total_chars = len(content.replace(' ', '').replace('\n', ''))
chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0

# 判定规则：中文字符 > 30% 则为中文文档
language = "zh" if chinese_ratio > 0.3 else "en"
```

将语言存入 `metadata.language` 字段。

### 4. 分析文档结构

提取以下信息：

- **标题层级**：`#`、`##`、`###`
- **章节内容**：每个标题下的正文
- **关键概念**：技术术语、流程、架构
- **专有名词**：提取文章中的专有名词（如 Linter、Healer、单兵模式等）

### 5. 确定主图数量

如果 `main_count == "auto"`：

| 章节数 | 主图数 |
|--------|--------|
| ≤ 3 | 2 张 |
| 4-6 | 3 张 |
| 7-10 | 5 张 |
| > 10 | 8 张 |

### 6. 封面分析

**重要**：封面 topic 必须使用文章标题（与文章语言一致）。

提取全文核心主题，生成封面配置：

```json
{
  "type": "cover",
  "topic": "Claude Code 代码医疗系统",
  "focal_point": "AI 驱动的代码诊断与修复",
  "style_id": "gradient-tech",
  "reference_image": "cover-gradient-tech.png",
  "platform": {
    "aspect": "16:9",
    "resolution": "1600x900"
  }
}
```

封面 topic 规则：
- 中文文章 → 使用文章标题（中文）
- 英文文章 → 使用文章标题（英文）
- `style_id` 使用 `config.params.cover_style_id`
- `reference_image` 使用对应封面风格的 `file` 字段

### 7. 主图分析

根据 `main_count` 智能分配：

| 数量 | 分配策略 |
|------|----------|
| 2 | 开头概览 + 总结 |
| 3 | 开头概览 + 核心章节 + 总结 |
| 5 | 每个一级标题下放 1 张 |
| 8 | 每个二级标题下放 1 张 |

### 8. 生成配图主题

**重要**：topic 和 context 必须使用与文章相同的语言。

每个主图位置生成：

- **type**：`"main"`
- **topic**：配图主题（与文章语言一致，中文文章用中文）
- **context**：上下文摘要（包含章节关键术语和专有名词）
- **section_content**：章节原文摘要（100-200 字，提取该章节核心内容）
- **key_points**：该章节的核心要点列表（3-5 个要点）
- **visual_suggestion**：建议的视觉元素（图标、场景、隐喻，指导图像生成）
- **section_id**：章节标识（用于文件命名）
- **insert_after_line**：插入位置（行号）
- **reference_image**：使用的垫图文件

示例（中文文章）：
```json
{
  "topic": "Linter 诊断模块",
  "context": "代码静态分析、问题检测、Linter 角色、诊断流程",
  "section_content": "Linter 模块是 Claude Code 代码医疗系统的诊断核心。它通过静态分析技术扫描代码，识别潜在问题如语法错误、风格违规、潜在 bug。类似医生做检查，Linter 会生成详细的诊断报告...",
  "key_points": [
    "静态分析扫描代码",
    "识别语法错误和风格问题",
    "生成诊断报告"
  ],
  "visual_suggestion": "医疗诊断比喻：放大镜/显微镜检查代码，代码行旁边标注问题标记，生成诊断清单"
}
```

示例（英文文章）：
```json
{
  "topic": "Linter Diagnostics Module",
  "context": "Static code analysis, issue detection, Linter role, diagnostic flow",
  "section_content": "The Linter module serves as the diagnostic core of Claude Code's code healthcare system. It performs static analysis to scan code and identify potential issues like syntax errors, style violations, and potential bugs...",
  "key_points": [
    "Static analysis scans code",
    "Identifies syntax and style issues",
    "Generates diagnostic reports"
  ],
  "visual_suggestion": "Medical diagnosis metaphor: magnifying glass examining code, issue markers beside code lines, diagnostic checklist"
}
```

### 9. 保存分析结果

写入 `step02-analyze/analysis.json`：

```json
{
  "document": {
    "title": "Claude Code 入门指南",
    "path": "/path/to/doc.md",
    "keyword": "claude-code",
    "total_sections": 6,
    "total_words": 3500
  },
  "cover": {
    "type": "cover",
    "topic": "Claude Code 入门指南",
    "focal_point": "AI 驱动的编程助手",
    "style_id": "info-card",
    "reference_image": "cover-info-card.png",
    "platform": {
      "aspect": "16:9",
      "resolution": "1600x900"
    }
  },
  "illustrations": [
    {
      "index": 1,
      "type": "main",
      "section": "## 安装配置",
      "section_id": "installation",
      "insert_after_line": 25,
      "topic": "安装配置流程",
      "context": "环境配置、依赖安装、初始化流程、命令行工具设置",
      "section_content": "首先使用 npm install -g claude-code 完成全局安装，然后运行 claude-code auth 配置 Anthropic API Key。接下来可以选择 VS Code 或 Cursor 进行 IDE 集成，通过插件市场搜索安装即可...",
      "key_points": [
        "npm 全局安装",
        "API Key 认证配置",
        "IDE 集成（VS Code/Cursor）"
      ],
      "visual_suggestion": "展示终端窗口执行安装命令，旁边是钥匙图标表示认证，下方是 IDE 图标表示集成",
      "style_id": "info-card",
      "reference_image": "main-info-card.jpg",
      "platform": {
        "aspect": "16:9",
        "resolution": "1280x720"
      }
    },
    {
      "index": 2,
      "type": "main",
      "section": "## 核心功能",
      "section_id": "core-features",
      "insert_after_line": 58,
      "topic": "核心功能与能力",
      "context": "代码补全、智能重构、调试辅助、AI 对话编程",
      "section_content": "Claude Code 的核心能力包括智能代码补全、上下文感知的代码重构、交互式调试辅助。通过自然语言对话，开发者可以描述需求，AI 自动生成代码并解释实现逻辑...",
      "key_points": [
        "智能代码补全与生成",
        "上下文感知重构",
        "自然语言对话编程"
      ],
      "visual_suggestion": "大脑/AI 核心连接多个功能模块：代码编辑器、调试器、对话框，形成能力网络",
      "style_id": "info-card",
      "reference_image": "main-info-card.jpg",
      "platform": {
        "aspect": "16:9",
        "resolution": "1280x720"
      }
    },
    {
      "index": 3,
      "type": "main",
      "section": "## 最佳实践",
      "section_id": "best-practices",
      "insert_after_line": 102,
      "topic": "AI 辅助开发最佳实践",
      "context": "工作流程优化、效率提升策略、提示词技巧、协作模式",
      "section_content": "高效使用 Claude Code 的关键在于：1）提供清晰的上下文和需求描述；2）善用代码审查功能检查 AI 生成的代码；3）建立人机协作的工作节奏，让 AI 处理重复性工作...",
      "key_points": [
        "清晰的上下文描述",
        "代码审查验证",
        "人机协作工作流"
      ],
      "visual_suggestion": "人与 AI 协作场景：开发者在左侧思考，AI 在右侧执行，中间是代码流转的箭头循环",
      "style_id": "info-card",
      "reference_image": "main-info-card.jpg",
      "platform": {
        "aspect": "16:9",
        "resolution": "1280x720"
      }
    }
  ],
  "metadata": {
    "analyzed_at": "2026-01-29T10:05:00Z",
    "main_count": 3,
    "cover_style_id": "gradient-tech",
    "main_style_id": "info-card",
    "platform_id": "x",
    "language": "zh"
  }
}
```

---

## 输出

| 文件 | 路径 | 内容 |
|------|------|------|
| 分析结果 | `{run_dir}/step02-analyze/analysis.json` | 封面+主图配置 |

---

## 进度更新

更新 `state/progress.json`：

```json
{
  "step": 2,
  "checkpoint": "2b",
  "status": "analyzed",
  "updated_at": "2026-01-29T10:05:00Z",
  "recovery_hint": "继续 Step 03 生成配图"
}
```

---

## 验证检查点

| 编号 | 检查项 | 通过标准 |
|------|--------|----------|
| 2a | 文档读取 | content 非空 |
| 2b | analysis.json 写入 | 文件存在且 JSON 可解析 |
| 2c | 封面/主图风格写入 | cover.style_id 与 main.style_id 存在 |

---

## 下一步

执行 `workflow/step03-generate.md`
