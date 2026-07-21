"""加购流程：供下单 E2E 复用（与各 test_*.py 场景一致）。"""
from __future__ import annotations

from pages.designer import DesignerPage
from pages.personalize import PersonalizePage
from pages.product import ProductPage


def add_cyo_product(designer: DesignerPage, *, quantity: int = 1) -> None:
    designer.open_cyo_pdp()
    designer.select_position("Front + Back")
    designer.select_random_color()
    designer.select_random_size()
    designer.set_quantity(quantity)
    designer.enter_designer()
    designer.upload_image()
    designer.switch_to_back()
    designer.add_to_cart()


def add_personalize_text_product(personalize: PersonalizePage, *, quantity: int = 1) -> None:
    personalize.open_personalize_pdp()
    personalize.select_random_color()
    personalize.select_random_size()
    personalize.set_quantity(quantity)
    personalize.enter_text_designer()
    personalize.edit_text_slot()
    personalize.add_to_cart()


def add_personalize_image_product(personalize: PersonalizePage, *, quantity: int = 1) -> None:
    personalize.open_image_slot_pdp()
    personalize.select_random_color()
    personalize.select_random_size()
    personalize.set_quantity(quantity)
    personalize.enter_image_designer()
    personalize.upload_slot_image()
    personalize.add_to_cart()


def add_standard_shirt(product: ProductPage, *, quantity: int = 1) -> None:
    product.open_womens_shirt_pdp()
    product.select_random_color()
    product.select_random_size()
    product.set_quantity(quantity)
    product.add_to_cart()


def add_standard_mug(product: ProductPage, *, quantity: int = 1) -> None:
    product.open_funny_skeleton_mug_pdp()
    product.select_random_color()
    product.set_quantity(quantity)
    product.add_to_cart()


def add_standard_tote(product: ProductPage, *, quantity: int = 1) -> None:
    product.open_worlds_best_chef_tote_pdp()
    product.select_random_color()
    product.select_random_size()
    product.set_quantity(quantity)
    product.add_to_cart()


def add_mixed_cart_products(
    designer: DesignerPage,
    personalize: PersonalizePage,
    product: ProductPage,
    *,
    quantity: int = 1,
) -> None:
    """CYO + PER 文本 + PER 图片 + 1 件普通商品（下单用，避免多件普通商品跳转 /cart 重复加购）。"""
    add_cyo_product(designer, quantity=quantity)
    add_personalize_text_product(personalize, quantity=quantity)
    add_personalize_image_product(personalize, quantity=quantity)
    add_standard_shirt(product, quantity=quantity)
