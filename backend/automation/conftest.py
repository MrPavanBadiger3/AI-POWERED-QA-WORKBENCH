"""Shared fixtures + failure evidence capture (screenshots) for every automated test."""
import logging
import os
import re
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

SCREENSHOT_DIR = Path(os.getenv("QA_SCREENSHOT_DIR", BACKEND_DIR / "screenshots"))
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
log = logging.getLogger("automation")


@pytest.fixture(scope="session")
def browser_instance():
    headless = os.getenv("QA_HEADLESS", "1") != "0"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        yield browser
        browser.close()


@pytest.fixture
def page(browser_instance):
    context = browser_instance.new_context(viewport={"width": 1280, "height": 800})
    context.set_default_timeout(15000)
    pg = context.new_page()
    yield pg
    context.close()


@pytest.fixture(autouse=True)
def evidence(json_metadata):
    """Autouse so that every test has a metadata dict that ends up in the JSON report."""
    return json_metadata


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when not in ("setup", "call") or not report.failed:
        return
    page = item.funcargs.get("page")
    if page is None:
        return
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.nodeid)[-110:]
    filename = f"{os.getenv('QA_EXECUTION_ID', 'local')}_{name}_{int(time.time() * 1000)}.png"
    try:
        png = page.screenshot(path=str(SCREENSHOT_DIR / filename), full_page=True)
    except Exception as exc:  # page may be closed/crashed - never mask the real failure
        log.warning("Could not capture failure screenshot: %s", exc)
        return
    meta = item.funcargs.get("json_metadata")
    if meta is not None:
        meta["screenshot"] = filename
    try:  # embed into the pytest-html report too
        import base64
        from pytest_html import extras
        report.extras = getattr(report, "extras", []) + [extras.png(base64.b64encode(png).decode())]
    except Exception:
        pass
