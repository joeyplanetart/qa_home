"""CafePress 搜索结果页"""
from __future__ import annotations

from urllib.parse import quote

from playwright.sync_api import Locator

from .base import BasePage


class SearchPage(BasePage):
    def open_query(self, keyword: str) -> None:
        self.open(f"/search?q={quote(keyword)}")

    @property
    def product_cards(self) -> Locator:
        return self.page.locator("a.product-card")

    def open_first_result(self) -> None:
        self.product_cards.first.click()
