#!/bin/bash
# 纯 bash + curl 上传文件到 R2（依赖 jq 解析 JSON）
# 用法: ./upload-to-r2.sh <图片URL|本地路径> <文件名>

set -e

# 加载配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SKILL_DIR/scripts/config.sh"

# 检查 jq
if ! command -v jq >/dev/null 2>&1; then
    echo "[ERROR] 缺少依赖: jq 未安装"
    echo "请先安装 jq，例如: brew install jq"
    exit 1
fi

# 读取 R2 凭证
CRED_PATH="$SKILL_DIR/credentials/r2.json"
if [ ! -f "$CRED_PATH" ]; then
    echo "[ERROR] R2 凭证不存在: $CRED_PATH"
    exit 1
fi

R2_ACCOUNT_ID=$(jq -r '.auth.account_id' "$CRED_PATH")
R2_ACCESS_KEY=$(jq -r '.auth.access_key' "$CRED_PATH")
R2_SECRET_KEY=$(jq -r '.auth.secret_key' "$CRED_PATH")
R2_BUCKET=$(jq -r '.auth.bucket' "$CRED_PATH")
R2_PUBLIC_URL=$(jq -r '.auth.public_url' "$CRED_PATH")
R2_IMAGES_FOLDER=$(jq -r '.auth.images_folder' "$CRED_PATH")

if [ -z "$R2_ACCOUNT_ID" ] || [ -z "$R2_ACCESS_KEY" ] || [ -z "$R2_SECRET_KEY" ] || [ -z "$R2_BUCKET" ] || [ -z "$R2_PUBLIC_URL" ]; then
    echo "[ERROR] R2 凭证字段不完整，请检查: $CRED_PATH"
    exit 1
fi

IMAGE_URL="$1"
FILENAME="$2"
TEMP_DIR="/tmp/r2-upload-$$"

# 验证参数
if [ -z "$IMAGE_URL" ] || [ -z "$FILENAME" ]; then
    log_error "缺少参数: 需要提供图片URL和文件名"
    echo "用法: $0 <图片URL> <文件名>"
    exit 1
fi

# 创建临时目录
mkdir -p "$TEMP_DIR"

# 处理输入来源（本地文件或 URL）
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
    # 下载图片（最多重试 MAX_RETRIES 次）
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

# R2 对象路径
OBJECT_KEY="${R2_IMAGES_FOLDER}/${FILENAME}"
FILE_PATH="$TEMP_DIR/$FILENAME"

# 生成 AWS Signature V4 签名并上传
log_info "上传到 R2: $OBJECT_KEY"

REGION="auto"
SERVICE="s3"
DATE=$(date -u +"%Y%m%d")
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
CONTENT_TYPE=$(file -b --mime-type "$FILE_PATH" 2>/dev/null || echo "application/octet-stream")
CONTENT_LENGTH=$(wc -c < "$FILE_PATH" | tr -d ' ')

# 计算文件哈希
hash_sha256_hex_file() {
    openssl dgst -sha256 -binary "$1" | xxd -p -c 256
}

hash_sha256_hex_string() {
    printf "%s" "$1" | openssl dgst -sha256 -binary | xxd -p -c 256
}

PAYLOAD_HASH=$(hash_sha256_hex_file "$FILE_PATH")

# Canonical Request (R2 不支持 x-amz-acl)
CANONICAL_REQUEST="PUT
/${OBJECT_KEY}

content-length:${CONTENT_LENGTH}
content-type:${CONTENT_TYPE}
host:${R2_BUCKET}.${R2_ACCOUNT_ID}.r2.cloudflarestorage.com
x-amz-content-sha256:${PAYLOAD_HASH}
x-amz-date:${TIMESTAMP}

content-length;content-type;host;x-amz-content-sha256;x-amz-date
${PAYLOAD_HASH}"

# String to Sign
CANONICAL_REQUEST_HASH=$(hash_sha256_hex_string "$CANONICAL_REQUEST")
STRING_TO_SIGN="AWS4-HMAC-SHA256
${TIMESTAMP}
${DATE}/${REGION}/${SERVICE}/aws4_request
${CANONICAL_REQUEST_HASH}"

# 计算签名
kSecret="AWS4${R2_SECRET_KEY}"
kDate=$(printf "%s" "${DATE}" | openssl dgst -sha256 -mac HMAC -macopt key:"${kSecret}" -binary | xxd -p -c 256)
kRegion=$(printf "%s" "${REGION}" | openssl dgst -sha256 -mac HMAC -macopt hexkey:"${kDate}" -binary | xxd -p -c 256)
kService=$(printf "%s" "${SERVICE}" | openssl dgst -sha256 -mac HMAC -macopt hexkey:"${kRegion}" -binary | xxd -p -c 256)
kSigning=$(printf "aws4_request" | openssl dgst -sha256 -mac HMAC -macopt hexkey:"${kService}" -binary | xxd -p -c 256)
SIGNATURE=$(printf "%s" "$STRING_TO_SIGN" | openssl dgst -sha256 -mac HMAC -macopt hexkey:"${kSigning}" -binary | xxd -p -c 256)

# Authorization Header
AUTHORIZATION="AWS4-HMAC-SHA256 Credential=${R2_ACCESS_KEY}/${DATE}/${REGION}/${SERVICE}/aws4_request,SignedHeaders=content-length;content-type;host;x-amz-content-sha256;x-amz-date,Signature=${SIGNATURE}"

# 上传文件（最多重试 MAX_RETRIES 次）
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
        -H "Host: ${R2_BUCKET}.${R2_ACCOUNT_ID}.r2.cloudflarestorage.com" \
        -H "Content-Type: ${CONTENT_TYPE}" \
        -H "Content-Length: ${CONTENT_LENGTH}" \
        -H "x-amz-content-sha256: ${PAYLOAD_HASH}" \
        -H "x-amz-date: ${TIMESTAMP}" \
        -H "Authorization: ${AUTHORIZATION}" \
        --data-binary "@${FILE_PATH}" \
        "https://${R2_BUCKET}.${R2_ACCOUNT_ID}.r2.cloudflarestorage.com/${OBJECT_KEY}")

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
        log_success "上传成功！"
        PUBLIC_URL="${R2_PUBLIC_URL}/${OBJECT_KEY}"
        log_info "公开链接: $PUBLIC_URL"
        rm -rf "$TEMP_DIR"
        echo "$PUBLIC_URL"
        exit 0
    else
        RETRY=$((RETRY + 1))
        if [ $RETRY -lt $MAX_RETRIES ]; then
            log_info "上传失败 (HTTP $HTTP_CODE)，重试 $RETRY/$MAX_RETRIES..."
            # 重新生成时间戳和签名（可能是时间同步问题）
            DATE=$(date -u +"%Y%m%d")
            TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")

            CANONICAL_REQUEST="PUT
/${OBJECT_KEY}

content-length:${CONTENT_LENGTH}
content-type:${CONTENT_TYPE}
host:${R2_BUCKET}.${R2_ACCOUNT_ID}.r2.cloudflarestorage.com
x-amz-content-sha256:${PAYLOAD_HASH}
x-amz-date:${TIMESTAMP}

content-length;content-type;host;x-amz-content-sha256;x-amz-date
${PAYLOAD_HASH}"

            CANONICAL_REQUEST_HASH=$(hash_sha256_hex_string "$CANONICAL_REQUEST")
            STRING_TO_SIGN="AWS4-HMAC-SHA256
${TIMESTAMP}
${DATE}/${REGION}/${SERVICE}/aws4_request
${CANONICAL_REQUEST_HASH}"

            kDate=$(printf "%s" "${DATE}" | openssl dgst -sha256 -mac HMAC -macopt key:"${kSecret}" -binary | xxd -p -c 256)
            kRegion=$(printf "%s" "${REGION}" | openssl dgst -sha256 -mac HMAC -macopt hexkey:"${kDate}" -binary | xxd -p -c 256)
            kService=$(printf "%s" "${SERVICE}" | openssl dgst -sha256 -mac HMAC -macopt hexkey:"${kRegion}" -binary | xxd -p -c 256)
            kSigning=$(printf "aws4_request" | openssl dgst -sha256 -mac HMAC -macopt hexkey:"${kService}" -binary | xxd -p -c 256)
            SIGNATURE=$(printf "%s" "$STRING_TO_SIGN" | openssl dgst -sha256 -mac HMAC -macopt hexkey:"${kSigning}" -binary | xxd -p -c 256)
            AUTHORIZATION="AWS4-HMAC-SHA256 Credential=${R2_ACCESS_KEY}/${DATE}/${REGION}/${SERVICE}/aws4_request,SignedHeaders=content-length;content-type;host;x-amz-content-sha256;x-amz-date,Signature=${SIGNATURE}"

            sleep 2
        else
            log_error "上传失败 (HTTP $HTTP_CODE)，已达到最大重试次数"
            rm -rf "$TEMP_DIR"
            exit 1
        fi
    fi
done
