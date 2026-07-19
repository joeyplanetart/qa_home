"""CafePress 商品详情页测试"""
from playwright.sync_api import expect


def test_product_detail_page_loads(search, product):
    search.open_query("mug")
    expect(search.product_cards.first).to_be_visible()
    search.open_first_result()
    expect(product.title).to_be_visible()


def test_product_detail_has_add_to_cart(search, product):
    search.open_query("mug")
    search.open_first_result()
    expect(product.add_to_cart_button).to_be_visible()
