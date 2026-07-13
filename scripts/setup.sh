#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d "venv" ]; then
  echo "→ 创建虚拟环境 venv/"
  python3 -m venv venv
fi

echo "→ 安装依赖"
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

echo "✅ 环境就绪。启动服务: ./scripts/run.sh"
