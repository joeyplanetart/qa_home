"""CafePress 购物车测试"""
import re

from playwright.sync_api import expect


def test_cart_page_loads(cart):
    cart.open()
    expect(cart.page).to_have_url(re.compile(r"/cart", re.I))


def test_cart_link_from_homepage(home, cart):
    home.open()
    home.open_cart()
    expect(cart.page).to_have_url(re.compile(r"/cart", re.I))
