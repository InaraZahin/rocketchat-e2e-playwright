"""Workspace administration: user management and access control."""

import pytest
from playwright.sync_api import Page, expect

from framework.api import RocketChatApi
from framework.data import strong_password, unique
from framework.wait import eventually
from pages import AdminUsersPage


@pytest.mark.smoke
def test_admin_creates_user(admin_page: Page, admin_api: RocketChatApi, cleanup) -> None:
    username = unique("ui-user")

    def delete() -> None:
        created = admin_api.find_user(username)
        if created:
            admin_api.delete_user(created["_id"])

    cleanup(delete)
    users_page = AdminUsersPage(admin_page).open()

    users_page.open_new_user_form().fill_and_submit(
        name="UI Created User", username=username, email=f"{username}@example.com", password=strong_password()
    )

    def created() -> None:
        user = admin_api.find_user(username)
        assert user is not None, "user was not created on the server"
        assert user["name"] == "UI Created User"
        assert "user" in user["roles"]

    eventually(created)
    users_page.open()
    expect(users_page.row(username)).to_be_visible()


@pytest.mark.regression
def test_regular_user_cannot_open_user_administration(user_page: Page) -> None:
    users_page = AdminUsersPage(user_page)
    user_page.goto(users_page.path)

    expect(user_page.get_by_role("main")).to_contain_text("You are not authorized")
    expect(users_page.new_user_button).to_have_count(0)
