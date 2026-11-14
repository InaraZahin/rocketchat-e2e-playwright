from playwright.sync_api import Page

from pages.base_page import AuthenticatedPage


class HomePage(AuthenticatedPage):
    path = "/home"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.heading = page.get_by_role("main").get_by_role("heading", name="Home", level=1)

    def open(self) -> "HomePage":
        super().open()
        self.heading.wait_for()
        return self
