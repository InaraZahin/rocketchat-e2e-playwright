"""Finding rooms, people and teams: sidebar search and the workspace directory."""

import pytest
from playwright.sync_api import Page, expect

from framework.api import RocketChatApi
from framework.data import Room, Team, User, unique
from pages import DirectoryPage, HomePage


@pytest.mark.smoke
def test_sidebar_search_opens_room(user_page: Page, channel: Room) -> None:
    home = HomePage(user_page).open()

    home.sidebar.search(channel.name)
    home.sidebar.search_result(channel.name).click()

    expect(user_page).to_have_url(f"{channel.path}")
    expect(user_page.get_by_role("main").get_by_role("heading", name=channel.name, level=1)).to_be_visible()


@pytest.mark.regression
def test_sidebar_search_does_not_list_rooms_user_cannot_see(
    user_page: Page, admin_api: RocketChatApi, user: User, cleanup
) -> None:
    prefix = unique("scope")
    visible = admin_api.create_channel(name=f"{prefix}-visible", private=True, members=[user.username])
    hidden = admin_api.create_channel(name=f"{prefix}-hidden", private=True)  # user is NOT a member
    cleanup(lambda: admin_api.delete_room(visible))
    cleanup(lambda: admin_api.delete_room(hidden))
    home = HomePage(user_page).open()

    home.sidebar.search(prefix)

    # Positive control first: proves results have loaded before asserting absence.
    expect(home.sidebar.search_result(visible.name)).to_be_visible()
    expect(home.sidebar.search_result(hidden.name)).to_have_count(0)


@pytest.mark.regression
def test_directory_finds_channel(user_page: Page, channel: Room) -> None:
    directory = DirectoryPage(user_page).open()

    directory.search("Channels", channel.name)
    expect(directory.result(channel.name)).to_have_count(1)
    directory.result(channel.name).click()

    expect(user_page.get_by_role("main").get_by_role("heading", name=channel.name, level=1)).to_be_visible()


@pytest.mark.regression
def test_directory_finds_user(user_page: Page, admin_api, cleanup) -> None:
    other: User = admin_api.create_user()
    cleanup(lambda: admin_api.delete_user(other.id))
    directory = DirectoryPage(user_page).open()

    directory.search("Users", other.username)

    expect(directory.result(other.username)).to_have_count(1)


@pytest.mark.regression
def test_directory_finds_team(user_page: Page, team: Team) -> None:
    directory = DirectoryPage(user_page).open()

    directory.search("Teams", team.name)

    expect(directory.result(team.name)).to_have_count(1)
