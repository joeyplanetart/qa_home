# 改动记录

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased]

### 新增
- 🤖 **UI 自动化模块**：Playwright + pytest 本地执行，管理页 `/automation`
  - 用例浏览（源码高亮、行号定位）、勾选运行、运行配置（有头/无头、视口、设备等）
  - 执行结果、历史记录、日志、HTML 报告、失败截图
  - 测试数据 Artifacts（注册账号、site_id 等）
  - pytest marker：`selected`（默认勾选）、`smoke`（冒烟）
- CafePress E2E 套件：Page Object 模块化结构（首页、搜索、商品、购物车、登录/注册）
- 项目卡片增加 🤖 自动化用例数统计（通过 `meta.json` 的 `projectId` 关联）
- `scripts/install-playwright.sh`：一键安装 Playwright Chromium

### 变更
- 项目文档更新：README、使用文档、部署文档补充 UI 自动化说明
- `.gitignore` 增加 `.idea/`（PyCharm）
- 新增 Cursor Skill：`.cursor/skills/qa-automation/`（生成/调试自动化用例）

### 修复
- 用例源码行号与高亮定位不一致
- 运行选中数量与执行结果不匹配（侧边栏/run 逻辑统一）
- 默认选中状态在切换 Tab 时重复应用

---

## [0.2.1] - 2026-07

### 新增
- 项目文档：README、使用文档、部署文档、改动记录

---

## [0.2.0] - 2026-07

### 新增
- 🛠️ **工具 Tab**：QA 常用工具链接管理
- 🩺 **项目健康检查**：批量探测站点 HTTP 可达性，5 分钟自动刷新
- **Turso 云数据库**：支持 Turso libSQL，Vercel Serverless 部署
- PlanetArt 内部项目扩展：Devtools、Cordial、Overlay_tool
- 项目卡片 env 标签支持 `pre` 环境

### 变更
- 前端迁移至 `server/static/`
- 数据库双模式：Turso（线上）/ SQLite（本地兜底）
- 项目筛选移至顶部搜索栏旁
- 移除所有删除/重置确认弹框
- 项目 Tab 统计改为 API 实时查询，筛选逻辑与统计对齐
- 使用 `pyproject.toml` + `uv.lock` 管理依赖

### 修复
- 项目 Tab 空白（stats API 失败导致渲染中断）
- 启动脚本从 `scripts/` 目录执行时找不到 `kill-port.sh`
- 项目卡片数据统计不准确

---

## [0.1.0] - 2026-07-12

### 新增
- QA Home 初始版本
- **项目维度**：24 个 PlanetArt 站点，5 个业务线分组
- **备忘录**：分类、颜色、置顶、按项目关联
- **操作流程**：步骤化文档，标签支持
- **代码片段**：多语言，一键复制
- **快捷链接**：侧边栏固定入口
- **每日清单**：可勾选任务，进度条，重置
- **全局搜索**：跨模块搜索
- **深色模式**
- **FastAPI + SQLite** 后端，REST API
- **venv 管理脚本**：`setup.sh` / `run.sh` / `stop.sh` / `kill-port.sh`
- 首次启动自动 seed 示例数据

[Unreleased]: https://github.com/joeyplanetart/qa_home/compare/main...HEAD
[0.2.0]: https://github.com/joeyplanetart/qa_home/compare/a9e3315...831a616
[0.1.0]: https://github.com/joeyplanetart/qa_home/commit/a9e3315
