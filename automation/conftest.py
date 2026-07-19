"""Playwright / pytest 公共配置"""
import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def browser_context_args():
    return {"viewport": {"width": 1280, "height": 720}}


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
