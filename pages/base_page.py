"""Common base for page objects.

Conventions used across ``pages/``:

* Locators are built from **user-facing semantics** (ARIA role + accessible name, label,
  placeholder) — never from absolute XPaths, positional CSS or generated class names.
* Playwright auto-waits for actionability, so there are **no sleeps**.
* Page objects describe *what a user can do*; assertions live in the tests.
"""

from playwright.sync_api import Page

from pages.components.navbar import NavBar
from pages.components.sidebar import Sidebar


class BasePage:
    path: str = "/"

    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self):
        self.page.goto(self.path)
        return self


class AuthenticatedPage(BasePage):
    """A page rendered inside the main app shell (top navigation + sidebar)."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.navbar = NavBar(page)
        self.sidebar = Sidebar(page)
