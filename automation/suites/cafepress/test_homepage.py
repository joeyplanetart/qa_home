"""CafePress 站点冒烟测试（示例 / demo 套件）"""
import re

from playwright.sync_api import Page, expect

CAFEPRESS_US = "https://www.cafepress.com"


def _open_homepage(page: Page) -> None:
    # 等待 domcontentloaded 而非 load：有头模式下第三方广告/脚本可能永不触发 load
    page.goto(CAFEPRESS_US, wait_until="domcontentloaded", timeout=60000)


def test_cafepress_homepage_loads(page: Page):
    _open_homepage(page)
    expect(page.locator("body")).to_be_visible()


def test_cafepress_page_title(page: Page):
    _open_homepage(page)
    expect(page).to_have_title(re.compile("CafePress", re.I))


def test_cafepress_header_visible(page: Page):
    _open_homepage(page)
    expect(page.locator("header, nav, [role='banner']").first).to_be_visible()
