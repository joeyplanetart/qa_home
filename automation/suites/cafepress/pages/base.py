"""CafePress Page Object 基类"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from playwright.sync_api import Error, Page

CAFEPRESS_US = "https://www.cafepress.com"
NAV_TIMEOUT = 60_000
_NAV_RETRIES = 3


class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def _path_matches(self, url: str, path: str) -> bool:
        if not path:
            parsed = urlparse(url)
            return parsed.path in ("", "/")
        return path.split("?", 1)[0] in url

    def open(self, path: str = "") -> None:
        url = f"{CAFEPRESS_US}{path}" if path else CAFEPRESS_US
        last_error: Error | None = None
        for attempt in range(_NAV_RETRIES):
            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
                last_error = None
                break
            except Error as exc:
                last_error = exc
                if "ERR_ABORTED" not in str(exc) and "NS_BINDING_ABORTED" not in str(exc):
                    raise
                if self._path_matches(self.page.url, path):
                    last_error = None
                    break
                if attempt < _NAV_RETRIES - 1:
                    self.page.wait_for_timeout(1000)
                    continue
                raise
        if last_error:
            raise last_error
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Error:
            pass
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
