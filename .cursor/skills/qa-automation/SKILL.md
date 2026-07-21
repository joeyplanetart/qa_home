---
name: qa-automation
description: >-
  Generate and debug Playwright + pytest UI automation tests for QA Home.
  Use when creating test cases, Page Objects, suite scaffolding, fixing E2E
  failures, or working in automation/ directory.
---

# QA Home UI 自动化

Playwright + pytest 本地 E2E。管理页 `/automation`，代码在 `automation/`。

## 快速决策

| 任务 | 做法 |
|------|------|
| 新站点套件 | 建 `automation/suites/{id}/` + `meta.json` + `conftest.py` + `pages/` |
| 新页面交互 | 先写/扩 Page Object，再写 `test_*.py` |
| 新用例 | 函数名 `test_*`，优先用 fixture（`home`, `login` 等） |
| 关键路径默认跑 | 加 `@pytest.mark.selected` |
| 冒烟/发布前 | 加 `@pytest.mark.smoke` |
| 产生账号/订单数据 | 用 `test_data` fixture + `record_auth` / `record_order` |
| 调试失败 | 有头模式 → 单用例 pytest → 看截图/log |
| CYO Designer 加购 | 见下方「CYO Designer」；上传后须选 thumbnail 再点 ADD |
| Personalize 加购 | 见下方「Personalize 产品」；文本 slot 或 image slot |
| 普通商品加购 | 见下方「普通商品 PDP」；选 color/size/qty 后直接 ADD TO CART |
| 混合购物车下单 | 见下方「混合购物车下单」；需 env 账号，会真实下单 |

## 生成用例工作流

```
- [ ] 1. 确认套件目录与 meta.json（projectId 关联首页项目）
- [ ] 2. Page Object：locator 用 property，动作封装为方法
- [ ] 3. conftest.py 暴露 page fixture（如 def home(page): return HomePage(page)）
- [ ] 4. test_*.py：一个文件一个场景域，函数 test_ 开头
- [ ] 5. 断言用 playwright.sync_api.expect，不用 time.sleep
- [ ] 6. 需要 UI 默认选中则加 @pytest.mark.selected
- [ ] 7. 本地验证：pytest 单用例或 /automation 页勾选运行
```

### 目录约定

```
automation/suites/{suite_id}/
├── meta.json          # name, description, projectId
├── conftest.py        # 套件级 Page Object fixtures
├── pages/
│   ├── base.py        # BasePage：goto、关弹窗
│   └── *.py           # 各页面 Page Object
└── test_*.py          # 测试用例（不含 Page 类）
```

### Page Object 规则

- 继承 `BasePage`，`open()` 用 `wait_until="domcontentloaded"`（不用默认 `load`）
- Locator 优先：`get_by_role` > `get_by_placeholder` > `locator('#id')` > CSS
- 页面常量（URL path、site_id）放 Page 模块或 `pages/base.py`
- 不把断言写在 Page 里（断言留在 test）

### 测试文件规则

- 模块 docstring 说明场景域
- 导入 Page 从 `pages.*`（套件内相对导入）
- 测试数据：`make_test_email()` 等 helper 放 Page 模块
- 共享记录逻辑：套件内 `_record_*` 私有函数

### meta.json 模板

```json
{
  "name": "Site E2E",
  "description": "简短描述",
  "projectId": 170
}
```

`projectId` 对应 `server/static/assets/js/projects.js` 中的项目 ID。

## 调试工作流

```
- [ ] 1. 读失败信息：/automation 执行结果、output.log、失败截图
- [ ] 2. 有头复现：UI 配置 headed=true，或 pytest --headed
- [ ] 3. 单用例：pytest path/to/test.py::test_name -v --headed
- [ ] 4. 定位：检查 locator、弹窗遮挡、第三方脚本导致 load 超时
- [ ] 5. 修复后跑选用例集验证无回归
- [ ] 6. 自我调试循环：写最小 repro 脚本 → 跑通关键步骤 → 回填 Page Object → 再跑 pytest
```

### 自我调试（Agent / 开发者）

复杂页面（如 CYO Designer）先用独立 Playwright 脚本逐步探查 DOM 与弹窗，再落 Page Object：

1. **最小 repro**：在仓库根用 `venv/bin/python` 写临时脚本，只测失败步骤（如上传、切 Back、加购）。
2. **打印可见弹窗**：`.ui-dialog:visible` 的 title 与按钮文案，避免 overlay 挡点击。
3. **跑通后再抽象**：把稳定 locator / 等待条件写入 `pages/*.py`，测试只调 Page 方法。
4. **验证**：`pytest 单用例 -v`（无头）→ 失败则 `--headed` 复现 → 修 Page Object → 重跑直至通过。
5. **截图**：步骤截图用 `AUTOMATION_SCREENSHOTS_DIR`；失败时 conftest 自动全页截图。

### CYO Designer（Create Your Own）

参考 `automation/suites/cafepress/pages/designer.py`、`test_cyo_designer.py`。

| 步骤 | 要点 |
|------|------|
| PDP 选项 | `.container-option-item.Text-option-item` + `.option-text`；Position 选 `Front + Back` |
| Color | `.container-option-item[class*='color' i]` |
| Size | 仅匹配 `S/M/L/XL/...`，勿点到 Logo/Front/Back |
| Personalize | 等 `.SIDE_TAB`、`.ADD_LOGO`（designer 加载慢，timeout 90s） |
| 上传图片 | 点 `.ADD_LOGO` → `set_input_files` → **等 cloudfront thumbnail** → 点 `a.photo-tray-thumb-container` → `.btn.add` |
| 测试图 | `automation/assert/` 下 png/jpg，可用 `random_assert_image()` |
| 切 Back | `.SIDE_TAB a` 文本 `back`；弹出 **CONFIRM** 时点 **YES**（Apply Front to Back） |
| 渲染等待 | 上传 Front、点 YES 应用 Back、加购前各等 **≥3s**（`AUTOMATION_DESIGN_SETTLE_MS`，默认 3000） |
| CONFIRM 弹窗 | 须 **等待出现** 再点 YES；`count()==0` 直接 return 会漏点 |
| 加购 | `ADD TO CART`；若 **Missing Image** 可点 PROCEED ANYWAY（完整流程应无需） |
| 断言 | `/cart` 有 checkout、商品名含 custom men's value t-shirt |

```bash
venv/bin/python -m pytest automation/suites/cafepress/test_cyo_designer.py::test_cyo_front_back_personalize_add_to_cart \
  -c automation/pytest.ini -v --headed
```

### Personalize 产品（固定 slot）

参考 `automation/suites/cafepress/pages/personalize.py`。

与 CYO 区别：slot 固定，无需选 Position；分 **文本 slot** 与 **图片 slot** 两类。

#### Edit Text（文本 slot）

参考 `test_personalize_designer.py`。

| 步骤 | 要点 |
|------|------|
| PDP | 随机 color / size，quantity ≥ 2，点 Personalize |
| 等 UCD | `.UCD_TEXT_DIALOG` 可见（timeout 90s） |
| 编辑文本 | `textarea.ucd-multiline` 填入自定义文本（默认占位 `yourwordhere.`） |
| 渲染等待 | 填文本后等 ≥3s 再截图 |
| 加购 | ADD TO CART；未编辑会弹 Alert |

```bash
venv/bin/python -m pytest automation/suites/cafepress/test_personalize_designer.py::test_personalize_edit_text_add_to_cart \
  -c automation/pytest.ini -v --headed
```

#### Add Your Image（图片 slot）

参考 `test_personalize_image.py`。

| 步骤 | 要点 |
|------|------|
| PDP | 随机 color / size / quantity(2–5)，点 Personalize |
| 等 UCD | `.main-gallery-label` 含 Personalization Editor |
| 打开上传 | 点 `.ucd-main-wrapper`（非 `.ADD_LOGO`）打开 uploader |
| 上传图片 | 同 CYO：cloudfront thumbnail → 选缩略图 → `.btn.add` |
| 渲染等待 | 上传后等 ≥3s 再截图 |
| 加购 | ADD TO CART，等 just added 弹窗后再截图 |
| 断言 | `/cart` 含 long sleeve 商品名、subtotal、cart id |

```bash
venv/bin/python -m pytest automation/suites/cafepress/test_personalize_image.py::test_personalize_image_slot_add_to_cart \
  -c automation/pytest.ini -v --headed
```

### 普通商品 PDP（无定制）

参考 `automation/suites/cafepress/pages/product.py`、`test_standard_product.py`。

与 CYO 类似选 PDP 选项，但**不点 Personalize**；部分商品（马克杯、托特包）加购后会**直接跳转 `/cart`** 而非 just added 弹窗。

| 步骤 | 要点 |
|------|------|
| PDP | 随机 color；**仅选可见** size（马克杯无尺码可跳过） |
| 数量 | quantity ≥ 2（`set_random_quantity`） |
| 加购 | ADD TO CART；断言 just added 弹窗 **或** URL 为 `/cart` |
| 断言 | `/cart` 含对应商品名、subtotal、cart id |

示例 URL（各一条用例）：

- 女款 T 恤：`/+i_like_to_party_and_by_womens_comfort_colors_shirt,69974637?...`
- 马克杯：`/+funny_skeleton_as_per_my_last_email_11_oz_ceramic_mug,3016343384?...`
- 托特包：`/+worlds_best_chef_tote_bag,468223473?...`

```bash
venv/bin/python -m pytest automation/suites/cafepress/test_standard_product.py \
  -c automation/pytest.ini -v --headed
```

### 混合购物车下单

参考 `pages/cart.py`、`pages/checkout.py`、`flows/add_products.py`、`test_checkout_order.py`。

**会真实下单**，运行前设置账号（任选其一）：

1. **本地文件（推荐）**：复制 `checkout.local.json.example` → `checkout.local.json`（已在 `.gitignore`）
2. **运行配置**：`/automation` 展开「运行配置」填写「结账邮箱 / 结账密码」
3. **环境变量**：`AUTOMATION_CAFPRESS_CHECKOUT_EMAIL` / `AUTOMATION_CAFPRESS_CHECKOUT_PASSWORD`

| 步骤 | 要点 |
|------|------|
| 登录 | `/secure/checkout/login`，登录后 header 有 My Account |
| 加购 | CYO + PER 文本 + PER 图片 + 女款 T 恤 + 马克杯 + 托特包（`flows/add_products.py`） |
| Promo | Cart 页 `input[name='promo code']` → Apply；断言 promo 已生效 |
| Checkout | `.container-checkout.btn-checkout`；spinner 挡点击时 fallback 到 `?step=1` |
| 地址 step=1 | `txtFirstName/LastName/Address1/City/State/Zip/Phone` → Continue to Shipping Method |
| 配送 step=2 | 等 ≥3s → 随机 visible radio → Continue to Payment |
| 支付 step=3 | Place Your Order（timeout 默认 120s） |
| 确认 | `/secure/checkout/confirm_order`，记录 `Your order number is {orderNo}` |

```bash
venv/bin/python -m pytest automation/suites/cafepress/test_checkout_order.py::test_mixed_cart_checkout_place_order \
  -c automation/pytest.ini -v --headed
```

### 常见问题

| 现象 | 处理 |
|------|------|
| `page.goto` 超时 | 改用 `wait_until="domcontentloaded"`；检查 `dismiss_overlays()` |
| Locator not found | 有头模式看 DOM；加 `timeout=`；检查是否在 iframe |
| 断言 URL 失败 | CafePress 搜索可能跳 `/+keyword` 而非 `/search`，用更宽 regex |
| site_id 169 vs 170 | B2C=170(CAFUS)；169 可能来自跨站 sync，记录 `get_site_context()` |
| CYO 上传后 ADD 无效 | 须先点击 photo tray thumbnail，否则 Alert「Please select an image first」 |
| 登录账号 photo tray 很多 | 上传后选已加载 cloudfront 的缩略图（新增/selected/last），再点弹窗内 **ADD** |
| CYO 切 Back overlay 挡点击 | 先处理 CONFIRM 对话框点 YES；或 `click(force=True)` 仅作兜底 |
| CYO 加购 Missing Image | Front+Back 需 Back 侧有图；切 Back 后 CONFIRM→YES 应用 Front 图 |
| 浏览器未安装 | `./scripts/install-playwright.sh` |

### 调试命令

```bash
# 单用例（有头）
venv/bin/python -m pytest automation/suites/cafepress/test_auth.py::test_register_new_account \
  -c automation/pytest.ini -v --headed

# 收集不执行
venv/bin/python -m pytest automation/suites/cafepress/ -c automation/pytest.ini --collect-only -q

# 安装浏览器
./scripts/install-playwright.sh
```

## pytest Markers

定义见 `automation/pytest.ini`：

- `selected` — UI 加载用例列表时默认勾选
- `smoke` — 关键路径，界面显示「冒烟」徽章

## 测试数据 Artifacts

```python
def test_example(page, test_data):
    test_data.record_auth(action="register", email=email, password=pwd, ...)
    test_data.record_order(order_id="123", email=email, total="29.99")
```

运行后写入 `reports/{runId}/artifacts/`，UI「执行结果」展示。

### 步骤截图

用例内关键步骤调用 `save_screenshot(name, label=..., test_data=test_data)`；**截图前自动等待 ≥3s**（`AUTOMATION_DESIGN_SETTLE_MS`）让 canvas/购物车预览渲染完成。

```python
designer.save_screenshot("cyo_designer_complete", label="设计完成", test_data=test_data)
```

失败时 conftest 另存 `{testId}.png` 作为「失败截图」一并展示。

## 全局 Fixtures

`automation/conftest.py` 提供：

- `test_data` — 记录业务数据
- `browser_context_args` — 读 `AUTOMATION_VIEWPORT_*`、`AUTOMATION_LOCALE`
- `page` — 设置 `AUTOMATION_TIMEOUT`
- 失败自动截图到 `AUTOMATION_SCREENSHOTS_DIR`

## 额外资源

- 完整示例：[examples.md](examples.md)
- 命令/API/环境变量：[reference.md](reference.md)
- 用户文档：`docs/USAGE.md` UI 自动化章节
