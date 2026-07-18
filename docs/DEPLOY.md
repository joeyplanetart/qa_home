# 部署文档

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.12+（见 `.python-version`） |
| 包管理 | pip + venv，或 [uv](https://github.com/astral-sh/uv) |
| 数据库（线上） | [Turso](https://turso.tech/) 账号 |
| 数据库（本地） | 无需额外配置，自动使用 SQLite |

---

## 一、本地开发

### 1. 克隆仓库

```bash
git clone https://github.com/joeyplanetart/qa_home.git
cd qa_home
```

### 2. 初始化环境

```bash
./scripts/setup.sh
```

脚本会：

- 创建 `venv/` 虚拟环境
- 安装 `requirements.txt` 依赖
- 提示复制 `.env.example` → `.env`

### 3. 配置环境变量（可选）

```bash
cp .env.example .env
```

**仅本地 SQLite 开发：** 可以不填 Turso 变量，服务会自动使用 `data/qa.db`。

**连接 Turso 云数据库：**

```bash
# 安装 Turso CLI
brew install tursodatabase/tap/turso

# 登录并创建数据库（若尚未创建）
turso auth login
turso db create qa

# 获取 URL
turso db show qa --url

# 生成数据库 Token（注意：是 db token，不是 org API token）
turso db tokens create qa
```

写入 `.env`：

```env
TURSO_DATABASE_URL=libsql://qa-xxx.turso.io
TURSO_AUTH_TOKEN=eyJ...
PORT=8765
```

### 4. 启动服务

```bash
./scripts/run.sh
```

访问 http://localhost:8765

`run.sh` 会自动 kill 占用端口的旧进程后再启动。

### 5. 停止服务

```bash
./scripts/stop.sh
```

### 使用 uv（可选）

```bash
uv sync
uv run python run.py
```

---

## 二、数据库说明

### 双模式自动切换

`server/db.py` 根据环境变量决定连接方式：

| 条件 | 存储 |
|------|------|
| 设置了 `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN` | Turso（libSQL HTTP） |
| 未设置 | 本地 SQLite `data/qa.db` |

### 数据表

| 表名 | 用途 |
|------|------|
| `memos` | 备忘录 |
| `quick_links` | 快捷链接 |
| `checklist_items` | 每日清单 |
| `operations` | 操作流程 |
| `snippets` | 代码片段 |
| `tools` | 工具链接 |
| `settings` | 用户设置（主题等） |
| `meta` | 元数据（seed 标记等） |

### 首次启动 Seed

服务启动时自动执行 `seed_if_empty()`，数据库为空时写入示例数据。已有数据不会重复 seed。

### 重置本地数据库

```bash
rm -f data/qa.db data/qa.db-wal data/qa.db-shm
./scripts/run.sh
```

---

## 三、Vercel 部署

项目已配置 `vercel.json` 与 `pyproject.toml`，入口为 `server.app:app`。

### 1. 连接 GitHub 仓库

在 [Vercel Dashboard](https://vercel.com/) 导入 `joeyplanetart/qa_home`。

### 2. 配置环境变量

在 Vercel 项目 Settings → Environment Variables 中添加：

| 变量 | 值 |
|------|-----|
| `TURSO_DATABASE_URL` | Turso 数据库 URL |
| `TURSO_AUTH_TOKEN` | Turso 数据库 Token |

> Vercel 无持久磁盘，**必须**配置 Turso，不能使用本地 SQLite。

### 3. 部署

推送 `main` 分支后 Vercel 自动构建部署。

```bash
git push origin main
```

或使用 Vercel CLI：

```bash
npm i -g vercel
vercel --prod
```

### 4. 验证

部署完成后访问 Vercel 分配的域名，确认：

- 首页正常加载
- API 返回数据（如 `/api/memos`）
- 增删改操作生效

---

## 四、API 端点

Base URL: `/api`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT/DELETE | `/memos` | 备忘录 CRUD |
| GET/POST/PUT/DELETE | `/links` | 快捷链接 CRUD |
| GET/POST/PUT/DELETE | `/checklist` | 每日清单 CRUD |
| POST | `/checklist/reset` | 重置所有勾选 |
| GET/POST/PUT/DELETE | `/operations` | 操作流程 CRUD |
| GET/POST/PUT/DELETE | `/snippets` | 代码片段 CRUD |
| GET/POST/PUT/DELETE | `/tools` | 工具链接 CRUD |
| GET/PUT | `/settings` | 用户设置 |
| GET | `/projects/stats` | 各项目内容统计 |
| POST | `/health-check` | 批量 URL 健康检查 |

---

## 五、生产注意事项

1. **Token 安全：** 不要将 `TURSO_AUTH_TOKEN` 提交到 Git，仅通过环境变量注入
2. **CORS：** 当前允许所有来源，内网使用无问题；若公网暴露需收紧
3. **健康检查：** 后端会对外部 URL 发起 HTTP 请求，注意频率与超时（默认 5 分钟 / 次）
4. **静态资源：** 前端文件位于 `server/static/`，修改后本地重启或重新部署生效
5. **项目配置：** 站点列表在 `server/static/assets/js/projects.js`，属前端静态配置，改后需刷新浏览器

---

## 六、故障排查

| 现象 | 处理 |
|------|------|
| `Address already in use` | 使用 `./scripts/run.sh`（自动 kill 端口） |
| `数据加载失败` | 检查服务是否启动；查看终端报错 |
| Turso 连接失败 | 确认 Token 是 **db token**；URL 格式为 `libsql://...` |
| Vercel 500 | 检查环境变量是否配置；查看 Vercel Function Logs |
| 项目 Tab 空白 | 硬刷新；检查浏览器 Console 是否有 JS 错误 |
