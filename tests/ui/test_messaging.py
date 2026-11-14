"""Posting and acting on messages. Each UI action is double-checked against the server."""

import pytest
from playwright.sync_api import Page, expect

from framework.api import RocketChatApi
from framework.data import Room, User, unique
from framework.wait import eventually
from pages import RoomPage


@pytest.fixture
def room_page(user_page: Page, channel: Room) -> RoomPage:
    return RoomPage(user_page, channel).open()


def _message_by_text(api: RocketChatApi, room: Room, text: str) -> dict:
    matches = [m for m in api.messages(room) if m.get("msg") == text]
    assert matches, f"no message {text!r} in {room.name}"
    return matches[0]


@pytest.mark.smoke
def test_send_message_in_public_channel(room_page: RoomPage, user_api: RocketChatApi, channel: Room) -> None:
    text = unique("hello")

    message = room_page.send(text)

    expect(message.body).to_have_text(text)
    expect(room_page.composer.input).to_be_empty()
    eventually(lambda: _message_by_text(user_api, channel, text))


@pytest.mark.smoke
def test_send_message_in_private_channel(
    user_page: Page, user_api: RocketChatApi, private_channel: Room
) -> None:
    room_page = RoomPage(user_page, private_channel).open()
    text = unique("secret")

    expect(room_page.send(text).body).to_have_text(text)
    eventually(lambda: _message_by_text(user_api, private_channel, text))


@pytest.mark.regression
def test_edit_own_message(room_page: RoomPage, user_api: RocketChatApi, channel: Room) -> None:
    original, edited = unique("original"), unique("edited")
    expect(room_page.send(original).body).to_have_text(original)

    message = room_page.edit_message(original, edited)

    expect(message.body).to_have_text(edited)
    expect(room_page.message_list).not_to_contain_text(original)
    stored = eventually(lambda: _message_by_text(user_api, channel, edited))
    assert "editedAt" in stored


@pytest.mark.regression
def test_delete_own_message(room_page: RoomPage, user_api: RocketChatApi, channel: Room) -> None:
    text = unique("to-delete")
    message = room_page.send(text)
    expect(message.body).to_have_text(text)

    message.delete()

    expect(room_page.message_list).not_to_contain_text(text)

    def gone() -> None:
        assert all(m.get("msg") != text for m in user_api.messages(channel))

    eventually(gone)


@pytest.mark.regression
def test_react_to_message(room_page: RoomPage, user_api: RocketChatApi, channel: Room, user: User) -> None:
    text = unique("react-to-me")
    message = room_page.send(text)
    expect(message.body).to_have_text(text)

    message.react("thumbsup")

    expect(message.reaction("thumbsup")).to_contain_text("1")

    def reacted() -> None:
        reactions = _message_by_text(user_api, channel, text).get("reactions", {})
        assert reactions.get(":thumbsup:", {}).get("usernames") == [user.username]

    eventually(reacted)


@pytest.mark.regression
def test_reply_in_thread(room_page: RoomPage, user_api: RocketChatApi, channel: Room) -> None:
    parent_text, reply_text = unique("parent"), unique("reply")
    parent = room_page.send(parent_text)
    expect(parent.body).to_have_text(parent_text)

    parent.open_thread()
    room_page.thread.composer.send(reply_text)

    expect(room_page.thread.messages).to_contain_text(reply_text)
    parent_id = eventually(lambda: _message_by_text(user_api, channel, parent_text))["_id"]

    def replied() -> None:
        assert [m["msg"] for m in user_api.thread_messages(parent_id)] == [reply_text]

    eventually(replied)


@pytest.mark.regression
def test_quote_message(room_page: RoomPage, user_api: RocketChatApi, channel: Room) -> None:
    quoted_text, reply_text = unique("quoted"), unique("quoting")
    quoted = room_page.send(quoted_text)
    expect(quoted.body).to_have_text(quoted_text)

    quoted.quote()
    room_page.composer.send(reply_text)

    reply = room_page.message(reply_text)
    expect(reply.root).to_contain_text(quoted_text)  # the quote is rendered inside the new message

    def quoted_on_server() -> None:
        latest = user_api.messages(channel, count=1)[0]
        assert reply_text in latest["msg"]
        assert latest["attachments"][0]["text"] == quoted_text

    eventually(quoted_on_server)
