"""CafePress Personalize 产品（固定 slot：文本 / 图片）"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from playwright.sync_api import expect

from .designer import DesignerPage, random_assert_image

PERSONALIZE_MENS_CLASSIC_TEE = (
    "/+create_your_own_mens_classic_t_shirts,550975980"
    "?attr2=8915&default_pos=front&attr4=6661"
)
PERSONALIZE_IMAGE_LONG_SLEEVE = (
    "/+add_your_own_image_long_sleeve_t_shirt,580421677"
    "?attr2=8915&default_pos=front&attr4=6664"
)


def make_personalize_text(prefix: str = "QA Auto") -> str:
    return f"{prefix} {uuid.uuid4().hex[:6]}"


class PersonalizePage(DesignerPage):
    def open_personalize_pdp(self, path: str = PERSONALIZE_MENS_CLASSIC_TEE) -> None:
        self.open(path)

    def open_image_slot_pdp(self, path: str = PERSONALIZE_IMAGE_LONG_SLEEVE) -> None:
        self.open(path)

    @property
    def text_dialog(self):
        return self.page.locator(".UCD_TEXT_DIALOG")

    @property
    def editor_gallery(self):
        return self.page.locator(".ucd-main-wrapper").first

    def enter_text_designer(self) -> None:
        expect(self.personalize_button).to_be_enabled()
        self.personalize_button.click()
        expect(self.text_dialog.first).to_be_visible(timeout=90_000)

    def enter_designer(self) -> None:
        self.enter_text_designer()

    def enter_image_designer(self) -> None:
        expect(self.personalize_button).to_be_enabled()
        self.personalize_button.click()
        expect(self.page.locator(".main-gallery-label")).to_contain_text(
            re.compile(r"Personalization Editor", re.I),
            timeout=90_000,
        )

    def open_image_uploader(self) -> None:
        self.dismiss_blocking_overlays()
        expect(self.editor_gallery).to_be_visible()
        self.editor_gallery.click()
        expect(self.page.locator(".ucd-uploader-dialog")).to_be_visible(timeout=20_000)

    def upload_slot_image(self, image_path: Path | None = None) -> Path:
        image = image_path or random_assert_image()
        self.open_image_uploader()
        return self._complete_image_upload(image, self.page.locator(".ucd-uploader-dialog"))

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
        if self.text_dialog.is_visible():
            unedited = self.page.locator(".ui-dialog:visible").filter(
                has_text=re.compile(r"did not edit|yourwordhere", re.I)
            )
            if unedited.count():
                raise AssertionError("Text slot was not edited before add to cart")
        missing_photo = self.page.locator(".ui-dialog:visible").filter(
            has_text=re.compile(r"missing a photo|missing photo", re.I)
        )
        if missing_photo.count():
            raise AssertionError("Image slot was not uploaded before add to cart")
        missing_image = self.page.get_by_label("Missing Image")
        if missing_image.count() and missing_image.is_visible():
            raise AssertionError("Design image missing before add to cart")
        expect(
            self.page.get_by_text(re.compile(r"just added to your cart", re.I))
        ).to_be_visible(timeout=30_000)
