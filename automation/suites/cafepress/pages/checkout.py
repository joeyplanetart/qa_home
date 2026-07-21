"""CafePress 结账流程（Shipping → Payment → Confirm）"""
from __future__ import annotations

import os
import random
import re
import uuid
from typing import Callable, TypedDict

from playwright.sync_api import Locator, expect

from .base import BasePage, CAFEPRESS_US

CHECKOUT_PAYMENT_STEP1 = "/secure/checkout/payment?step=1"
CHECKOUT_CONFIRM = "/secure/checkout/confirm_order"
PROMO_CODE = "qa_ppal_code"
ORDER_NUMBER_RE = re.compile(r"Your order number is\s*(\d+)", re.I)
SHIPPING_SETTLE_MS = int(os.environ.get("AUTOMATION_DESIGN_SETTLE_MS", "3000"))
PLACE_ORDER_TIMEOUT_MS = int(os.environ.get("AUTOMATION_PLACE_ORDER_TIMEOUT_MS", "120000"))

US_ADDRESSES = [
    ("Los Angeles", "CA", "90001"),
    ("New York", "NY", "10001"),
    ("Chicago", "IL", "60601"),
    ("Houston", "TX", "77001"),
    ("Phoenix", "AZ", "85001"),
    ("Seattle", "WA", "98101"),
    ("Denver", "CO", "80201"),
    ("Atlanta", "GA", "30301"),
]
STREET_NAMES = ("QA Automation Ln", "Test Order Way", "Auto Ship St", "E2E Checkout Rd")


class ShippingAddress(TypedDict):
    first_name: str
    last_name: str
    address1: str
    city: str
    state: str
    zip: str
    phone: str


def make_us_shipping_address() -> ShippingAddress:
    city, state, zip_code = random.choice(US_ADDRESSES)
    suffix = uuid.uuid4().hex[:4]
    return {
        "first_name": "QA",
        "last_name": f"Auto{suffix}",
        "address1": f"{random.randint(100, 9999)} {random.choice(STREET_NAMES)}",
        "city": city,
        "state": state,
        "zip": zip_code,
        "phone": f"310555{random.randint(1000, 9999)}",
    }


class CheckoutPage(BasePage):
    @property
    def shipping_form(self) -> Locator:
        return self.page.locator(".checkout-address-form:visible").first

    @property
    def first_name_input(self) -> Locator:
        return self.shipping_form.locator(
            "input[name='shipping_firstname'], input[name='txtFirstName']"
        ).first

    @property
    def last_name_input(self) -> Locator:
        return self.shipping_form.locator(
            "input[name='shipping_lastname'], input[name='txtLastName']"
        ).first

    @property
    def address1_input(self) -> Locator:
        return self.shipping_form.locator(
            "input[name='shipping_address1'], input[name='txtAddress1']"
        ).first

    @property
    def city_input(self) -> Locator:
        return self.shipping_form.locator(
            "input[name='shipping_city'], input[name='txtCity']"
        ).first

    @property
    def state_select(self) -> Locator:
        return self.shipping_form.locator(
            "select[name='shipping_state'], select[name='txtState']"
        ).first

    @property
    def zip_input(self) -> Locator:
        return self.shipping_form.locator(
            "input[name='shipping_zip'], input[name='txtZip']"
        ).first

    @property
    def phone_input(self) -> Locator:
        return self.shipping_form.locator(
            "input[name='shipping_phone'], input[name='txtPhone']"
        ).first

    @property
    def country_select(self) -> Locator:
        return self.page.locator("select[name='shipping_country']:visible").first

    @property
    def shipping_method_radios(self) -> Locator:
        return self.page.locator("input[type='radio']:visible")

    def wait_for_step1_ready(self) -> None:
        expect(self.page).to_have_url(re.compile(r"/secure/checkout/payment\?step=1", re.I), timeout=30_000)
        expect(self.first_name_input).to_be_visible(timeout=30_000)

    def open_step1(self) -> None:
        self.open(CHECKOUT_PAYMENT_STEP1)
        self.wait_for_step1_ready()

    def fill_shipping_address(self, address: ShippingAddress | None = None) -> ShippingAddress:
        data = address or make_us_shipping_address()
        self.wait_for_step1_ready()
        expect(self.shipping_form).to_be_visible(timeout=30_000)
        if self.country_select.count():
            self.country_select.select_option(value="1")
        self.first_name_input.fill(data["first_name"])
        self.last_name_input.fill(data["last_name"])
        self.address1_input.fill(data["address1"])
        self._dismiss_address_autocomplete()
        self.city_input.fill(data["city"])
        self.state_select.select_option(value=data["state"])
        self.zip_input.fill(data["zip"])
        self.phone_input.fill(data["phone"])
        self._dismiss_address_autocomplete()
        return data

    def fill_random_us_address(self) -> ShippingAddress:
        return self.fill_shipping_address(make_us_shipping_address())

    def _dismiss_address_autocomplete(self) -> None:
        self.page.keyboard.press("Escape")
        overlay = self.page.locator(
            ".pac-container, .ui-autocomplete:visible, .address-autocomplete:visible"
        )
        if overlay.count():
            self.page.keyboard.press("Escape")

    def _click_continue(self, label_pattern: str) -> None:
        pattern = re.compile(label_pattern, re.I)
        for selector in (
            ".checkout-shipping-address .g-btn",
            ".shipping-address-section .g-btn",
            ".checkout-left .g-btn",
            ".g-btn",
            "a, button, input[type='submit'], input[type='button']",
        ):
            button = self.page.locator(selector).filter(has_text=pattern).first
            try:
                if button.count() and button.is_visible():
                    button.click(force=True)
                    return
            except Exception:
                continue
        button = self.page.get_by_text(pattern).first
        expect(button).to_be_visible(timeout=30_000)
        button.click(force=True)

    def _dismiss_address_not_verified_modal(self) -> bool:
        """随机测试地址常无法通过校验；弹窗出现时点击 CONTINUE ANYWAY。"""
        title = self.page.get_by_text(re.compile(r"address not verified", re.I))
        if not title.count() or not title.first.is_visible():
            return False
        self._click_continue(r"continue anyway")
        return True

    def _advance_to_checkout_step(
        self,
        step: int,
        *,
        on_blocked: Callable[[], bool] | None = None,
        timeout_ms: int = 60_000,
    ) -> None:
        url_pattern = re.compile(rf"/secure/checkout/payment\?step={step}", re.I)
        polls = max(1, timeout_ms // 500)
        for _ in range(polls):
            if url_pattern.search(self.page.url):
                return
            if on_blocked and on_blocked():
                continue
            self.page.wait_for_timeout(500)
        expect(self.page).to_have_url(url_pattern, timeout=5_000)

    def continue_to_shipping_method(self) -> None:
        self._click_continue(r"Continue to Shipping Method")
        self._advance_to_checkout_step(
            2,
            on_blocked=self._dismiss_address_not_verified_modal,
        )

    def select_random_shipping_method(self) -> str | None:
        self.page.wait_for_timeout(SHIPPING_SETTLE_MS)
        radios = self.shipping_method_radios
        expect(radios.first).to_be_visible(timeout=60_000)
        count = radios.count()
        if count == 0:
            raise RuntimeError("No visible shipping methods on checkout step 2")
        choice = radios.nth(random.randrange(count))
        method_value = choice.get_attribute("value")
        choice.check()
        return method_value

    def continue_to_payment(self) -> None:
        self._click_continue(r"Continue to Payment")
        expect(self.page).to_have_url(re.compile(r"/secure/checkout/payment\?step=3", re.I), timeout=60_000)

    def place_order(self) -> None:
        self._click_continue(r"Place Your Order")
        expect(self.page).to_have_url(re.compile(r"/secure/checkout/confirm_order", re.I), timeout=PLACE_ORDER_TIMEOUT_MS)

    def read_order_number(self) -> str:
        body = self.page.locator("body")
        expect(body).to_contain_text(ORDER_NUMBER_RE, timeout=30_000)
        match = ORDER_NUMBER_RE.search(body.inner_text())
        if not match:
            raise AssertionError("Order confirmation page did not contain order number")
        return match.group(1)

    def place_order_and_get_order_number(self) -> str:
        self.place_order()
        return self.read_order_number()
