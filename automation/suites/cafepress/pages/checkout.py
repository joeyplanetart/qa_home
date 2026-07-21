"""CafePress 结账流程（Shipping → Payment → Confirm）"""
from __future__ import annotations

import os
import random
import re
import uuid
from typing import TypedDict

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
STREET_NAMES = ("Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine Rd", "Elm St")


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
    def first_name_input(self) -> Locator:
        return self.page.locator("input[name='txtFirstName']")

    @property
    def last_name_input(self) -> Locator:
        return self.page.locator("input[name='txtLastName']")

    @property
    def address1_input(self) -> Locator:
        return self.page.locator("input[name='txtAddress1']")

    @property
    def city_input(self) -> Locator:
        return self.page.locator("input[name='txtCity']")

    @property
    def state_select(self) -> Locator:
        return self.page.locator("select[name='txtState']")

    @property
    def zip_input(self) -> Locator:
        return self.page.locator("input[name='txtZip']")

    @property
    def phone_input(self) -> Locator:
        return self.page.locator("input[name='txtPhone']")

    @property
    def shipping_method_radios(self) -> Locator:
        return self.page.locator("input[type='radio']:visible")

    def open_step1(self) -> None:
        self.open(CHECKOUT_PAYMENT_STEP1)
        expect(self.page).to_have_url(re.compile(r"/secure/checkout/payment\?step=1", re.I))

    def fill_shipping_address(self, address: ShippingAddress | None = None) -> ShippingAddress:
        data = address or make_us_shipping_address()
        expect(self.first_name_input).to_be_visible(timeout=30_000)
        self.first_name_input.fill(data["first_name"])
        self.last_name_input.fill(data["last_name"])
        self.address1_input.fill(data["address1"])
        self.city_input.fill(data["city"])
        self.state_select.select_option(value=data["state"])
        self.zip_input.fill(data["zip"])
        self.phone_input.fill(data["phone"])
        return data

    def fill_random_us_address(self) -> ShippingAddress:
        return self.fill_shipping_address(make_us_shipping_address())

    def _click_continue(self, label_pattern: str) -> None:
        button = self.page.locator("input[type='submit'], button, a, .g-btn").filter(
            has_text=re.compile(label_pattern, re.I)
        )
        expect(button.first).to_be_visible(timeout=30_000)
        button.first.click()

    def continue_to_shipping_method(self) -> None:
        self._click_continue(r"Continue to Shipping Method")
        expect(self.page).to_have_url(re.compile(r"/secure/checkout/payment\?step=2", re.I), timeout=60_000)

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
