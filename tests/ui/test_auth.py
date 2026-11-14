"""Authentication through the real login form (the only tests that do not inject a session)."""

import re

import pytest
from playwright.sync_api import Page, expect

from framework.data import User
from pages import HomePage, LoginPage


@pytest.fixture
def login_page(page: Page) -> LoginPage:
    return LoginPage(page).open()


@pytest.mark.smoke
def test_login_form_offers_recovery_and_registration(login_page: LoginPage) -> None:
    expect(login_page.page).to_have_title(re.compile("Rocket.Chat"))
    expect(login_page.forgot_password_link).to_be_visible()
    expect(login_page.register_link).to_be_visible()


@pytest.mark.smoke
def test_user_can_log_in_with_valid_credentials(login_page: LoginPage, user: User) -> None:
    login_page.login(user.username, user.password)

    home = HomePage(login_page.page)
    expect(home.heading).to_be_visible()
    expect(home.navbar.user_menu_button).to_be_visible()


@pytest.mark.regression
def test_login_is_rejected_with_wrong_password(login_page: LoginPage, user: User) -> None:
    login_page.login(user.username, "definitely-not-the-password")

    expect(login_page.error).to_have_text("User not found or incorrect password")
    expect(login_page.username).to_have_attribute("aria-invalid", "true")
    expect(login_page.submit).to_be_visible()


@pytest.mark.regression
def test_unknown_user_cannot_log_in(login_page: LoginPage) -> None:
    login_page.login("no-such-user-for-e2e", "Some-Password-123!")

    expect(login_page.error).to_have_text("User not found or incorrect password")


@pytest.mark.smoke
def test_user_can_log_out(login_page: LoginPage, user: User) -> None:
    login_page.login(user.username, user.password)
    home = HomePage(login_page.page)
    expect(home.heading).to_be_visible()

    home.navbar.logout()

    expect(login_page.form).to_be_visible()
    # A reload must not restore the session.
    login_page.page.reload()
    expect(login_page.form).to_be_visible()
