# Sample requirements (human-authored inputs for SauceDemo)

These are **inputs** to paste into the Requirement Analyzer. They are not AI output.

## SR-1 Login (simple)
As a user, I should be able to log in to the application using valid credentials.

## SR-2 Login (with acceptance criteria)
**Title:** SauceDemo user authentication
**Requirement:** Users must be able to log in to SauceDemo using valid credentials and reach the inventory page. Invalid credentials and empty submissions must be rejected.
**User story:** As a SauceDemo customer, I want to log in with my username and password so that I can access the product catalogue.
**Acceptance criteria:**
1. Given standard_user / secret_sauce, the user is taken to the inventory page.
2. Given invalid credentials, an error message is displayed and the user stays on the login page.
3. Given empty username or password, an error message is displayed.

## SR-3 Cart and checkout
As a shopper, I want to add a product to my cart, review the cart and complete checkout with my first name, last name and postal code, so that I receive an order confirmation.
**Acceptance criteria:** Adding a product increases the cart count. The cart lists the product added. Checkout requires first name, last name and postal code. Completing checkout shows a confirmation message.
