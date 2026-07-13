"""启动 QA Home 服务（API + 静态页面 + SQLite）

推荐使用 venv 启动:
  ./scripts/setup.sh   # 首次初始化
  ./scripts/run.sh     # 启动服务（自动释放端口）
  ./scripts/stop.sh    # 停止服务
"""
import os

import uvicorn

PORT = int(os.environ.get("PORT", 8765))

if __name__ == "__main__":
    uvicorn.run("server.app:app", host="0.0.0.0", port=PORT, reload=True)
