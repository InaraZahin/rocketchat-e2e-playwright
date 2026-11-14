"""Shared fixtures.

Design goals:

* **Isolation** - every test gets its own freshly created user (and rooms/teams as needed),
  so tests never depend on each other, on execution order, or on leftovers from earlier runs.
  This is what makes ``pytest -n auto`` safe.
* **Fast arrange via API, act via UI, assert via UI *and* API.**
* **Guaranteed cleanup** - everything a test creates is deleted afterwards, even on failure.
* **No UI login for every test** - sessions are injected from an API token. Only the
  authentication tests drive the real login form.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from playwright.sync_api import BrowserContext, Page, expect

from framework.api import ApiError, RocketChatApi
from framework.config import Settings, get_settings
from framework.data import Room, Team, User
from framework.wait import eventually

# ----------------------------------------------------------------------------- config


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def base_url(settings: Settings) -> str:
    """Lets page objects navigate with relative paths (consumed by pytest-playwright)."""
    return settings.url


@pytest.fixture(scope="session", autouse=True)
def _configure_expect(settings: Settings) -> None:
    expect.set_options(timeout=settings.ui_timeout_ms)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    return {**browser_context_args, "viewport": {"width": 1440, "height": 900}, "locale": "en-US"}


# ----------------------------------------------------------------------------- cleanup


@pytest.fixture
def cleanup() -> Iterator[Callable[[Callable[[], Any]], None]]:
    """Register teardown callbacks; they run in reverse order after the test.

    A failing cleanup never hides the real test result - it is reported as a warning.
    """
    callbacks: list[Callable[[], Any]] = []
    yield callbacks.append
    for callback in reversed(callbacks):
        try:
            callback()
        except ApiError as err:
            if err.status != 404:
                warnings.warn(f"cleanup failed: {err}", stacklevel=1)


# ----------------------------------------------------------------------------- API


@pytest.fixture(scope="session")
def admin_api(settings: Settings) -> Iterator[RocketChatApi]:
    with RocketChatApi(settings.url, settings.api_timeout_s) as api:
        api.login(settings.admin_username, settings.admin_password.get_secret_value())
        yield api


@pytest.fixture(scope="session", autouse=True)
def _workspace_is_writable(admin_api: RocketChatApi) -> None:
    """Fail fast with a clear message if the server is in read-only mode.

    Unlicensed Rocket.Chat (7.x+) blocks writes until it has reported statistics to
    collector.rocket.chat, which happens asynchronously shortly after startup. A server
    with no route to that host stays read-only, and every messaging test would fail
    with a confusing ``restricted-workspace`` error.
    """
    setting = "Cloud_Workspace_AirGapped_Restrictions_Remaining_Days"
    try:
        eventually(lambda: _assert_not_restricted(admin_api.setting(setting)), timeout=120, interval=2)
    except AssertionError:
        pytest.exit(
            "Rocket.Chat is in read-only (air-gapped) mode: the server could not reach "
            "collector.rocket.chat. Give it outbound internet access and restart it.",
            returncode=3,
        )


def _assert_not_restricted(remaining_days: int) -> None:
    assert remaining_days != 0, "workspace is restricted"


@pytest.fixture
def user(admin_api: RocketChatApi, cleanup) -> User:
    """A brand-new regular user, deleted after the test."""
    new_user = admin_api.create_user()
    cleanup(lambda: admin_api.delete_user(new_user.id))
    return new_user


@pytest.fixture
def user_api(user: User, settings: Settings) -> Iterator[RocketChatApi]:
    """API client authenticated as ``user`` - used to verify state from the user's point of view."""
    with RocketChatApi(settings.url, settings.api_timeout_s) as api:
        api.login(user.username, user.password)
        yield api


@pytest.fixture
def channel(admin_api: RocketChatApi, user: User, cleanup) -> Room:
    """A public channel that ``user`` is a member of."""
    room = admin_api.create_channel(members=[user.username])
    cleanup(lambda: admin_api.delete_room(room))
    return room


@pytest.fixture
def private_channel(admin_api: RocketChatApi, user: User, cleanup) -> Room:
    room = admin_api.create_channel(private=True, members=[user.username])
    cleanup(lambda: admin_api.delete_room(room))
    return room


@pytest.fixture
def team(admin_api: RocketChatApi, user: User, cleanup) -> Team:
    """A public team owned by the admin with ``user`` as a member."""
    new_team = admin_api.create_team(members=[user.username])
    cleanup(lambda: admin_api.delete_team(new_team.name))
    return new_team


# ----------------------------------------------------------------------------- browser


def _authenticated_page(new_context: Callable[..., BrowserContext], settings: Settings, api: RocketChatApi):
    """Open a page whose browser context is already signed in with ``api``'s token.

    The Meteor client resumes a session from these localStorage keys. The expiry key is
    required: without it the client treats the token as expired and logs out.
    """
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    storage_state = {
        "cookies": [],
        "origins": [
            {
                "origin": settings.url,
                "localStorage": [
                    {"name": "Meteor.loginToken", "value": api.auth_token},
                    {"name": "Meteor.userId", "value": api.user_id},
                    {"name": "Meteor.loginTokenExpires", "value": expires},
                ],
            }
        ],
    }
    context = new_context(storage_state=storage_state)
    context.set_default_timeout(settings.ui_timeout_ms)
    return context.new_page()


@pytest.fixture
def user_page(new_context, user_api: RocketChatApi, settings: Settings) -> Page:
    """A browser page signed in as the fresh ``user``."""
    return _authenticated_page(new_context, settings, user_api)


@pytest.fixture
def admin_page(new_context, admin_api: RocketChatApi, settings: Settings) -> Page:
    """A browser page signed in as the workspace administrator."""
    return _authenticated_page(new_context, settings, admin_api)
