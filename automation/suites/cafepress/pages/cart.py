"""CafePress 购物车页"""
from __future__ import annotations

import re

from playwright.sync_api import Locator, expect

from .base import BasePage


class CartPage(BasePage):
    def open(self, path: str = "/cart") -> None:
        super().open(path)

    def wait_for_loaded(self) -> None:
        expect(self.page.locator("body")).to_contain_text(re.compile(r"shopping cart", re.I))
        expect(self.page.locator("body")).not_to_contain_text(
            re.compile(r"your (shopping )?cart is empty", re.I)
        )

    @property
    def cart_link(self) -> Locator:
        return self.page.get_by_role("link", name="Cart")
