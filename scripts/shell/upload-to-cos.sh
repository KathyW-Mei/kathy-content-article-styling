#!/bin/bash
# 纯 bash + curl 上传文件到腾讯云 COS
# 用法: ./upload-to-cos.sh <图片URL|本地路径> <文件名>

set -e

# ==================== 加载配置 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SKILL_DIR/scripts/config.sh"

# ==================== 依赖检查 ====================
if ! command -v jq >/dev/null 2>&1; then
    echo "[ERROR] 缺少依赖: jq 未安装"
    echo "请先安装 jq，例如: brew install jq"
    exit 1
fi

# ==================== 读取 COS 凭证 ====================
CRED_PATH="$SKILL_DIR/credentials/cos.json"
if [ ! -f "$CRED_PATH" ]; then
    echo "[ERROR] COS 凭证不存在: $CRED_PATH"
    exit 1
fi

COS_SECRET_ID=$(jq -r '.auth.secret_id' "$CRED_PATH")
COS_SECRET_KEY=$(jq -r '.auth.secret_key' "$CRED_PATH")
COS_REGION=$(jq -r '.auth.region' "$CRED_PATH")
COS_BUCKET=$(jq -r '.auth.bucket' "$CRED_PATH")
COS_IMAGES_FOLDER=$(jq -r '.auth.images_folder' "$CRED_PATH")

if [ -z "$COS_SECRET_ID" ] || [ -z "$COS_SECRET_KEY" ] || [ -z "$COS_REGION" ] || [ -z "$COS_BUCKET" ]; then
    echo "[ERROR] COS 凭证字段不完整，请检查: $CRED_PATH"
    exit 1
fi

# ==================== 参数解析 ====================
IMAGE_URL="$1"
FILENAME="$2"
TEMP_DIR="/tmp/cos-upload-$$"

if [ -z "$IMAGE_URL" ] || [ -z "$FILENAME" ]; then
    log_error "缺少参数: 需要提供图片URL和文件名"
    echo "用法: $0 <图片URL|本地路径> <文件名>"
    exit 1
fi

mkdir -p "$TEMP_DIR"

# ==================== 处理输入来源 ====================
if [[ "$IMAGE_URL" == file://* ]]; then
    SOURCE_PATH="${IMAGE_URL#file://}"
elif [ -f "$IMAGE_URL" ]; then
    SOURCE_PATH="$IMAGE_URL"
else
    SOURCE_PATH=""
fi

if [ -n "$SOURCE_PATH" ]; then
    if [ ! -f "$SOURCE_PATH" ]; then
        log_error "本地文件不存在: $SOURCE_PATH"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    log_info "复制本地图片: $SOURCE_PATH"
    cp "$SOURCE_PATH" "$TEMP_DIR/$FILENAME"
    log_success "本地图片复制成功"
else
    # 下载图片
    log_info "下载图片: $IMAGE_URL"
    RETRY=0
    while [ $RETRY -lt $MAX_RETRIES ]; do
        if curl -L -f -o "$TEMP_DIR/$FILENAME" "$IMAGE_URL"; then
            log_success "图片下载成功"
            break
        else
            RETRY=$((RETRY + 1))
            if [ $RETRY -lt $MAX_RETRIES ]; then
                log_info "下载失败，重试 $RETRY/$MAX_RETRIES..."
                sleep 2
            else
                log_error "下载失败，已达到最大重试次数"
                rm -rf "$TEMP_DIR"
                exit 1
            fi
        fi
    done
fi

# ==================== COS 对象路径 ====================
OBJECT_KEY="${COS_IMAGES_FOLDER}/${FILENAME}"
FILE_PATH="$TEMP_DIR/$FILENAME"
HOST="${COS_BUCKET}.cos.${COS_REGION}.myqcloud.com"

# ==================== 腾讯云签名 V3（TC3-HMAC-SHA256） ====================
log_info "上传到 COS: $OBJECT_KEY"

# 时间戳
TIMESTAMP=$(date -u +%s)
DATE=$(date -u +%Y-%m-%d)

# Content-Type
CONTENT_TYPE=$(file -b --mime-type "$FILE_PATH" 2>/dev/null || echo "application/octet-stream")
CONTENT_LENGTH=$(wc -c < "$FILE_PATH" | tr -d ' ')

# 文件 SHA256
PAYLOAD_HASH=$(openssl dgst -sha256 -binary "$FILE_PATH" | xxd -p -c 256)

# HTTP 请求方法
HTTP_METHOD="PUT"

# ==================== 签名计算（简化版 - 使用 COS 原生签名） ====================
# COS 使用自己的签名格式，不是 TC3

# 生成签名有效期（1小时）
START_TIME=$TIMESTAMP
END_TIME=$((TIMESTAMP + 3600))
KEY_TIME="${START_TIME};${END_TIME}"

# HMAC-SHA1 辅助函数
hmac_sha1() {
    printf "%s" "$2" | openssl dgst -sha1 -hmac "$1" -binary | xxd -p -c 40
}

hmac_sha1_hex() {
    printf "%s" "$2" | openssl dgst -sha1 -mac HMAC -macopt hexkey:"$1" -binary | xxd -p -c 40
}

# Step 1: SignKey
SIGN_KEY=$(hmac_sha1 "$COS_SECRET_KEY" "$KEY_TIME")

# Step 2: HttpString（规范请求）
# 格式: HttpMethod\nUriPathname\nHttpParameters\nHttpHeaders\n
# HttpHeaders 格式: key=value&key=value（按字典序排列）
# 注意: 即使为空，换行符也必须保留
HTTP_STRING="put
/${OBJECT_KEY}

host=${HOST}
"

# Step 3: StringToSign
# macOS openssl 直接输出哈希，Linux 带前缀，用 awk NF 兼容
HTTP_STRING_SHA1=$(printf "%s" "$HTTP_STRING" | openssl dgst -sha1 | awk '{print $NF}')
STRING_TO_SIGN="sha1
${KEY_TIME}
${HTTP_STRING_SHA1}"

# Step 4: Signature
SIGNATURE=$(hmac_sha1_hex "$SIGN_KEY" "$STRING_TO_SIGN")

# Step 5: 构建 Authorization
AUTHORIZATION="q-sign-algorithm=sha1&q-ak=${COS_SECRET_ID}&q-sign-time=${KEY_TIME}&q-key-time=${KEY_TIME}&q-header-list=host&q-url-param-list=&q-signature=${SIGNATURE}"

# ==================== 上传文件 ====================
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
        -H "Host: ${HOST}" \
        -H "Content-Type: ${CONTENT_TYPE}" \
        -H "Content-Length: ${CONTENT_LENGTH}" \
        -H "Authorization: ${AUTHORIZATION}" \
        --data-binary "@${FILE_PATH}" \
        "https://${HOST}/${OBJECT_KEY}")

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
        log_success "上传成功！"
        PUBLIC_URL="https://${HOST}/${OBJECT_KEY}"
        log_info "公开链接: $PUBLIC_URL"
        rm -rf "$TEMP_DIR"
        echo "$PUBLIC_URL"
        exit 0
    else
        RETRY=$((RETRY + 1))
        if [ $RETRY -lt $MAX_RETRIES ]; then
            log_info "上传失败 (HTTP $HTTP_CODE)，重试 $RETRY/$MAX_RETRIES..."
            # 重新生成时间戳和签名
            TIMESTAMP=$(date -u +%s)
            START_TIME=$TIMESTAMP
            END_TIME=$((TIMESTAMP + 3600))
            KEY_TIME="${START_TIME};${END_TIME}"

            SIGN_KEY=$(hmac_sha1 "$COS_SECRET_KEY" "$KEY_TIME")
            HTTP_STRING_SHA1=$(printf "%s" "$HTTP_STRING" | openssl dgst -sha1 | awk '{print $NF}')
            STRING_TO_SIGN="sha1
${KEY_TIME}
${HTTP_STRING_SHA1}"
            SIGNATURE=$(hmac_sha1_hex "$SIGN_KEY" "$STRING_TO_SIGN")
            AUTHORIZATION="q-sign-algorithm=sha1&q-ak=${COS_SECRET_ID}&q-sign-time=${KEY_TIME}&q-key-time=${KEY_TIME}&q-header-list=host&q-url-param-list=&q-signature=${SIGNATURE}"

            sleep 2
        else
            log_error "上传失败 (HTTP $HTTP_CODE)，已达到最大重试次数"
            rm -rf "$TEMP_DIR"
            exit 1
        fi
    fi
done
