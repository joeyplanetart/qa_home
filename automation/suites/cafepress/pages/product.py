"""CafePress 普通商品详情页（无 Personalize / 定制）"""
from __future__ import annotations

import random
import re

from playwright.sync_api import Locator, expect

from .designer import DesignerPage, SIZE_PATTERN

WOMENS_COMFORT_COLORS_SHIRT = (
    "/+i_like_to_party_and_by_womens_comfort_colors_shirt,69974637"
    "?attr2=9025&default_pos=front"
)
FUNNY_SKELETON_MUG = (
    "/+funny_skeleton_as_per_my_last_email_11_oz_ceramic_mug,3016343384"
    "?attr2=12772&default_pos=front"
)
WORLDS_BEST_CHEF_TOTE = (
    "/+worlds_best_chef_tote_bag,468223473"
    "?attr4=8925&default_pos=front"
)


class ProductPage(DesignerPage):
    @property
    def title(self) -> Locator:
        return self.page.locator("h1").first

    def open_product(self, path: str) -> None:
        self.open(path)

    def open_womens_shirt_pdp(self) -> None:
        self.open(WOMENS_COMFORT_COLORS_SHIRT)

    def open_funny_skeleton_mug_pdp(self) -> None:
        self.open(FUNNY_SKELETON_MUG)

    def open_worlds_best_chef_tote_pdp(self) -> None:
        self.open(WORLDS_BEST_CHEF_TOTE)

    def select_random_color(self) -> str | None:
        """随机选可见颜色；仅一种且已预选时可能不可见，直接读当前值。"""
        options = self.color_options
        visible_indices = [
            i for i in range(options.count()) if options.nth(i).is_visible()
        ]
        if not visible_indices:
            if options.count() == 0:
                return None
            choice = options.filter(has=self.page.locator(".selected")).first
            if choice.count() == 0:
                choice = options.first
            color = (
                choice.get_attribute("title")
                or choice.get_attribute("data-caption")
                or choice.get_attribute("aria-label")
                or ""
            ).strip()
            self.last_color = color or None
            return self.last_color
        choice = options.nth(random.choice(visible_indices))
        choice.click()
        color = (
            choice.get_attribute("title")
            or choice.get_attribute("data-caption")
            or choice.get_attribute("aria-label")
            or choice.inner_text()
        ).strip()
        if not color:
            color = f"color-{random.randrange(len(visible_indices))}"
        self.last_color = color
        return color

    def select_random_size(self) -> str | None:
        """仅选择可见的尺码；马克杯等无尺码商品返回 None。"""
        sizes: list[str] = []
        for i in range(self.text_options.count()):
            item = self.text_options.nth(i)
            if not item.is_visible():
                continue
            text = item.locator(".option-text").inner_text().strip()
            if SIZE_PATTERN.match(text):
                sizes.append(text)
        if not sizes:
            return None
        label = random.choice(sizes)
        self.select_text_option(label)
        self.last_size = label
        return label

    def configure_options(self, quantity: int | None = None) -> dict[str, object]:
        color = self.select_random_color()
        size = self.select_random_size()
        if quantity is None:
            qty = self.set_random_quantity()
        else:
            self.set_quantity(quantity)
            qty = quantity
        return {"color": color, "size": size, "quantity": qty}

    def add_to_cart(self) -> None:
        expect(self.add_to_cart_button).to_be_enabled()
        self.add_to_cart_button.click()
        just_added = self.page.get_by_text(re.compile(r"just added to your cart", re.I))
        try:
            expect(just_added).to_be_visible(timeout=8_000)
        except AssertionError:
            expect(self.page).to_have_url(re.compile(r"/cart", re.I), timeout=30_000)
