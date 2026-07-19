"""CafePress 站点冒烟测试（示例 / demo 套件）"""
import re

from playwright.sync_api import Page, expect

CAFEPRESS_US = "https://www.cafepress.com"


def test_cafepress_homepage_loads(page: Page):
    page.goto(CAFEPRESS_US, timeout=60000)
    expect(page.locator("body")).to_be_visible()


def test_cafepress_page_title(page: Page):
    page.goto(CAFEPRESS_US, timeout=60000)
    expect(page).to_have_title(re.compile("CafePress", re.I))


def test_cafepress_header_visible(page: Page):
    page.goto(CAFEPRESS_US, timeout=60000)
    expect(page.locator("header, nav, [role='banner']").first).to_be_visible()
