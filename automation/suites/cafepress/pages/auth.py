"""CafePress 登录 / 注册页"""
from __future__ import annotations

import re
import time
import uuid

from playwright.sync_api import Locator, Page

from .base import BasePage

LOGIN_PATH = "/secure/checkout/login"
REGISTER_PATH = "/secure/checkout/register?redirect=/"
TEST_PASSWORD = "Test1234"


def make_test_email() -> str:
    return f"qa.auto.{int(time.time())}.{uuid.uuid4().hex[:6]}@planetart.com"


class LoginPage(BasePage):
    def open(self, path: str = LOGIN_PATH) -> None:
        super().open(path)

    @property
    def form(self) -> Locator:
        return self.page.locator("#form-login")

    @property
    def email_input(self) -> Locator:
        return self.form.locator('input[name="email"]')

    @property
    def password_input(self) -> Locator:
        return self.form.locator('input[name="password"]')

    @property
    def sign_in_button(self) -> Locator:
        return self.form.locator('input[type="submit"]')

    def sign_in(self, email: str, password: str) -> None:
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.sign_in_button.click()


class RegisterPage(BasePage):
    def open(self, path: str = REGISTER_PATH) -> None:
        super().open(path)

    @property
    def form(self) -> Locator:
        return self.page.locator("#form-register")

    @property
    def create_account_button(self) -> Locator:
        return self.form.locator('input[type="submit"]')

    def register(
        self,
        email: str,
        password: str = TEST_PASSWORD,
        first_name: str = "QA",
        last_name: str = "Automation",
    ) -> None:
        self.form.locator('input[name="txtFirstName"]').fill(first_name)
        self.form.locator('input[name="txtLastName"]').fill(last_name)
        self.form.locator('input[name="txtEmail"]').fill(email)
        self.form.locator('input[name="txtPassword"]').fill(password)
        self.create_account_button.click()


def expect_logged_in(page: Page) -> Locator:
    """注册/登录成功后 header 会出现 My Account 链接。"""
    return page.locator('a[title="My Account"]')


CAFEPRESS_B2C_SITE_ID = 170
CAFEPRESS_B2B_SITE_ID = 169


def get_site_context(page: Page) -> dict[str, str | int | None]:
    """读取当前页面的站点上下文（SITE_ID / body class / URL）。"""
    try:
        ctx = page.evaluate(
            """() => {
                const bodyClass = document.body.className || '';
                const match = bodyClass.match(/\\b(CAFUS|CPBUS|PCBUS)\\b/);
                return {
                    site_id: window.SITE_ID ?? null,
                    site_code: match ? match[1] : null,
                    url: window.location.href,
                };
            }"""
        )
        if isinstance(ctx, dict):
            return ctx
    except Exception:
        pass
    return {"site_id": None, "site_code": None, "url": page.url}


def get_customer_id(page: Page) -> str | None:
    """从 cookie / 页面 JS 变量中提取 customer_id。"""
    try:
        page.wait_for_function(
            """() => {
                if (window.customer_id || window.customerId) return true;
                if (!Array.isArray(window.dataLayer)) return false;
                return window.dataLayer.some(item =>
                    item && (item.customer_id || item.customerId || item.user_id || item.userId)
                );
            }""",
            timeout=5000,
        )
    except Exception:
        pass

    cookie_names = {
        "customer_id",
        "customerid",
        "user_id",
        "userid",
        "cp_customer_id",
    }
    for cookie in page.context.cookies():
        name = cookie.get("name", "").lower()
        if name in cookie_names and cookie.get("value"):
            return str(cookie["value"])

    try:
        customer_id = page.evaluate(
            """() => {
                const pick = (obj) => {
                    if (!obj || typeof obj !== 'object') return null;
                    for (const key of ['customer_id', 'customerId', 'user_id', 'userId']) {
                        if (obj[key]) return String(obj[key]);
                    }
                    return null;
                };
                if (window.customer_id) return String(window.customer_id);
                if (window.customerId) return String(window.customerId);
                if (Array.isArray(window.dataLayer)) {
                    for (const item of window.dataLayer) {
                        const found = pick(item);
                        if (found) return found;
                    }
                }
                return null;
            }"""
        )
        if customer_id:
            return str(customer_id)
    except Exception:
        pass

    try:
        profile_href = page.locator('a[title="My Account"]').first.get_attribute("href") or ""
        for pattern in (r"/profile/(\d+)", r"customer[_-]?id=(\d+)", r"/(\d+)/profile"):
            match = re.search(pattern, profile_href, re.I)
            if match:
                return match.group(1)
    except Exception:
        pass

    return None
