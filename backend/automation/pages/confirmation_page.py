from playwright.sync_api import Page, TimeoutError as PWTimeout

from .base_page import BasePage


class ConfirmationPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.confirmation_header = page.locator(".complete-header")

    def is_order_confirmed(self, timeout: int = 10000) -> bool:
        try:
            self.confirmation_header.wait_for(state="visible", timeout=timeout)
            return True
        except PWTimeout:
            return False

    def get_confirmation_message(self) -> str:
        return self.confirmation_header.inner_text() if self.is_order_confirmed(5000) else ""
