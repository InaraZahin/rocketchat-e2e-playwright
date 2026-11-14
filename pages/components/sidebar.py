import re
from typing import Literal

from playwright.sync_api import Locator, Page

RoomMenuAction = Literal["Hide", "Mark unread", "Mark read", "Favorite", "Unfavorite", "Leave"]


class Sidebar:
    """The left-hand room list plus the room search box in the top bar."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.get_by_role("navigation", name="Sidebar")
        self.search_box = page.get_by_role("search", name="Search rooms").get_by_role("combobox")

    @staticmethod
    def _link_selector(name: str) -> str:
        # Match on the room URL: the link's accessible name changes with state
        # (e.g. "1 unread message from <room>"), but its href does not.
        return f'a[href="/channel/{name}"], a[href="/group/{name}"]'

    def room_link(self, name: str) -> Locator:
        return self.root.locator(self._link_selector(name))

    def unread_badge(self, name: str) -> Locator:
        return self.root.get_by_role("status", name=re.compile(rf"unread .* from {re.escape(name)}$"))

    def _room_row(self, name: str) -> Locator:
        # `has=` is resolved relative to each list item, so it must not be anchored at the root.
        link = self.page.locator(self._link_selector(name))
        return self.root.get_by_role("listitem").filter(has=link)

    def open_room(self, name: str) -> None:
        self.room_link(name).click()

    def room_menu(self, name: str, action: RoomMenuAction) -> None:
        row = self._room_row(name)
        row.hover()  # the Options button only renders on hover
        row.get_by_role("button", name="Options").click()
        self.page.get_by_role("menu", name="Options").get_by_role("menuitem", name=action).click()

    def search(self, term: str) -> Locator:
        """Type into the room search and return the results listbox."""
        self.search_box.click()
        self.search_box.fill(term)
        return self.page.get_by_role("listbox")

    def search_result(self, name: str) -> Locator:
        return self.page.get_by_role("listbox").get_by_role("option", name=name, exact=True)
