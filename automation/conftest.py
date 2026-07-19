"""Playwright / pytest 公共配置"""
import os
from pathlib import Path

import pytest


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


@pytest.fixture(scope="session")
def browser_context_args():
    ctx = {
        "viewport": {
            "width": _env_int("AUTOMATION_VIEWPORT_WIDTH", 1280),
            "height": _env_int("AUTOMATION_VIEWPORT_HEIGHT", 720),
        },
    }
    locale = os.environ.get("AUTOMATION_LOCALE", "").strip()
    if locale:
        ctx["locale"] = locale
    return ctx


@pytest.fixture
def page(page):
    timeout = _env_int("AUTOMATION_TIMEOUT", 30000)
    page.set_default_timeout(timeout)
    page.set_default_navigation_timeout(timeout)
    return page


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or report.passed:
        return
    page = item.funcargs.get("page")
    screenshots_dir = os.environ.get("AUTOMATION_SCREENSHOTS_DIR")
    if page is None or not screenshots_dir:
        return
    Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
    safe_name = item.nodeid.replace("/", "_").replace("::", "_")
    path = Path(screenshots_dir) / f"{safe_name}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
    except Exception:
        pass
