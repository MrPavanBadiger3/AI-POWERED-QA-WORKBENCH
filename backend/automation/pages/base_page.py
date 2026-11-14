import logging
import os
from pathlib import Path

from playwright.sync_api import Page

log = logging.getLogger("automation")


class BasePage:
    BASE_URL = os.getenv("QA_BASE_URL", "https://www.saucedemo.com").rstrip("/")

    def __init__(self, page: Page):
        self.page = page
        self.screenshots_dir = Path(os.getenv("QA_SCREENSHOT_DIR", Path(__file__).resolve().parents[2] / "screenshots"))

    def navigate(self, path: str = "/"):
        log.info("Navigate to %s%s", self.BASE_URL, path)
        self.page.goto(f"{self.BASE_URL}{path}")

    def screenshot(self, name: str) -> str:
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        path = self.screenshots_dir / f"{name}.png"
        self.page.screenshot(path=str(path))
        return str(path)
