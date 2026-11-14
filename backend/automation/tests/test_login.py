"""Login automation tests for SauceDemo (fixed scenarios; the data-driven suite covers input matrices)."""
from automation.pages.inventory_page import InventoryPage
from automation.pages.login_page import LoginPage


class TestLogin:
    def test_valid_login(self, page):
        LoginPage(page).login("standard_user", "secret_sauce")
        assert InventoryPage(page).is_loaded(), "Inventory page should load after valid login"

    def test_invalid_username(self, page):
        login = LoginPage(page)
        login.login("invalid_user", "secret_sauce")
        assert login.is_login_error_visible(), "An error message should be shown for an unknown user"

    def test_invalid_password(self, page):
        login = LoginPage(page)
        login.login("standard_user", "wrong_password")
        assert login.is_login_error_visible(), "An error message should be shown for a wrong password"

    def test_empty_credentials(self, page):
        login = LoginPage(page)
        login.login("", "")
        assert login.is_login_error_visible(), "An error message should be shown for empty credentials"

    def test_locked_out_user(self, page):
        login = LoginPage(page)
        login.login("locked_out_user", "secret_sauce")
        message = login.get_error_message()
        assert "locked out" in message.lower(), f"Expected a locked-out message, got: {message!r}"
