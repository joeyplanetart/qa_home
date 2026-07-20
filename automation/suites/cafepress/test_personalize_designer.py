"""CafePress Personalize 产品：固定 slot 文本编辑加购流程"""
import re

import pytest
from playwright.sync_api import expect

from pages.cart import CartPage


@pytest.mark.selected
@pytest.mark.smoke
def test_personalize_edit_text_add_to_cart(personalize, cart: CartPage, test_data):
    personalize.open_personalize_pdp()
    color = personalize.select_random_color()
    size = personalize.select_random_size()
    personalize.set_quantity(2)
    personalize.enter_text_designer()

    custom_text = personalize.edit_text_slot()
    personalize.save_screenshot("personalize_text_complete", label="文本编辑完成", test_data=test_data)
    personalize.add_to_cart()

    cart.open()
    cart.wait_for_loaded()
    personalize.save_screenshot("personalize_cart_after_add", label="加购后购物车", test_data=test_data)
    expect(cart.page).to_have_url(re.compile(r"/cart", re.I))
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"cart id:", re.I))
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"subtotal", re.I))

    test_data.update({
        "action": "personalize_add_to_cart",
        "product": "personalize_mens_classic_tee",
        "color": color,
        "size": size,
        "quantity": 2,
        "custom_text": custom_text,
    })
