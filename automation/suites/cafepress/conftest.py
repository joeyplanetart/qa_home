"""CafePress 套件专用 fixtures"""
import json
import os
from pathlib import Path

import pytest

from pages.auth import LoginPage, RegisterPage
from pages.cart import CartPage
from pages.checkout import CheckoutPage
from pages.designer import DesignerPage
from pages.homepage import HomePage
from pages.personalize import PersonalizePage
from pages.product import ProductPage
from pages.search import SearchPage

_CHECKOUT_CREDENTIALS_FILE = Path(__file__).with_name("checkout.local.json")


def _checkout_timeout_ms() -> int:
    try:
        return int(os.environ.get("AUTOMATION_CHECKOUT_TIMEOUT", "120000"))
    except (TypeError, ValueError):
        return 120_000


def _load_checkout_credentials() -> tuple[str, str]:
    email = os.environ.get("AUTOMATION_CAFPRESS_CHECKOUT_EMAIL", "").strip()
    password = os.environ.get("AUTOMATION_CAFPRESS_CHECKOUT_PASSWORD", "").strip()
    if email and password:
        return email, password

    if _CHECKOUT_CREDENTIALS_FILE.is_file():
        try:
            data = json.loads(_CHECKOUT_CREDENTIALS_FILE.read_text(encoding="utf-8"))
            email = str(data.get("email", "")).strip()
            password = str(data.get("password", "")).strip()
            if email and password:
                return email, password
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    return "", ""


@pytest.fixture
def login(page):
    return LoginPage(page)


@pytest.fixture
def register(page):
    return RegisterPage(page)


@pytest.fixture
def home(page):
    return HomePage(page)


@pytest.fixture
def search(page):
    return SearchPage(page)


@pytest.fixture
def product(page):
    return ProductPage(page)


@pytest.fixture
def cart(page):
    return CartPage(page)


@pytest.fixture
def checkout_account():
    email, password = _load_checkout_credentials()
    if not email or not password:
        pytest.skip(
            "缺少下单账号：在运行配置填写结账邮箱/密码，或复制 "
            "checkout.local.json.example 为 checkout.local.json"
        )
    return {"email": email, "password": password}


@pytest.fixture
def checkout(page):
    timeout = _checkout_timeout_ms()
    page.set_default_timeout(timeout)
    page.set_default_navigation_timeout(timeout)
    return CheckoutPage(page)


@pytest.fixture
def designer(page):
    return DesignerPage(page)


@pytest.fixture
def personalize(page):
    return PersonalizePage(page)
