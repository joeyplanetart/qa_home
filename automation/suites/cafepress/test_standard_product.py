"""CafePress 普通商品 PDP：选色/尺码/数量后直接加购（无 Personalize）"""
import re

import pytest
from playwright.sync_api import expect

from pages.cart import CartPage


def _ensure_cart(product, cart: CartPage) -> None:
    if not re.search(r"/cart", product.page.url, re.I):
        cart.open()
    cart.wait_for_loaded()


@pytest.mark.selected
@pytest.mark.smoke
def test_standard_womens_shirt_add_to_cart(product, cart: CartPage, test_data):
    product.open_womens_shirt_pdp()
    options = product.configure_options()
    product.save_screenshot("standard_shirt_pdp", label="女款 T 恤 PDP", test_data=test_data)
    product.add_to_cart()

    _ensure_cart(product, cart)
    product.save_screenshot("standard_shirt_cart", label="购物车", test_data=test_data)
    expect(cart.page).to_have_url(re.compile(r"/cart", re.I))
    expect(cart.page.locator("body")).to_contain_text(
        re.compile(r"i like to party.*comfort colors", re.I)
    )
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"subtotal", re.I))
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"cart id:", re.I))

    test_data.update({
        "action": "standard_add_to_cart",
        "product": "womens_comfort_colors_shirt",
        **options,
    })


@pytest.mark.selected
@pytest.mark.smoke
def test_standard_ceramic_mug_add_to_cart(product, cart: CartPage, test_data):
    product.open_funny_skeleton_mug_pdp()
    options = product.configure_options()
    product.save_screenshot("standard_mug_pdp", label="马克杯 PDP", test_data=test_data)
    product.add_to_cart()

    _ensure_cart(product, cart)
    product.save_screenshot("standard_mug_cart", label="购物车", test_data=test_data)
    expect(cart.page).to_have_url(re.compile(r"/cart", re.I))
    expect(cart.page.locator("body")).to_contain_text(
        re.compile(r"funny skeleton.*ceramic mug", re.I)
    )
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"subtotal", re.I))
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"cart id:", re.I))

    test_data.update({
        "action": "standard_add_to_cart",
        "product": "funny_skeleton_ceramic_mug",
        **options,
    })


@pytest.mark.selected
@pytest.mark.smoke
def test_standard_tote_bag_add_to_cart(product, cart: CartPage, test_data):
    product.open_worlds_best_chef_tote_pdp()
    options = product.configure_options()
    product.save_screenshot("standard_tote_pdp", label="托特包 PDP", test_data=test_data)
    product.add_to_cart()

    _ensure_cart(product, cart)
    product.save_screenshot("standard_tote_cart", label="购物车", test_data=test_data)
    expect(cart.page).to_have_url(re.compile(r"/cart", re.I))
    expect(cart.page.locator("body")).to_contain_text(
        re.compile(r"world.*best chef", re.I)
    )
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"subtotal", re.I))
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"cart id:", re.I))

    test_data.update({
        "action": "standard_add_to_cart",
        "product": "worlds_best_chef_tote_bag",
        **options,
    })
