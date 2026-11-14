from playwright.sync_api import Locator, Page

from framework.data import Room, Team
from pages.components.modals import CreateRoomModal, Modal
from pages.room_page import RoomPage


class TeamChannelsPanel:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.get_by_role("dialog", name="Team channels")
        self.add_existing_button = self.root.get_by_role("button", name="Add existing")
        self.create_new_button = self.root.get_by_role("button", name="Create new")

    def channel(self, name: str) -> Locator:
        return self.root.get_by_text(name, exact=True)

    def add_existing(self, channel_name: str) -> None:
        self.add_existing_button.click()
        modal = Modal(self.page, "Add existing channels")
        # Rocket.Chat renders this autocomplete without an accessible name; it is the
        # only textbox in the dialog, so scoping to the dialog keeps the locator unambiguous.
        search = modal.root.get_by_role("textbox")
        search.press_sequentially(channel_name)
        self.page.get_by_role("option", name=channel_name, exact=True).click()
        # Unlike the create-room member picker, this list closes itself after a pick
        # (and Escape here would dismiss the whole dialog).
        self.page.get_by_role("listbox").wait_for(state="hidden")
        modal.button("Add").click()

    def create_new(self) -> CreateRoomModal:
        self.create_new_button.click()
        return CreateRoomModal(self.page, "Create channel")


class TeamPage(RoomPage):
    def __init__(self, page: Page, team: Team) -> None:
        super().__init__(page, Room(team.room_id, team.name, "c"))
        self.team = team
        toolbar = page.get_by_role("toolbar", name="Primary room actions")
        self.channels_button = toolbar.get_by_role("button", name="Team channels")
        self.info_button = toolbar.get_by_role("button", name="Team info")

    def open_channels(self) -> TeamChannelsPanel:
        self.channels_button.click()
        return TeamChannelsPanel(self.page)
