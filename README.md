# QA Home

PlanetArt QA 团队的工作台：按项目维度管理测试资源，集中存放备忘录、操作流程、代码片段、工具链接与每日清单。

**仓库：** https://github.com/joeyplanetart/qa_home

## 功能概览

| 模块 | 说明 |
|------|------|
| 📦 项目 | 24+ 站点按业务线分组，展示域名、环境、内容统计与健康状态 |
| 📝 备忘录 | 测试环境、Bug 要点、API 说明等，支持分类、颜色、置顶 |
| ⚙️ 操作流程 | 冒烟、发布、订单变更等步骤化文档 |
| 💻 代码片段 | SQL / Bash / Git 等常用命令，一键复制 |
| 🛠️ 工具 | QA 常用内部/外部工具链接 |
| 🔗 快捷链接 | 侧边栏固定入口（JIRA、Confluence 等） |
| ✅ 每日清单 | 可勾选的任务列表，支持重置 |

## 技术栈

- **前端：** 原生 HTML / CSS / JavaScript（无构建步骤）
- **后端：** Python 3.12+ · FastAPI · Uvicorn
- **数据库：** [Turso](https://turso.tech/)（线上）/ 本地 SQLite（开发兜底）
- **部署：** Vercel Serverless

## 快速开始

```bash
git clone https://github.com/joeyplanetart/qa_home.git
cd qa_home
./scripts/setup.sh    # 创建 venv、安装依赖
cp .env.example .env  # 填入 Turso Token（可选，本地可仅用 SQLite）
./scripts/run.sh      # 启动 → http://localhost:8765
```

## 文档

- [使用文档](docs/USAGE.md) — 界面操作与日常使用
- [部署文档](docs/DEPLOY.md) — 本地开发、Turso 配置、Vercel 部署
- [改动记录](CHANGELOG.md) — 版本更新历史

## 项目结构

```
qa_home/
├── server/
│   ├── app.py          # FastAPI 路由与 API
│   ├── db.py           # 数据库连接（Turso / SQLite）
│   ├── turso.py        # Turso HTTP 客户端
│   ├── seed.py         # 首次启动示例数据
│   └── static/         # 前端静态资源
│       ├── index.html
│       └── assets/
├── scripts/
│   ├── setup.sh        # 环境初始化
│   ├── run.sh          # 启动服务（自动释放端口）
│   ├── stop.sh         # 停止服务
│   └── kill-port.sh    # 释放占用端口
├── docs/               # 文档
├── data/               # 本地 SQLite（git 忽略）
├── run.py              # 开发入口
├── requirements.txt
├── pyproject.toml
└── vercel.json         # Vercel 部署配置
```

## 常用命令

```bash
./scripts/run.sh              # 启动（默认 8765）
PORT=9000 ./scripts/run.sh    # 指定端口
./scripts/stop.sh             # 停止服务
```

## 环境变量

见 [`.env.example`](.env.example)：

| 变量 | 说明 |
|------|------|
| `TURSO_DATABASE_URL` | Turso 数据库 URL |
| `TURSO_AUTH_TOKEN` | Turso 数据库 Token（非组织 API Token） |
| `PORT` | 本地服务端口，默认 `8765` |

## License

内部使用，PlanetArt QA Team。
