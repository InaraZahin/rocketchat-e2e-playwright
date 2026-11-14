from playwright.sync_api import Locator, Page

from framework.data import Room
from pages.base_page import AuthenticatedPage
from pages.components.modals import ConfirmModal


class Composer:
    def __init__(self, scope: Locator, room_name: str) -> None:
        self.input = scope.get_by_role("textbox", name=f"Message #{room_name}")
        self.send_button = scope.get_by_role("button", name="Send", exact=True)

    def send(self, text: str) -> None:
        self.input.fill(text)
        self.input.press("Enter")


class Message:
    """A single message in a message list, located by its text."""

    def __init__(self, page: Page, root: Locator) -> None:
        self.page = page
        self.root = root
        self.body = root.get_by_role("document")
        self.actions = root.get_by_role("toolbar", name="Message actions")

    def _action(self, name: str) -> None:
        self.root.hover()  # message actions render on hover
        self.actions.get_by_role("button", name=name, exact=True).click()

    def _more(self, item: str) -> None:
        self._action("More")
        self.page.get_by_role("menu", name="More").get_by_role("menuitem", name=item).click()

    def reaction(self, emoji: str) -> Locator:
        return self.root.get_by_role("button", name=f"Reacted with :{emoji}:")

    def react(self, emoji: str) -> None:
        self._action("Add reaction")
        picker = self.page.get_by_role("dialog", name="Emoji picker")
        picker.get_by_role("textbox", name="Search").fill(emoji)
        picker.get_by_role("button", name=emoji, exact=True).click()

    def quote(self) -> None:
        self._action("Quote")

    def open_thread(self) -> None:
        self._action("Reply in thread")

    def star(self) -> None:
        self._more("Star")

    def start_edit(self) -> None:
        self._more("Edit")

    def delete(self) -> None:
        self._more("Delete")
        ConfirmModal(self.page).confirm("Yes, delete")


class ThreadPanel:
    def __init__(self, page: Page, room_name: str) -> None:
        self.root = page.get_by_role("dialog").filter(
            has=page.get_by_role("list", name="Thread message list")
        )
        self.messages = self.root.get_by_role("list", name="Thread message list")
        self.composer = Composer(self.root, room_name)
        self.close_button = self.root.get_by_role("button", name="Close")


class RoomPage(AuthenticatedPage):
    def __init__(self, page: Page, room: Room) -> None:
        super().__init__(page)
        self.room = room
        self.path = room.path
        main = page.get_by_role("main")
        self.title = main.get_by_role("heading", name=room.name, level=1)
        self.favorite_toggle = main.get_by_role("button", name=f"Favorite {room.name}")
        self.unfavorite_toggle = main.get_by_role("button", name=f"Unfavorite {room.name}")
        self.message_list = main.get_by_role("list", name="Message list")
        self.composer = Composer(main, room.name)
        self.thread = ThreadPanel(page, room.name)
        self.join_button = main.get_by_role("button", name="Join", exact=True)

    def open(self) -> "RoomPage":
        super().open()
        self.title.wait_for()
        return self

    def message(self, text: str) -> Message:
        return Message(self.page, self.message_list.get_by_role("listitem").filter(has_text=text).last)

    def send(self, text: str) -> Message:
        self.composer.send(text)
        return self.message(text)

    def edit_message(self, original: str, new_text: str) -> Message:
        self.message(original).start_edit()
        self.composer.input.fill(new_text)
        self.composer.input.press("Enter")
        return self.message(new_text)
