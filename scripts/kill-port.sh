#!/usr/bin/env bash
# 释放指定端口（默认 8765）
set -euo pipefail

PORT="${1:-${PORT:-8765}}"

PIDS=$(lsof -ti:"$PORT" 2>/dev/null || true)
if [ -z "$PIDS" ]; then
  echo "端口 $PORT 未被占用"
  exit 0
fi

echo "→ 释放端口 $PORT (PID: $(echo "$PIDS" | tr '\n' ' '))"
echo "$PIDS" | xargs kill -9 2>/dev/null || true
sleep 0.3
echo "✅ 端口 $PORT 已释放"
