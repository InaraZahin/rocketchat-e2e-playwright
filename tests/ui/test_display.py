"""Sidebar display preferences. Each test runs as a fresh user, so changes never leak."""

import pytest
from playwright.sync_api import Page, expect

from framework.api import RocketChatApi
from framework.wait import eventually
from pages import HomePage
from pages.components.navbar import ViewMode


@pytest.mark.regression
@pytest.mark.parametrize("mode", ["Extended", "Condensed", "Medium"])
def test_change_sidebar_view_mode(user_page: Page, user_api: RocketChatApi, mode: ViewMode) -> None:
    home = HomePage(user_page).open()

    home.navbar.set_view_mode(mode)

    def saved() -> None:
        assert user_api.preferences()["sidebarViewMode"] == mode.lower()

    eventually(saved)
    # The preference survives a reload, i.e. it was persisted rather than only applied locally.
    user_page.reload()
    home.navbar.display_button.click()
    expect(user_page.get_by_role("menu", name="Display").get_by_role("radio", name=mode)).to_be_checked()
