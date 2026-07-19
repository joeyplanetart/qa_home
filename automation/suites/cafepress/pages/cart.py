"""CafePress 购物车页"""
from __future__ import annotations

from playwright.sync_api import Locator

from .base import BasePage


class CartPage(BasePage):
    def open(self, path: str = "/cart") -> None:
        super().open(path)

    @property
    def cart_link(self) -> Locator:
        return self.page.get_by_role("link", name="Cart")
