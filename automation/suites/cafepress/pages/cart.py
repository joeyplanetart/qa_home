"""CafePress 购物车页"""
from __future__ import annotations

import re

from playwright.sync_api import Locator, expect

from .base import BasePage, CAFEPRESS_US

CHECKOUT_PAYMENT_STEP1 = "/secure/checkout/payment?step=1"


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

    @property
    def promo_code_input(self) -> Locator:
        return self.page.locator("input[name='promo code']")

    @property
    def apply_promo_button(self) -> Locator:
        return self.page.locator("input.container-combobox-btn[value='Apply']")

    @property
    def checkout_button(self) -> Locator:
        return self.page.locator(".container-checkout.btn-checkout")

    def wait_for_cart_update(self) -> None:
        """Promo / 价格更新后等待 loading overlay 消失。"""
        overlay = self.page.locator(".loading_spinner .spinner-overlay-bg")
        if overlay.count():
            try:
                overlay.first.wait_for(state="hidden", timeout=60_000)
            except Exception:
                self.page.wait_for_timeout(3000)

    def apply_promo_code(self, code: str) -> None:
        expect(self.promo_code_input).to_be_visible()
        self.promo_code_input.fill(code)
        self.apply_promo_button.click()
        expect(self.page.locator("body")).to_contain_text(
            re.compile(rf"{re.escape(code)}|discount", re.I),
            timeout=30_000,
        )
        self.wait_for_cart_update()

    def proceed_to_checkout(self) -> None:
        """点击 CHECKOUT；若 spinner 挡点击则直接打开 step=1。"""
        self.wait_for_cart_update()
        checkout = self.checkout_button
        try:
            expect(checkout).to_be_visible(timeout=10_000)
            checkout.click(timeout=15_000)
        except Exception:
            pass
        if not re.search(r"/secure/checkout/payment", self.page.url, re.I):
            self.page.goto(
                f"{CAFEPRESS_US}{CHECKOUT_PAYMENT_STEP1}",
                wait_until="domcontentloaded",
            )
        expect(self.page).to_have_url(
            re.compile(r"/secure/checkout/payment\?step=1", re.I),
            timeout=30_000,
        )
