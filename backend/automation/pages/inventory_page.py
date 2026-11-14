import logging

from playwright.sync_api import Page, TimeoutError as PWTimeout

from .base_page import BasePage

log = logging.getLogger("automation")


class InventoryPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.inventory_list = page.locator(".inventory_list")
        self.items = page.locator(".inventory_item")
        self.cart_badge = page.locator(".shopping_cart_badge")
        self.cart_link = page.locator(".shopping_cart_link")

    def is_loaded(self, timeout: int = 10000) -> bool:
        try:
            self.inventory_list.wait_for(state="visible", timeout=timeout)
            return True
        except PWTimeout:
            return False

    def get_product_names(self) -> list[str]:
        self.inventory_list.wait_for(state="visible")
        return self.page.locator(".inventory_item_name").all_inner_texts()

    def add_product_by_name(self, name: str) -> str:
        log.info("Add product to cart: %s", name)
        item = self.items.filter(has_text=name)
        item.get_by_role("button", name="Add to cart").click()
        return name

    def add_first_product_to_cart(self) -> str:
        name = self.get_product_names()[0]
        return self.add_product_by_name(name)

    def get_cart_count(self) -> int:
        try:
            self.cart_badge.wait_for(state="visible", timeout=5000)
            return int(self.cart_badge.inner_text())
        except PWTimeout:
            return 0

    def go_to_cart(self):
        self.cart_link.click()
