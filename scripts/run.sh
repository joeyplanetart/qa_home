#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8765}"

if [ ! -d "venv" ]; then
  echo "未找到 venv，请先运行: ./scripts/setup.sh"
  exit 1
fi

# 释放占用端口的进程
"$SCRIPT_DIR/kill-port.sh" "$PORT"

echo "→ 启动 QA Home  http://localhost:$PORT"
export PORT
exec venv/bin/python run.py
