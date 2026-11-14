from playwright.sync_api import Page

from pages.base_page import BasePage


class LoginPage(BasePage):
    path = "/home"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.form = page.get_by_role("form", name="Login")
        self.username = self.form.get_by_role("textbox", name="Email or username")
        self.password = self.form.get_by_role("textbox", name="Password")
        self.submit = self.form.get_by_role("button", name="Login")
        self.error = self.form.get_by_role("alert")
        self.forgot_password_link = self.form.get_by_role("link", name="Forgot your password?")
        self.register_link = self.form.get_by_role("link", name="Create an account")

    def login(self, username: str, password: str) -> None:
        self.username.fill(username)
        self.password.fill(password)
        self.submit.click()
