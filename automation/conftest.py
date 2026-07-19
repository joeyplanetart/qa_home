"""Playwright / pytest 公共配置"""
import json
import os
from pathlib import Path

import pytest

from test_data import TestData


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _artifact_filename(nodeid: str) -> str:
    return nodeid.replace("/", "_").replace("::", "_")


def _save_test_artifacts(nodeid: str, data: dict) -> None:
    if not data:
        return
    artifacts_dir = os.environ.get("AUTOMATION_ARTIFACTS_DIR")
    if not artifacts_dir:
        return
    out_dir = Path(artifacts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{_artifact_filename(nodeid)}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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


@pytest.fixture
def test_data(request):
    data = TestData()
    yield data
    _save_test_artifacts(request.node.nodeid, data.to_dict())


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
