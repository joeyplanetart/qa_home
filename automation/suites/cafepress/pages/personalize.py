"""CafePress Personalize 产品（固定 slot，如 Edit Text）"""
from __future__ import annotations

import re
import uuid

from playwright.sync_api import expect

from .designer import DesignerPage

PERSONALIZE_MENS_CLASSIC_TEE = (
    "/+create_your_own_mens_classic_t_shirts,550975980"
    "?attr2=8915&default_pos=front&attr4=6661"
)


def make_personalize_text(prefix: str = "QA Auto") -> str:
    return f"{prefix} {uuid.uuid4().hex[:6]}"


class PersonalizePage(DesignerPage):
    def open_personalize_pdp(self, path: str = PERSONALIZE_MENS_CLASSIC_TEE) -> None:
        self.open(path)

    @property
    def text_dialog(self):
        return self.page.locator(".UCD_TEXT_DIALOG")

    def enter_designer(self) -> None:
        expect(self.personalize_button).to_be_enabled()
        self.personalize_button.click()
        expect(self.text_dialog.first).to_be_visible(timeout=90_000)

    def edit_text_slot(self, text: str | None = None) -> str:
        label = text or make_personalize_text()
        expect(self.text_dialog).to_be_visible()
        textarea = self.text_dialog.locator("textarea").first
        expect(textarea).to_be_visible()
        textarea.fill(label)
        self.wait_for_design_render()
        self.last_text = label
        return label

    def add_to_cart(self) -> None:
        self.wait_for_design_render()
        expect(self.add_to_cart_button).to_be_enabled()
        self.add_to_cart_button.click()
        unedited = self.page.locator(".ui-dialog:visible").filter(
            has_text=re.compile(r"did not edit|yourwordhere", re.I)
        )
        if unedited.count():
            raise AssertionError("Text slot was not edited before add to cart")
        expect(
            self.page.get_by_text(re.compile(r"just added to your cart", re.I))
        ).to_be_visible(timeout=30_000)
