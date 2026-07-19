"""CafePress 首页冒烟测试"""
import re

from playwright.sync_api import expect


def test_cafepress_homepage_loads(home):
    home.open()
    expect(home.page.locator("body")).to_be_visible()


def test_cafepress_page_title(home):
    home.open()
    expect(home.page).to_have_title(re.compile("CafePress", re.I))


def test_cafepress_header_visible(home):
    home.open()
    expect(home.header).to_be_visible()


def test_cafepress_search_box_visible(home):
    home.open()
    expect(home.search_input).to_be_visible()


def test_cafepress_bestsellers_visible(home):
    home.open()
    expect(home.bestseller_cards.first).to_be_visible()
