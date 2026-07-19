#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d "venv" ]; then
  echo "❌ 未找到 venv，请先运行: ./scripts/setup.sh"
  exit 1
fi

echo "→ 安装 Playwright Chromium 浏览器..."
venv/bin/python -m playwright install chromium

echo "→ 验证浏览器..."
venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    browser.close()
print('✅ Playwright Chromium 已就绪')
"
