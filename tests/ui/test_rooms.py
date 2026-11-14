"""Creating rooms and managing them from the sidebar."""

import pytest
from playwright.sync_api import Page, expect

from framework.api import RocketChatApi
from framework.data import Room, User, unique
from framework.wait import eventually
from pages import HomePage, RoomPage
from pages.components.modals import ConfirmModal


@pytest.fixture
def home(user_page: Page) -> HomePage:
    return HomePage(user_page).open()


@pytest.fixture
def delete_room_named(admin_api: RocketChatApi, cleanup):
    """Register cleanup for a room the test is about to create through the UI."""

    def register(name: str) -> None:
        def delete() -> None:
            info = admin_api.room_info(room_name=name)
            if info:
                admin_api.delete_room(Room(info["_id"], name, info["t"]))

        cleanup(delete)

    return register


@pytest.mark.smoke
@pytest.mark.parametrize(("private", "room_type"), [(False, "c"), (True, "p")], ids=["public", "private"])
def test_create_channel(
    home: HomePage, user_api: RocketChatApi, delete_room_named, private: bool, room_type: str
) -> None:
    name = unique("ui-channel")
    delete_room_named(name)

    home.navbar.open_create_channel().create(name, private=private, topic="Created by the e2e suite")

    expect(home.page.get_by_role("main").get_by_role("heading", name=name, level=1)).to_be_visible()
    expect(home.sidebar.room_link(name)).to_be_visible()

    def created() -> None:
        info = user_api.room_info(room_name=name)
        assert info is not None, "room was not created on the server"
        assert info["t"] == room_type
        assert info.get("topic") == "Created by the e2e suite"

    eventually(created)


@pytest.mark.regression
def test_create_channel_with_member(
    home: HomePage, admin_api: RocketChatApi, delete_room_named, cleanup
) -> None:
    member = admin_api.create_user()
    cleanup(lambda: admin_api.delete_user(member.id))
    name = unique("ui-members")
    delete_room_named(name)

    home.navbar.open_create_channel().create(name, private=False, members=(member.username,))

    expect(home.sidebar.room_link(name)).to_be_visible()

    def has_member() -> None:
        members = admin_api.get("channels.members", roomName=name)["members"]
        assert member.username in {m["username"] for m in members}

    eventually(has_member)


@pytest.mark.regression
def test_start_direct_message(home: HomePage, admin_api: RocketChatApi, user_api: RocketChatApi, cleanup):
    other: User = admin_api.create_user()
    cleanup(lambda: admin_api.delete_user(other.id))

    home.navbar.open_create_direct_message().create(other.username)

    expect(home.page.get_by_role("main").get_by_role("heading", name=other.username)).to_be_visible()
    text = unique("dm")
    home.page.get_by_role("main").get_by_role("textbox", name=f"Message @{other.username}").fill(text)
    home.page.keyboard.press("Enter")
    expect(home.page.get_by_role("main").get_by_role("list", name="Message list")).to_contain_text(text)

    def dm_exists() -> None:
        dms = user_api.get("im.list")["ims"]
        assert any(other.username in dm.get("usernames", []) for dm in dms)

    eventually(dm_exists)


@pytest.mark.regression
def test_favorite_and_unfavorite_channel(home: HomePage, user_api: RocketChatApi, channel: Room) -> None:
    home.sidebar.room_menu(channel.name, "Favorite")
    eventually(lambda: _assert_favorite(user_api, channel, True))

    room = RoomPage(home.page, channel).open()
    expect(room.unfavorite_toggle).to_be_visible()

    room.unfavorite_toggle.click()

    expect(room.favorite_toggle).to_be_visible()
    eventually(lambda: _assert_favorite(user_api, channel, False))


def _assert_favorite(api: RocketChatApi, room: Room, expected: bool) -> None:
    assert bool(api.subscription(room.id).get("f")) is expected


@pytest.mark.regression
def test_hide_channel_removes_it_from_sidebar(home: HomePage, user_api: RocketChatApi, channel: Room) -> None:
    expect(home.sidebar.room_link(channel.name)).to_be_visible()

    home.sidebar.room_menu(channel.name, "Hide")
    ConfirmModal(home.page).confirm("Yes, hide it!")

    expect(home.sidebar.room_link(channel.name)).to_be_hidden()

    def hidden() -> None:
        assert user_api.subscription(channel.id)["open"] is False

    eventually(hidden)


@pytest.mark.regression
def test_mark_channel_unread_and_read(
    user_page: Page, user_api: RocketChatApi, admin_api: RocketChatApi, channel: Room
) -> None:
    # Arrange: a message exists and the user has read it.
    text = unique("seed")
    admin_api.post_message(channel.id, text)
    room = RoomPage(user_page, channel).open()
    expect(room.message_list).to_contain_text(text)
    eventually(lambda: _assert_unread(user_api, channel, False))

    room.sidebar.room_menu(channel.name, "Mark unread")
    expect(room.sidebar.unread_badge(channel.name)).to_be_visible()
    eventually(lambda: _assert_unread(user_api, channel, True))

    room.sidebar.room_menu(channel.name, "Mark read")
    expect(room.sidebar.unread_badge(channel.name)).to_be_hidden()
    eventually(lambda: _assert_unread(user_api, channel, False))


def _assert_unread(api: RocketChatApi, room: Room, expected: bool) -> None:
    assert bool(api.subscription(room.id).get("alert")) is expected


@pytest.mark.regression
def test_leave_and_rejoin_public_channel(home: HomePage, user_api: RocketChatApi, channel: Room) -> None:
    home.sidebar.room_menu(channel.name, "Leave")
    home.page.get_by_role("dialog").get_by_role("button", name="Leave", exact=True).click()

    expect(home.sidebar.room_link(channel.name)).to_be_hidden()
    eventually(lambda: _assert_member(user_api, channel, False))

    room = RoomPage(home.page, channel).open()
    room.join_button.click()

    expect(home.sidebar.room_link(channel.name)).to_be_visible()
    eventually(lambda: _assert_member(user_api, channel, True))


def _assert_member(api: RocketChatApi, room: Room, expected: bool) -> None:
    assert (api.subscription(room.id) is not None) is expected
