"""CafePress 商品详情页"""
from __future__ import annotations

import re

from playwright.sync_api import Locator

from .base import BasePage


class ProductPage(BasePage):
    @property
    def title(self) -> Locator:
        return self.page.locator("h1").first

    @property
    def add_to_cart_button(self) -> Locator:
        return self.page.get_by_role(
            "button",
            name=re.compile(r"add to cart|add to bag", re.I),
        )

    def add_to_cart(self) -> None:
        self.add_to_cart_button.click()
