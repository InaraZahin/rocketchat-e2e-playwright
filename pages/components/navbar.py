from typing import Literal

from playwright.sync_api import Page

from pages.components.modals import CreateRoomModal, DirectMessageModal

ViewMode = Literal["Extended", "Medium", "Condensed"]


class NavBar:
    """The top navigation bar: create menu, directory, display options, user menu."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.get_by_role("navigation", name="header")
        self.home_button = self.root.get_by_role("button", name="Home")
        self.directory_button = self.root.get_by_role("button", name="Directory")
        self.display_button = self.root.get_by_role("button", name="Display")
        self.create_new_button = self.root.get_by_role("button", name="Create new")
        self.user_menu_button = self.root.get_by_role("button", name="User menu")

    def _create(self, item: str) -> None:
        self.create_new_button.click()
        self.page.get_by_role("menu", name="Create new").get_by_role("menuitem", name=item).click()

    def open_create_channel(self) -> CreateRoomModal:
        self._create("Channel")
        return CreateRoomModal(self.page, "Create channel")

    def open_create_team(self) -> CreateRoomModal:
        self._create("Team")
        return CreateRoomModal(self.page, "Create team")

    def open_create_direct_message(self) -> DirectMessageModal:
        self._create("Direct message")
        return DirectMessageModal(self.page)

    def set_view_mode(self, mode: ViewMode) -> None:
        self.display_button.click()
        self.page.get_by_role("menu", name="Display").get_by_role("menuitemcheckbox", name=mode).click()
        self.page.keyboard.press("Escape")

    def logout(self) -> None:
        self.user_menu_button.click()
        self.page.get_by_role("menu", name="User menu").get_by_role("menuitemcheckbox", name="Logout").click()
