"""CafePress Personalize 产品：固定 image slot 上传加购流程"""
import re

import pytest
from playwright.sync_api import expect

from pages.cart import CartPage


@pytest.mark.selected
@pytest.mark.smoke
def test_personalize_image_slot_add_to_cart(personalize, cart: CartPage, test_data):
    personalize.open_image_slot_pdp()
    color = personalize.select_random_color()
    size = personalize.select_random_size()
    quantity = personalize.set_random_quantity()
    personalize.enter_image_designer()

    image = personalize.upload_slot_image()
    personalize.save_screenshot("personalize_image_complete", label="图片上传完成", test_data=test_data)
    personalize.add_to_cart()
    # personalize.save_screenshot("personalize_image_after_atc", label="加购成功", test_data=test_data)

    cart.open()
    cart.wait_for_loaded()
    personalize.save_screenshot("personalize_image_cart", label="购物车", test_data=test_data)
    expect(cart.page).to_have_url(re.compile(r"/cart", re.I))
    expect(cart.page.locator("body")).to_contain_text(
        re.compile(r"add your own image.*long sleeve", re.I)
    )
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"cart id:", re.I))
    expect(cart.page.locator("body")).to_contain_text(re.compile(r"subtotal", re.I))

    test_data.update({
        "action": "personalize_image_add_to_cart",
        "product": "personalize_image_long_sleeve",
        "color": color,
        "size": size,
        "quantity": quantity,
        "image": image.name,
    })
