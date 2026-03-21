#!/bin/bash
# 预检：参考图与凭证存在性检查
# 用法: ./precheck.sh <RUN_DIR>

set -e

if [ -z "${1:-}" ]; then
    echo "[ERROR] 缺少参数: RUN_DIR"
    echo "用法: $0 <RUN_DIR>"
    exit 1
fi

RUN_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

CONFIG_PATH="$RUN_DIR/state/config.json"
STYLES_PATH="$SKILL_DIR/reference/images/styles.json"
GEMINI_CRED="$SKILL_DIR/credentials/gemini.json"

if [ ! -f "$CONFIG_PATH" ]; then
    echo "[ERROR] 配置不存在: $CONFIG_PATH"
    exit 1
fi

if [ ! -f "$STYLES_PATH" ]; then
    echo "[ERROR] 风格索引不存在: $STYLES_PATH"
    exit 1
fi

if [ ! -f "$GEMINI_CRED" ]; then
    echo "[ERROR] Gemini 凭证不存在: $GEMINI_CRED"
    exit 1
fi

python3 - "$RUN_DIR" "$SKILL_DIR" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
skill_dir = Path(sys.argv[2])

config = json.loads((run_dir / "state" / "config.json").read_text(encoding="utf-8"))
styles = json.loads((skill_dir / "reference" / "images" / "styles.json").read_text(encoding="utf-8"))

cover_style_id = config.get("params", {}).get("cover_style_id")
main_style_id = config.get("params", {}).get("main_style_id")

def find_style(styles_list, style_id):
    for s in styles_list:
        if s.get("id") == style_id:
            return s
    return None

errors = []

cover_style = find_style(styles.get("cover_styles", []), cover_style_id)
if not cover_style:
    errors.append(f"封面风格不存在: {cover_style_id}")
else:
    cover_file = skill_dir / "reference" / "images" / cover_style["file"]
    if not cover_file.exists():
        errors.append(f"封面垫图缺失: {cover_file}")

main_style = find_style(styles.get("main_styles", []), main_style_id)
if not main_style:
    errors.append(f"主图风格不存在: {main_style_id}")
else:
    main_file = skill_dir / "reference" / "images" / main_style["file"]
    if not main_file.exists():
        errors.append(f"主图垫图缺失: {main_file}")

if errors:
    for err in errors:
        print(f"[ERROR] {err}")
    sys.exit(2)

print("[OK] 预检通过")
PY
