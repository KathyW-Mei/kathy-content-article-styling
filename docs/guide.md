# 文章风格配图使用指南

> 垫图模式为核心，用户自建风格库

---

## 功能概述

文章风格配图是一个为 Markdown 文章自动生成配图的 Skill，核心特点：

1. **垫图模式**：使用参考图片作为风格基准，生成风格一致的配图
2. **封面与主图**：封面与正文配图分别控制
3. **多平台适配**：X/微信/小红书/抖音，自动匹配分辨率
4. **用户可扩展**：添加自己的垫图即可创建新风格

---

## 快速开始

### 1. 触发 Skill

```
风格配图
```

或：

```
/xiangyu-content-article-styling
```

### 2. 回答两轮问题（4 + 1）

Skill 会一次询问所有参数：

| 问题 | 选项示例 |
|------|---------|
| 文章路径 | 拖拽文件或输入路径 |
| 目标平台 | X / 微信 / 小红书 / 抖音 |
| 主图数量 | 3 / 5 / 8 / auto |
| 封面风格 | 渐变科技 / 新闻报刊 / ... |
| 主图风格 | 信息卡片 / 信息图表 / ... |

### 3. 等待完成

Skill 自动执行：
- 分析文档结构
- 生成封面 + 主图
- 上传到 R2
- 插入文档

---

## 内置风格

### 封面风格

| 风格 | 适用场景 | 特点 |
|------|---------|------|
| 渐变科技 | 科技产品/AI | 蓝紫渐变、玻璃质感 |
| 新闻报刊 | 新闻资讯 | 报纸版式、红黑配色 |
| 笔记本涂鸦 | 教程/攻略 | 线圈本背景、手写字 |
| 简笔涂鸦 | 小红书/教程 | 手绘简笔、黄色高亮 |

### 主图风格

| 风格 | 适用场景 | 特点 |
|------|---------|------|
| 信息卡片 | 介绍性文章 | 卡片布局、信息块 |
| 知识理论 | 学术科普 | 螺旋/漏斗结构 |
| 信息图表 | 数据分析 | 结构化流程/图谱 |
| 渐变科技 | 科技产品/AI | 渐变科技视觉 |
| 科普插画 | 教育/学科 | 自然科学图解 |
| 笔记本涂鸦 | 教程/攻略 | 手写风格 |
| 简笔涂鸦 | 小红书/教程 | 轻松涂鸦 |

---

## 平台适配

不同平台有不同的最佳比例：

| 平台 | 封面 | 主图 |
|------|------|------|
| X/Twitter | 16:9 (1600×900) | 16:9 (1280×720) |
| 微信公众号 | 2.35:1 (900×383) | 16:9 (1280×720) |
| 小红书 | 3:4 (1080×1440) | 3:4 (1080×1440) |
| 抖音 | 9:16 (1080×1920) | 9:16 (1080×1920) |

---

## 添加自定义风格

### Step 1: 准备垫图

准备两张图片：
- 封面垫图：体现你想要的封面风格
- 主图垫图：体现你想要的正文配图风格

### Step 2: 放入目录

```bash
# 封面垫图
cp ~/Downloads/my-cover.png \
   ~/.claude/skills/xiangyu-content-article-styling/reference/images/cover-my-style.png

# 主图垫图
cp ~/Downloads/my-main.png \
   ~/.claude/skills/xiangyu-content-article-styling/reference/images/main-my-style.png
```

### Step 3: 更新索引

编辑 `reference/images/styles.json`，在对应数组添加：

```json
{
  "cover_styles": [
    {
      "id": "my-cover",
      "name": "我的封面风格",
      "description": "风格描述，适合xxx类型文章",
      "file": "cover-my-cover.png",
      "prompt_hint": "Style description for fallback generation"
    }
  ],
  "main_styles": [
    {
      "id": "my-main",
      "name": "我的主图风格",
      "description": "风格描述，适合xxx类型文章",
      "file": "main-my-main.png",
      "prompt_hint": "Style description for fallback generation"
    }
  ]
}
```

### Step 4: 使用新风格

下次运行时，「我的风格」会出现在风格选择列表中。

---

## 输出说明

配图完成后，输出目录结构：

```
{skill_dir}/runs/{keyword}-{timestamp}/
├── state/config.json            # 配置
├── state/progress.json          # 进度
├── step02-analyze/analysis.json # 分析结果
├── step03-generate/
│   ├── 00-cover.png            # 封面
│   ├── 01-section-a.png        # 主图 1
│   ├── 02-section-b.png        # 主图 2
│   └── 03-section-c.png        # 主图 3
├── step04-upload/urls.json     # 图片 URL
└── output/{doc}.md             # 带配图的文档
```

---

## 常见问题

### Q: 垫图不存在会怎样？

A: 自动回退到纯提示词模式，使用 `prompt_hint` 生成。

### Q: 如何查看已有风格？

A: 查看 `reference/images/styles.json`。

### Q: 生成失败怎么办？

A: 检查网络连接和 API Key。查看运行日志定位问题。

### Q: 可以只生成封面不生成主图吗？

A: 当前最少生成 2 张主图。如只需封面，可在 Step05 手动删除主图插入段落。

---

## 示例输出

使用「信息卡片」风格的配图示例：

```markdown
# Claude Code 入门指南

![Claude Code Introduction](https://r2.example.com/images/00-cover.png)

## 安装配置

安装 Claude Code 非常简单...

![Installation and Setup](https://r2.example.com/images/01-installation.png)

首先确保你的系统满足以下要求：
```
