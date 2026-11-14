from playwright.sync_api import Page, TimeoutError as PWTimeout

from .base_page import BasePage


class CartPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.cart_items = page.locator(".cart_item")
        self.checkout_button = page.get_by_role("button", name="Checkout")

    def is_loaded(self, timeout: int = 10000) -> bool:
        try:
            self.page.wait_for_url("**/cart.html", timeout=timeout)
            return True
        except PWTimeout:
            return False

    def get_item_names(self) -> list[str]:
        try:
            self.cart_items.first.wait_for(state="visible", timeout=5000)
        except PWTimeout:
            return []
        return self.page.locator(".inventory_item_name").all_inner_texts()

    def get_item_count(self) -> int:
        return self.cart_items.count()

    def proceed_to_checkout(self):
        self.checkout_button.click()
