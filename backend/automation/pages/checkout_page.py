from playwright.sync_api import Page, TimeoutError as PWTimeout

from .base_page import BasePage


class CheckoutPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.first_name = page.get_by_placeholder("First Name")
        self.last_name = page.get_by_placeholder("Last Name")
        self.postal_code = page.get_by_placeholder("Zip/Postal Code")
        self.continue_button = page.get_by_role("button", name="Continue")
        self.finish_button = page.get_by_role("button", name="Finish")
        self.error_message = page.locator('[data-test="error"]')

    def fill_information(self, first_name: str, last_name: str, postal_code: str):
        self.first_name.fill(first_name)
        self.last_name.fill(last_name)
        self.postal_code.fill(postal_code)

    def continue_to_overview(self):
        self.continue_button.click()

    def is_overview_loaded(self, timeout: int = 10000) -> bool:
        try:
            self.finish_button.wait_for(state="visible", timeout=timeout)
            return True
        except PWTimeout:
            return False

    def finish_order(self):
        self.finish_button.click()

    def is_error_visible(self, timeout: int = 5000) -> bool:
        try:
            self.error_message.wait_for(state="visible", timeout=timeout)
            return True
        except PWTimeout:
            return False
