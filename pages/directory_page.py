from typing import Literal

from playwright.sync_api import Locator, Page

from pages.base_page import AuthenticatedPage

DirectoryTab = Literal["Channels", "Users", "Teams"]


class DirectoryPage(AuthenticatedPage):
    path = "/directory"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.main = page.get_by_role("main")
        self.heading = self.main.get_by_role("heading", name="Directory", level=1)
        self.results = self.main.get_by_role("table")

    def open(self) -> "DirectoryPage":
        super().open()
        self.heading.wait_for()
        return self

    def search(self, tab: DirectoryTab, term: str) -> None:
        self.main.get_by_role("tab", name=tab).click()
        self.main.get_by_role("textbox", name=f"Search {tab.lower()}").fill(term)

    def result(self, text: str) -> Locator:
        """A result row (rendered as a link) whose content contains ``text``."""
        return self.results.get_by_role("link").filter(has_text=text)
