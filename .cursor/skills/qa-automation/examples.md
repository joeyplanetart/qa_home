# QA Automation 示例

## 1. BasePage（pages/base.py）

```python
class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self, path: str = "") -> None:
        url = f"{BASE_URL}{path}" if path else BASE_URL
        self.page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
        self.dismiss_overlays()
```

## 2. Page Object（pages/homepage.py）

```python
class HomePage(BasePage):
    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...")

    def search(self, keyword: str) -> None:
        self.search_input.fill(keyword)
        self.search_input.press("Enter")
```

## 3. conftest.py fixtures

```python
@pytest.fixture
def home(page):
    return HomePage(page)
```

## 4. 页面加载测试

```python
def test_login_page_loads(login):
    login.open()
    expect(login.form).to_be_visible()
    expect(login.email_input).to_be_visible()
```

## 5. 业务流程 + 默认选中 + 测试数据

```python
@pytest.mark.selected
def test_register_new_account(register, page, test_data):
    email = make_test_email()
    register.open()
    register.register(email=email)
    expect(expect_logged_in(page)).to_be_visible(timeout=30_000)
    test_data.record_auth(
        action="register",
        email=email,
        password=TEST_PASSWORD,
        customer_id=get_customer_id(page),
        site_id=get_site_context(page).get("site_id"),
        expected_site_id=CAFEPRESS_B2C_SITE_ID,
    )
```

## 6. 冒烟路径

```python
@pytest.mark.smoke
@pytest.mark.selected
def test_browse_search_and_view_product(page):
    home = HomePage(page)
    search = SearchPage(page)
    product = ProductPage(page)
    home.open()
    home.search("mug")
    expect(page).to_have_url(re.compile(r"search|\+", re.I))
    search.open_first_result()
    expect(product.title).to_be_visible()
```

## 7. 新套件 scaffold

```
automation/suites/mysite/
├── meta.json              # { "name": "...", "projectId": 123 }
├── conftest.py            # Page fixtures
├── pages/
│   ├── __init__.py
│   └── base.py
└── test_homepage.py
```

## 8. CafePress 参考实现

现有完整套件：`automation/suites/cafepress/`

| 文件 | 用途 |
|------|------|
| `pages/auth.py` | 登录/注册、make_test_email、site context |
| `pages/homepage.py` | 首页搜索、购物车入口 |
| `test_auth.py` | 认证流程 + test_data |
| `test_checkout_flow.py` | smoke 用户旅程 |

生成新用例时 **先读同套件已有文件**，保持风格一致。
