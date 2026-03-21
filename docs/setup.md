# 环境初始化指南

## 依赖安装

### Python 环境

```bash
cd ~/.claude/skills/xiangyu-content-article-styling/scripts/python
uv venv
uv pip install -e .
```

### 系统依赖

```bash
# macOS
brew install jq openssl
```

系统默认需具备：
- curl
- file
- xxd

### 脚本权限

```bash
chmod +x ~/.claude/skills/xiangyu-content-article-styling/scripts/shell/*.sh
chmod +x ~/.claude/skills/xiangyu-content-article-styling/scripts/python/*.py
```

---

## 凭证配置

### Gemini API

使用本 Skill 的凭证文件：

```
~/.claude/skills/xiangyu-content-article-styling/credentials/gemini.json
```

API Key 由 `generate_image.py` 从 `credentials/gemini.json` 读取。

### R2 存储

R2 凭证放在：

```bash
~/.claude/skills/xiangyu-content-article-styling/credentials/r2.json
```

---

## 验证安装

```bash
# 1. 测试 Python 环境
cd ~/.claude/skills/xiangyu-content-article-styling/scripts/python
source .venv/bin/activate
python3 -c "from google import genai; print('OK')"

# 2. 测试 R2 上传（依赖 jq）
cd ~/.claude/skills/xiangyu-content-article-styling/scripts/shell
./upload-to-r2.sh /path/to/test.png test-upload.png
```

---

## 添加参考图片（图片模式）

如果要使用图片模式，需要添加参考图片：

```bash
# 为新风格添加参考图
cp /path/to/cover.png \
   ~/.claude/skills/xiangyu-content-article-styling/reference/images/cover-my-style.png

cp /path/to/main.png \
   ~/.claude/skills/xiangyu-content-article-styling/reference/images/main-my-style.png
```

参考图片要求：
- 格式：JPEG 或 PNG
- 分辨率：建议 1920x1080 或更高
- 风格：与目标风格一致
