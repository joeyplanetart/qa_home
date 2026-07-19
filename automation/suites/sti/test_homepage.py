"""STI 站点冒烟测试"""
from playwright.sync_api import Page, expect


def test_sti_homepage_loads(page: Page):
    page.goto("https://www.simplytoimpress.com", timeout=60000)
    expect(page.locator("body")).to_be_visible()


def test_sti_has_header(page: Page):
    page.goto("https://www.simplytoimpress.com", timeout=60000)
    expect(page.locator("header, nav, [role='banner']").first).to_be_visible()
