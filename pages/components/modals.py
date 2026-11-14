from playwright.sync_api import Locator, Page, expect


class Modal:
    def __init__(self, page: Page, title: str) -> None:
        self.page = page
        self.root = page.get_by_role("dialog", name=title)

    def button(self, name: str) -> Locator:
        return self.root.get_by_role("button", name=name, exact=True)


def set_switch(checkbox: Locator, value: bool) -> None:
    """Toggle a Fuselage switch. Its <input> is visually hidden, so click the wrapping label."""
    if checkbox.is_checked() != value:
        checkbox.locator("xpath=..").click()
    expect(checkbox).to_be_checked(checked=value)


def _pick_user(page: Page, combobox: Locator, username: str) -> None:
    # The autocomplete reacts to key events, so type rather than fill.
    combobox.press_sequentially(username)
    page.get_by_role("option", name=username).first.click()
    # The suggestions popup stays open after a pick and would cover the dialog buttons.
    combobox.press("Escape")
    page.get_by_role("listbox").wait_for(state="hidden")


class CreateRoomModal(Modal):
    """The 'Create channel' and 'Create team' dialogs share one layout."""

    def __init__(self, page: Page, title: str) -> None:
        super().__init__(page, title)
        self.name = self.root.get_by_role("textbox", name="Name")
        self.topic = self.root.get_by_role("textbox", name="Topic")
        self.members = self.root.get_by_role("combobox", name="Members")
        self.private = self.root.get_by_role("checkbox", name="Private")
        self.create_button = self.button("Create")

    def create(
        self, name: str, *, private: bool = True, topic: str | None = None, members: tuple[str, ...] = ()
    ) -> None:
        self.name.fill(name)
        if topic:
            self.topic.fill(topic)
        for username in members:
            _pick_user(self.page, self.members, username)
        set_switch(self.private, private)
        self.create_button.click()


class DirectMessageModal(Modal):
    def __init__(self, page: Page) -> None:
        super().__init__(page, "New direct message")
        self.people = self.root.get_by_role("combobox", name="Select one or more people to message")
        self.create_button = self.button("Create")

    def create(self, *usernames: str) -> None:
        for username in usernames:
            _pick_user(self.page, self.people, username)
        self.create_button.click()


class ConfirmModal(Modal):
    def __init__(self, page: Page, title: str = "Are you sure?") -> None:
        super().__init__(page, title)

    def confirm(self, button: str) -> None:
        self.button(button).click()
