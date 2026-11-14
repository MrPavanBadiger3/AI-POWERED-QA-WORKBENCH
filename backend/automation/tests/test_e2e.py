"""Product selection, cart, checkout and order confirmation on SauceDemo."""
from automation.pages.cart_page import CartPage
from automation.pages.checkout_page import CheckoutPage
from automation.pages.confirmation_page import ConfirmationPage
from automation.pages.inventory_page import InventoryPage
from automation.pages.login_page import LoginPage


def _login(page) -> InventoryPage:
    LoginPage(page).login("standard_user", "secret_sauce")
    inventory = InventoryPage(page)
    assert inventory.is_loaded(), "Precondition failed: login did not reach the inventory page"
    return inventory


class TestE2EWorkflow:
    def test_product_selection_adds_to_cart_badge(self, page):
        inventory = _login(page)
        names = inventory.get_product_names()
        assert len(names) >= 2, "Expected at least two products on the inventory page"
        inventory.add_product_by_name(names[1])
        assert inventory.get_cart_count() == 1

    def test_cart_validation(self, page):
        inventory = _login(page)
        product = inventory.add_first_product_to_cart()
        inventory.go_to_cart()
        cart = CartPage(page)
        assert cart.is_loaded()
        assert cart.get_item_names() == [product]
        assert cart.get_item_count() == 1

    def test_complete_purchase_flow(self, page):
        inventory = _login(page)
        product = inventory.add_first_product_to_cart()
        assert inventory.get_cart_count() == 1
        inventory.go_to_cart()
        cart = CartPage(page)
        assert cart.is_loaded()
        assert product in cart.get_item_names()
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page)
        checkout.fill_information("Test", "User", "12345")
        checkout.continue_to_overview()
        assert checkout.is_overview_loaded(), "Checkout overview page did not load"
        checkout.finish_order()
        assert ConfirmationPage(page).is_order_confirmed(), "Order confirmation was not displayed"

    def test_checkout_missing_info(self, page):
        inventory = _login(page)
        inventory.add_first_product_to_cart()
        inventory.go_to_cart()
        CartPage(page).proceed_to_checkout()
        checkout = CheckoutPage(page)
        checkout.continue_to_overview()
        assert checkout.is_error_visible(), "An error should be shown when checkout information is missing"
