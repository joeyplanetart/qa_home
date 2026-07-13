#!/usr/bin/env bash
# 停止 QA Home 服务
set -euo pipefail

PORT="${PORT:-8765}"
"$(cd "$(dirname "$0")" && pwd)/kill-port.sh" "$PORT"
