"""CafePress 首页"""
from __future__ import annotations

from playwright.sync_api import Locator

from .base import BasePage


class HomePage(BasePage):
    @property
    def header(self) -> Locator:
        return self.page.locator("header.site-header-wrapper")

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...")

    @property
    def bestseller_cards(self) -> Locator:
        return self.page.locator("a.product-card")

    def search(self, keyword: str) -> None:
        self.search_input.fill(keyword)
        self.search_input.press("Enter")

    def open_cart(self) -> None:
        self.page.get_by_role("link", name="Cart").click()
