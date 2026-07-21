"""CafePress 套件专用 fixtures"""
import os

import pytest

from pages.auth import LoginPage, RegisterPage
from pages.cart import CartPage
from pages.checkout import CheckoutPage
from pages.designer import DesignerPage
from pages.homepage import HomePage
from pages.personalize import PersonalizePage
from pages.product import ProductPage
from pages.search import SearchPage


def _checkout_timeout_ms() -> int:
    try:
        return int(os.environ.get("AUTOMATION_CHECKOUT_TIMEOUT", "120000"))
    except (TypeError, ValueError):
        return 120_000


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
    email = os.environ.get("AUTOMATION_CAFPRESS_CHECKOUT_EMAIL", "").strip()
    password = os.environ.get("AUTOMATION_CAFPRESS_CHECKOUT_PASSWORD", "").strip()
    if not email or not password:
        pytest.skip(
            "Set AUTOMATION_CAFPRESS_CHECKOUT_EMAIL and "
            "AUTOMATION_CAFPRESS_CHECKOUT_PASSWORD to run checkout order test"
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
