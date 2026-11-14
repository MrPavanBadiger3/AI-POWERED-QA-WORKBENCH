import logging

from playwright.sync_api import Page, TimeoutError as PWTimeout

from .base_page import BasePage

log = logging.getLogger("automation")


class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.username_input = page.get_by_placeholder("Username")
        self.password_input = page.get_by_placeholder("Password")
        self.login_button = page.get_by_role("button", name="Login")
        self.error_message = page.locator('[data-test="error"]')
        self._inventory = page.locator(".inventory_list")

    def navigate_to(self):
        self.navigate("/")

    def login(self, username: str, password: str):
        log.info("Login attempt user=%r (password hidden)", username)
        self.navigate_to()
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def wait_for_outcome(self, timeout: int = 8000) -> str:
        """Returns 'success' (inventory shown), 'failure' (error banner) or 'unknown' - without fixed sleeps."""
        try:
            self._inventory.or_(self.error_message).first.wait_for(state="visible", timeout=timeout)
        except PWTimeout:
            return "unknown"
        return "success" if self._inventory.is_visible() else "failure"

    def is_login_error_visible(self, timeout: int = 5000) -> bool:
        try:
            self.error_message.wait_for(state="visible", timeout=timeout)
            return True
        except PWTimeout:
            return False

    def get_error_message(self) -> str:
        return self.error_message.inner_text() if self.is_login_error_visible(timeout=2000) else ""
