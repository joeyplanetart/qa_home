# QA Automation 参考

## 运行环境

| 项 | 值 |
|----|-----|
| 框架 | Playwright + pytest + pytest-playwright |
| 配置 | `automation/pytest.ini` |
| 执行引擎 | `server/runner.py` |
| 管理 UI | `http://localhost:8765/automation` |
| 报告目录 | `reports/{runId}/`（git 忽略） |

## 环境变量（runner 注入）

| 变量 | 说明 |
|------|------|
| `AUTOMATION_VIEWPORT_WIDTH` | 视口宽，默认 1280 |
| `AUTOMATION_VIEWPORT_HEIGHT` | 视口高，默认 720 |
| `AUTOMATION_TIMEOUT` | 默认超时 ms，默认 30000 |
| `AUTOMATION_LOCALE` | 浏览器 locale |
| `AUTOMATION_SCREENSHOTS_DIR` | 失败截图目录 |
| `AUTOMATION_ARTIFACTS_DIR` | test_data JSON 目录 |

UI 运行配置存 `localStorage`，后端通过 pytest 参数 `--headed`、`--browser` 等传递。

## pytest 命令

```bash
# 整个套件
venv/bin/python -m pytest automation/suites/cafepress/ -c automation/pytest.ini -v

# 单文件
venv/bin/python -m pytest automation/suites/cafepress/test_auth.py -c automation/pytest.ini -v

# 单用例 + 有头 + 慢动作（调试）
venv/bin/python -m pytest automation/suites/cafepress/test_auth.py::test_login_page_loads \
  -c automation/pytest.ini -v --headed --slowmo 500
```

## API（供 UI / 调试）

| 方法 | 路径 |
|------|------|
| GET | `/api/automation/suites` |
| GET | `/api/automation/suites/{id}/cases` |
| GET | `/api/automation/suites/{id}/files/{path}` |
| POST | `/api/automation/run` body: `{ suite, tests?, config? }` |
| GET | `/api/automation/runs/{id}` |

`tests` 格式：`test_auth.py::test_register_new_account`

## 用例解析（UI 展示）

`server/runner.py` 的 `_parse_test_cases` 解析：

- `markers` — `@pytest.mark.*`
- `selected` — 含 `selected` marker
- `line` — 用例起始行（含装饰器）

## CafePress 站点常量

| 项 | 值 |
|----|-----|
| B2C site_id | 170 (CAFUS) |
| B2B site_id | 169 (CPBUS) |
| 基础 URL | https://www.cafepress.com |
| 测试邮箱 | `qa.auto.{ts}.{rand}@planetart.com` |
| 测试密码 | `Test1234` |

## 代码审查清单

- [ ] Page Object 与 test 职责分离
- [ ] 无 `time.sleep`，用 `expect` 等待
- [ ] `goto` 使用 `domcontentloaded`
- [ ] 新套件有 `meta.json` + `projectId`
- [ ] 关键用例有合适 marker
- [ ] 产生业务数据的用例使用 `test_data`
- [ ] 本地 pytest 或 UI 跑通
