"""CafePress 混合购物车下单：登录 → 多类型加购 → Promo → Checkout → 下单确认"""
import re

import pytest
from playwright.sync_api import expect

from flows.add_products import add_mixed_cart_products
from pages.auth import expect_logged_in
from pages.cart import CartPage
from pages.checkout import PROMO_CODE


@pytest.mark.selected
@pytest.mark.smoke
def test_mixed_cart_checkout_place_order(
    checkout,
    login,
    designer,
    personalize,
    product,
    cart: CartPage,
    checkout_account,
    page,
    test_data,
):
    """登录 → CYO/PER/普通商品加购 → promo → 填写地址 → 下单并记录 order number。"""
    login.open()
    login.sign_in(checkout_account["email"], checkout_account["password"])
    expect(expect_logged_in(page)).to_be_visible(timeout=30_000)
    test_data.set("email", checkout_account["email"])

    cart.open()
    cart.clear_all_items()

    add_mixed_cart_products(designer, personalize, product, quantity=1)
    designer.save_screenshot("checkout_all_added", label="全部加购完成", test_data=test_data)

    cart.open()
    cart.wait_for_loaded()
    cart.apply_promo_code(PROMO_CODE)
    designer.save_screenshot("checkout_cart_promo", label="Promo 已应用", test_data=test_data)
    cart.proceed_to_checkout()

    checkout.wait_for_step1_ready()
    address = checkout.fill_random_us_address()
    designer.save_screenshot("checkout_shipping_address", label="收货地址", test_data=test_data)
    checkout.continue_to_shipping_method()

    shipping_method = checkout.select_random_shipping_method()
    designer.save_screenshot("checkout_shipping_method", label="配送方式", test_data=test_data)
    checkout.continue_to_payment()

    order_number = checkout.place_order_and_get_order_number()
    designer.save_screenshot("checkout_confirm_order", label="下单成功", test_data=test_data)

    test_data.record_order(
        order_id=order_number,
        email=checkout_account["email"],
        promo_code=PROMO_CODE,
        shipping_address=address,
        shipping_method=shipping_method,
        action="mixed_cart_checkout",
    )
