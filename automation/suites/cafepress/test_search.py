"""CafePress 搜索功能测试"""
import re

from playwright.sync_api import expect


def test_search_returns_results(search):
    search.open_query("mug")
    expect(search.page).to_have_url(re.compile(r"/search\?q=mug", re.I))
    expect(search.product_cards.first).to_be_visible()


def test_search_from_homepage(home, search):
    home.open()
    home.search("tea")
    expect(home.page).to_have_url(re.compile(r"/search", re.I))
    expect(search.product_cards.first).to_be_visible()
