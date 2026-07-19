"""CafePress 关键路径冒烟：浏览 → 搜索 → 查看商品"""
import re

import pytest
from playwright.sync_api import expect

from pages.homepage import HomePage
from pages.product import ProductPage
from pages.search import SearchPage


@pytest.mark.smoke
@pytest.mark.selected
def test_browse_search_and_view_product(page):
    """完整用户旅程 smoke：首页 → 搜索 → 商品详情（不含登录结账）。"""
    home = HomePage(page)
    search = SearchPage(page)
    product = ProductPage(page)

    home.open()
    expect(home.header).to_be_visible()
    expect(home.bestseller_cards.first).to_be_visible()

    home.search("mug")
    expect(page).to_have_url(re.compile(r"/search", re.I))
    expect(search.product_cards.first).to_be_visible()

    search.open_first_result()
    expect(product.title).to_be_visible()
    expect(product.add_to_cart_button).to_be_visible()
