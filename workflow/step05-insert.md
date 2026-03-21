# Step 05: 插入文档

## 概述

| 项目 | 内容 |
|------|------|
| **执行者** | 主 Agent |
| **输入** | `step04-upload/urls.json` + `step02-analyze/analysis.json` |
| **输出** | `output/{doc}.md` |

---

## 职责

将 R2 图片链接插入到 Markdown 文档的指定位置。

---

## 执行流程

### 1. 读取数据

```bash
ANALYSIS=$(cat "$RUN_DIR/step02-analyze/analysis.json")
URLS=$(cat "$RUN_DIR/step04-upload/urls.json")
DOC_PATH=$(jq -r '.document.path' "$RUN_DIR/state/config.json")
```

### 2. 复制文档到 output

```bash
cp "$DOC_PATH" "$RUN_DIR/output/"
```

### 3. 构建 URL 映射

从 `urls.json` 提取每个文件对应的 URL：

```python
url_map = {
    "01-overview.png": "https://pub-xxx.r2.dev/images/...",
    "02-workflow.png": "https://pub-xxx.r2.dev/images/..."
}
```

### 4. 按位置插入图片

从后向前插入（避免行号偏移）：

```python
# 按 insert_after_line 降序排列
illustrations = sorted(analysis["illustrations"],
                      key=lambda x: x["insert_after_line"],
                      reverse=True)

for illust in illustrations:
    line_num = illust["insert_after_line"]
    topic = illust["topic"]
    filename = f"{illust['index']:02d}-{illust['section_id']}.png"
    url = url_map[filename]

    # 构建图片 Markdown
    img_md = f"\n![{topic}]({url})\n"

    # 在指定行后插入
    insert_after_line(doc_lines, line_num, img_md)
```

### 5. 插入格式

```markdown
## 概述

本章介绍 AI 工具的分类和应用场景。

![AI Tools Ecosystem Overview](https://pub-xxx.r2.dev/images/doc-style-ai-tools-01-overview.png)

AI 工具可以分为以下几类：
```

**规则**：
- 在指定行号后插入空行 + 图片 + 空行
- 图片 alt 文本使用 topic
- 保持文档格式整洁

### 6. 保存文档

写入 `output/{original-filename}.md`

---

## 完成报告

输出汇总表格：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 风格配图完成！

📊 统计信息：
   - 配图数量: 5
   - 上传成功: 5
   - 风格: 扁平插画
   - 模式: 提示词模式

📁 输出文件：
   - 配图文档: {run_dir}/output/document.md

🔗 图片链接：
   1. 01-overview.png → https://...
   2. 02-workflow.png → https://...
   3. 03-architecture.png → https://...
   4. 04-deployment.png → https://...
   5. 05-summary.png → https://...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 错误处理

| 错误 | 处理 |
|------|------|
| 插入位置无效 | 追加到章节末尾 |
| 文档复制失败 | 报错并停止 |
| URL 不存在 | 跳过该图片 |

---

## 输出

| 文件 | 路径 | 内容 |
|------|------|------|
| 配图文档 | `{run_dir}/output/*.md` | 插入图片后的文档 |

---

## 进度更新

更新 `state/progress.json`：

```json
{
  "step": 5,
  "checkpoint": "5b",
  "status": "completed",
  "updated_at": "2026-01-29T10:25:00Z",
  "recovery_hint": "流程完成，无需恢复"
}
```

---

## 验证检查点

| 编号 | 检查项 | 通过标准 |
|------|--------|----------|
| 5a | 文档复制 | `{run_dir}/output/` 下存在目标文件 |
| 5b | 图片插入 | 插入图片数量与 urls.json 一致 |
| 5c | Markdown 可读 | 图片前后保留空行 |
