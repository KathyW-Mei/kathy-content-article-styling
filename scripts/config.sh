#!/bin/bash
# Doc MD Styler - 配置文件
# 版本：1.0.0

# ==================== 处理配置 ====================
export MAX_RETRIES=3              # 最大重试次数

# ==================== 日志配置 ====================
# 强制要求 RUN_DIR，不在 Skill 根目录创建 logs
if [ -z "${RUN_DIR:-}" ]; then
    echo "[WARN] RUN_DIR 未设置，日志将只输出到 stderr" >&2
    export LOG_DIR=""
    export LOG_FILE="/dev/null"
else
    export LOG_DIR="$RUN_DIR/logs"
    export LOG_FILE="$LOG_DIR/processing-$(date +%Y%m%d).log"
    mkdir -p "$LOG_DIR"
fi

# 日志函数
log_info() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $*" | tee -a "$LOG_FILE" >&2
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $*" | tee -a "$LOG_FILE" >&2
}

log_success() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS] $*" | tee -a "$LOG_FILE" >&2
}
