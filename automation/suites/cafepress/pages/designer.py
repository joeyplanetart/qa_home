"""CafePress CYO Designer / PDP 页"""
from __future__ import annotations

import os
import random
import re
from pathlib import Path

from playwright.sync_api import Locator, Page, expect

from .base import BasePage

CYO_MENS_VALUE_TEE = (
    "/designer/custom-mens-value-t-shirts"
    "?attr2=8915&default_pos=front&attr11=3870&attr4=6661"
)
ASSERT_DIR = Path(__file__).resolve().parents[3] / "assert"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SIZE_PATTERN = re.compile(r"^(S|M|L|XL|XLT|2XL|2XLT|3XL|3XLT|4XL|5XL)$", re.I)
DESIGN_SETTLE_MS = int(os.environ.get("AUTOMATION_DESIGN_SETTLE_MS", "3000"))
UPLOAD_THUMB_READY_JS = """
(thumbIndex) => {
  const thumbs = document.querySelectorAll('.ucd-uploader-dialog a.photo-tray-thumb-container');
  const thumb = thumbs[thumbIndex];
  if (!thumb) return false;
  const img = thumb.querySelector('img[src*="cloudfront.net"]');
  return Boolean(img && img.complete && img.naturalWidth > 0);
}
"""


def random_assert_image() -> Path:
    images = [
        p for p in ASSERT_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    ]
    if not images:
        raise FileNotFoundError(f"No test images found in {ASSERT_DIR}")
    return random.choice(images)


class DesignerPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.last_color: str | None = None
        self.last_size: str | None = None
        self.last_image: str | None = None

    def open_cyo_pdp(self, path: str = CYO_MENS_VALUE_TEE) -> None:
        self.open(path)

    @property
    def text_options(self) -> Locator:
        return self.page.locator(".container-option-item.Text-option-item")

    @property
    def color_options(self) -> Locator:
        return self.page.locator(".container-option-item[class*='color' i]")

    @property
    def quantity_input(self) -> Locator:
        return self.page.locator("input[name*='quantity'], input[type='number']").first

    @property
    def personalize_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"^Personalize$", re.I))

    @property
    def add_logo_button(self) -> Locator:
        return self.page.locator(".ADD_LOGO")

    @property
    def side_tabs(self) -> Locator:
        return self.page.locator(".SIDE_TAB a")

    @property
    def add_to_cart_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"ADD TO CART", re.I))

    def select_text_option(self, label: str) -> None:
        option = self.text_options.filter(
            has=self.page.locator(".option-text", has_text=re.compile(f"^{re.escape(label)}$", re.I))
        ).first
        expect(option).to_be_visible()
        option.click()

    def select_position(self, position: str = "Front + Back") -> None:
        self.select_text_option(position)

    def select_random_color(self) -> str:
        options = self.color_options
        expect(options.first).to_be_visible()
        count = options.count()
        choice = options.nth(random.randrange(count))
        choice.click()
        color = (choice.get_attribute("title") or choice.get_attribute("aria-label") or "").strip()
        if not color:
            color = choice.inner_text().strip() or f"color-{random.randrange(count)}"
        self.last_color = color
        return color

    def select_random_size(self) -> str:
        sizes: list[str] = []
        for i in range(self.text_options.count()):
            text = self.text_options.nth(i).locator(".option-text").inner_text().strip()
            if SIZE_PATTERN.match(text):
                sizes.append(text)
        if not sizes:
            raise RuntimeError("No size options found on CYO PDP")
        label = random.choice(sizes)
        self.select_text_option(label)
        self.last_size = label
        return label

    def set_quantity(self, quantity: int = 2) -> None:
        expect(self.quantity_input).to_be_visible()
        self.quantity_input.fill(str(quantity))

    def set_random_quantity(self, minimum: int = 2, maximum: int = 5) -> int:
        quantity = random.randint(minimum, maximum)
        self.set_quantity(quantity)
        return quantity

    def enter_designer(self) -> None:
        expect(self.personalize_button).to_be_enabled()
        self.personalize_button.click()
        expect(self.page.locator(".SIDE_TAB").first).to_be_visible(timeout=90_000)
        expect(self.add_logo_button).to_be_visible(timeout=90_000)

    def dismiss_blocking_overlays(self) -> None:
        overlay = self.page.locator(".ui-widget-overlay.ui-front")
        if overlay.count():
            try:
                overlay.first.wait_for(state="hidden", timeout=10_000)
            except Exception:
                pass
        self.dismiss_overlays()

    def wait_for_design_render(self) -> None:
        """Designer 图片渲染较慢，关键步骤后等待 canvas 稳定。"""
        self.dismiss_blocking_overlays()
        self.page.wait_for_timeout(DESIGN_SETTLE_MS)

    def upload_image(self, image_path: Path | None = None) -> Path:
        image = image_path or random_assert_image()
        uploader = self.page.locator(".ucd-uploader-dialog")
        self.dismiss_blocking_overlays()
        for attempt in range(3):
            self.add_logo_button.click()
            try:
                expect(uploader).to_be_visible(timeout=20_000)
                break
            except AssertionError:
                if attempt == 2:
                    raise
                self.dismiss_blocking_overlays()
        return self._complete_image_upload(image, uploader)

    def _complete_image_upload(self, image: Path, uploader: Locator) -> Path:
        thumbs = uploader.locator("a.photo-tray-thumb-container")
        before_count = thumbs.count()
        uploader.locator("input[type='file']").first.set_input_files(str(image.resolve()))
        expect(thumbs).to_have_count(before_count + 1, timeout=90_000)
        new_thumb = thumbs.nth(before_count)
        expect(new_thumb).to_be_visible()
        self.page.wait_for_function(UPLOAD_THUMB_READY_JS, before_count, timeout=90_000)
        new_thumb.click()
        uploader.locator(".btn.add").click()
        expect(uploader).to_be_hidden(timeout=30_000)
        self.wait_for_design_render()
        self.last_image = image.name
        return image

    def switch_to_back(self) -> None:
        self.wait_for_design_render()
        back_tab = self.side_tabs.filter(has_text=re.compile(r"^back$", re.I)).first
        expect(back_tab).to_be_visible()
        back_tab.click()
        self.apply_front_image_to_back()

    def apply_front_image_to_back(self) -> None:
        confirm = self.page.locator(".ui-dialog").filter(
            has=self.page.locator(".ui-dialog-title", has_text=re.compile(r"^CONFIRM$", re.I))
        )
        expect(confirm).to_be_visible(timeout=15_000)
        expect(confirm).to_contain_text(re.compile(r"back of the design", re.I))
        yes_btn = confirm.get_by_role("button", name=re.compile(r"^YES$", re.I)).first
        expect(yes_btn).to_be_visible()
        yes_btn.click()
        expect(confirm).to_be_hidden(timeout=15_000)
        self.wait_for_design_render()

    def add_to_cart(self) -> None:
        self.wait_for_design_render()
        expect(self.add_to_cart_button).to_be_enabled()
        self.add_to_cart_button.click()
        missing = self.page.get_by_label("Missing Image")
        if missing.count() and missing.is_visible():
            raise AssertionError("Back image not applied before add to cart")
        expect(
            self.page.get_by_text(re.compile(r"just added to your cart", re.I))
        ).to_be_visible(timeout=30_000)

    def save_screenshot(
        self,
        name: str,
        *,
        label: str | None = None,
        test_data: object | None = None,
    ) -> Path | None:
        screenshots_dir = os.environ.get("AUTOMATION_SCREENSHOTS_DIR", "").strip()
        if not screenshots_dir:
            return None
        self.wait_for_design_render()
        test_id = os.environ.get("AUTOMATION_TEST_ID", "").strip()
        filename = f"{test_id}__{name}.png" if test_id else f"{name}.png"
        out_dir = Path(screenshots_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        self.page.screenshot(path=str(path), full_page=True)
        if test_data is not None and hasattr(test_data, "record_screenshot"):
            test_data.record_screenshot(filename, label or name.replace("_", " "))
        return path
