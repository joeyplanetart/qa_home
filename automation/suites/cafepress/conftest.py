"""CafePress 套件专用 fixtures"""
import pytest

from pages.cart import CartPage
from pages.homepage import HomePage
from pages.product import ProductPage
from pages.search import SearchPage


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
