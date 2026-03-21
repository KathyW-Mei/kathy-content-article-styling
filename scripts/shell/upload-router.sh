#!/bin/bash
# 图片上传路由脚本 - 根据模式选择 COS/R2/本地
# 用法: ./upload-router.sh <mode> <local_path> <filename> [output_dir]

set -e

# ==================== 加载配置 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SKILL_DIR/scripts/config.sh"

# ==================== 参数解析 ====================
MODE="$1"
LOCAL_PATH="$2"
FILENAME="$3"
OUTPUT_DIR="$4"

if [ -z "$MODE" ] || [ -z "$LOCAL_PATH" ] || [ -z "$FILENAME" ]; then
    echo "用法: $0 <mode> <local_path> <filename> [output_dir]"
    echo "  mode: cos | r2 | local"
    echo "  local_path: 本地图片路径"
    echo "  filename: 目标文件名"
    echo "  output_dir: 本地模式必须，输出目录"
    exit 1
fi

# ==================== 路由处理 ====================
case "$MODE" in
    cos)
        # 腾讯云 COS 上传（使用 Python SDK）
        log_info "路由到 COS 上传: $FILENAME"
        RESULT=$("$SKILL_DIR/scripts/python/.venv/bin/python" \
          "$SKILL_DIR/scripts/python/upload_to_cos.py" \
          --skill-dir "$SKILL_DIR" \
          --local-path "$LOCAL_PATH" \
          --filename "$FILENAME" 2>/dev/null)
        echo "$RESULT" | jq -r '.url'
        ;;

    r2)
        # Cloudflare R2 上传
        log_info "路由到 R2 上传: $FILENAME"
        bash "$SCRIPT_DIR/upload-to-r2.sh" "file://$LOCAL_PATH" "$FILENAME"
        ;;

    local)
        # 本地存储
        if [ -z "$OUTPUT_DIR" ]; then
            log_error "本地模式需要指定 output_dir"
            exit 1
        fi

        log_info "本地存储: $FILENAME"

        # 创建 images 目录
        IMAGES_DIR="$OUTPUT_DIR/images"
        mkdir -p "$IMAGES_DIR"

        # 复制文件
        cp "$LOCAL_PATH" "$IMAGES_DIR/$FILENAME"
        log_success "本地存储成功: $IMAGES_DIR/$FILENAME"

        # 返回相对路径
        echo "./images/$FILENAME"
        ;;

    *)
        log_error "未知模式: $MODE (支持: cos, r2, local)"
        exit 1
        ;;
esac
