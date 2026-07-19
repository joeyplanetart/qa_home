"""CafePress CYO Designer：Front+Back 定制 T 恤加购流程"""
import re

import pytest
from playwright.sync_api import expect

from pages.cart import CartPage


@pytest.mark.selected
@pytest.mark.smoke
def test_cyo_front_back_personalize_add_to_cart(designer, cart: CartPage, test_data):
    designer.open_cyo_pdp()
    designer.select_position("Front + Back")
    color = designer.select_random_color()
    size = designer.select_random_size()
    designer.set_quantity(2)
    designer.enter_designer()

    image = designer.upload_image()
    designer.switch_to_back()
    designer.save_screenshot("cyo_designer_complete", label="设计完成", test_data=test_data)
    designer.add_to_cart()

    cart.open()
    designer.save_screenshot("cyo_cart_after_add", label="加购后购物车", test_data=test_data)
    expect(cart.page).to_have_url(re.compile(r"/cart", re.I))
    expect(cart.page.locator("body")).to_contain_text(
        re.compile(r"custom men's value t-shirt", re.I)
    )
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"subtotal", re.I))
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"cart id:", re.I))

    test_data.update({
        "action": "cyo_add_to_cart",
        "product": "custom_mens_value_tee",
        "position": "Front + Back",
        "color": color,
        "size": size,
        "quantity": 2,
        "image": image.name,
    })
