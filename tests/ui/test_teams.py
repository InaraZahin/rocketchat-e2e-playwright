"""Teams: creation and channel management. Run as the admin, who owns the team fixtures."""

import pytest
from playwright.sync_api import Page, expect

from framework.api import RocketChatApi
from framework.data import Room, Team, unique
from framework.wait import eventually
from pages import HomePage
from pages.team_page import TeamPage


@pytest.fixture
def admin_channel(admin_api: RocketChatApi, cleanup) -> Room:
    room = admin_api.create_channel()
    cleanup(lambda: admin_api.delete_room(room))
    return room


@pytest.mark.smoke
def test_create_team(admin_page: Page, admin_api: RocketChatApi, cleanup) -> None:
    name = unique("ui-team")
    cleanup(lambda: admin_api.team_info(name) and admin_api.delete_team(name))
    home = HomePage(admin_page).open()

    home.navbar.open_create_team().create(name, private=False, topic="E2E team")

    expect(admin_page.get_by_role("main").get_by_role("heading", name=name, level=1)).to_be_visible()
    expect(home.sidebar.room_link(name)).to_be_visible()

    def created() -> None:
        info = admin_api.team_info(name)
        assert info is not None, "team was not created on the server"
        assert info["type"] == 0  # public

    eventually(created)


@pytest.mark.regression
def test_add_existing_channel_to_team(
    admin_page: Page, admin_api: RocketChatApi, team: Team, admin_channel: Room
) -> None:
    team_page = TeamPage(admin_page, team).open()

    panel = team_page.open_channels()
    panel.add_existing(admin_channel.name)

    expect(panel.channel(admin_channel.name)).to_be_visible()
    eventually(lambda: _assert_in_team(admin_api, team, admin_channel.name))


@pytest.mark.regression
def test_create_new_channel_inside_team(
    admin_page: Page, admin_api: RocketChatApi, team: Team, cleanup
) -> None:
    name = unique("team-channel")

    def delete() -> None:
        info = admin_api.room_info(room_name=name)
        if info:
            admin_api.delete_room(Room(info["_id"], name, info["t"]))

    cleanup(delete)
    team_page = TeamPage(admin_page, team).open()

    team_page.open_channels().create_new().create(name, private=False)

    eventually(lambda: _assert_in_team(admin_api, team, name))


def _assert_in_team(api: RocketChatApi, team: Team, room_name: str) -> None:
    assert room_name in api.team_room_names(team.name)
