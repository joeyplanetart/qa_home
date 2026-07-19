"""CafePress Page Object 基类"""
from __future__ import annotations

import re

from playwright.sync_api import Page

CAFEPRESS_US = "https://www.cafepress.com"
NAV_TIMEOUT = 60_000


class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self, path: str = "") -> None:
        url = f"{CAFEPRESS_US}{path}" if path else CAFEPRESS_US
        self.page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
        self.dismiss_overlays()

    def dismiss_overlays(self) -> None:
        """关闭可能出现的 cookie / 个性化弹窗。"""
        for pattern in (
            re.compile(r"^Confirm$", re.I),
            re.compile(r"^Accept", re.I),
            re.compile(r"^Continue", re.I),
        ):
            btn = self.page.get_by_role("button", name=pattern)
            try:
                if btn.count() > 0:
                    btn.first.click(timeout=2000)
            except Exception:
                pass
