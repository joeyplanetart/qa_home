"""CafePress 套件专用 fixtures"""
import pytest

from pages.auth import LoginPage, RegisterPage
from pages.cart import CartPage
from pages.designer import DesignerPage
from pages.homepage import HomePage
from pages.personalize import PersonalizePage
from pages.product import ProductPage
from pages.search import SearchPage


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
def designer(page):
    return DesignerPage(page)


@pytest.fixture
def personalize(page):
    return PersonalizePage(page)
