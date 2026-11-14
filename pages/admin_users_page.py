from playwright.sync_api import Locator, Page

from pages.base_page import AuthenticatedPage
from pages.components.modals import set_switch


class NewUserForm:
    def __init__(self, page: Page) -> None:
        self.root = page.get_by_role("dialog", name="New user")
        self.email = self.root.get_by_role("textbox", name="Email")
        self.name = self.root.get_by_role("textbox", name="Name", exact=True)
        self.username = self.root.get_by_role("textbox", name="Username")
        self.password = self.root.get_by_role("textbox", name="Password", exact=True)
        self.confirm_password = self.root.get_by_placeholder("Confirm password")
        self.join_default_channels = self.root.get_by_role("checkbox", name="Join default channels")
        self.submit = self.root.get_by_role("button", name="Add user")

    def fill_and_submit(self, *, name: str, username: str, email: str, password: str) -> None:
        self.email.fill(email)
        self.name.fill(name)
        self.username.fill(username)
        self.password.fill(password)
        self.confirm_password.fill(password)
        set_switch(self.join_default_channels, False)
        self.submit.click()


class AdminUsersPage(AuthenticatedPage):
    path = "/admin/users"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.main = page.get_by_role("main")
        self.new_user_button = self.main.get_by_role("button", name="New user")
        self.search_input = self.main.get_by_role("textbox", name="Search users")

    def open(self) -> "AdminUsersPage":
        super().open()
        self.new_user_button.wait_for()
        return self

    def open_new_user_form(self) -> NewUserForm:
        self.new_user_button.click()
        return NewUserForm(self.page)

    def row(self, username: str) -> Locator:
        return self.main.get_by_role("table").get_by_role("link").filter(has_text=username)
