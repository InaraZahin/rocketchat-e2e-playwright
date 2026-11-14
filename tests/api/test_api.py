"""Fast REST-level checks. They catch backend regressions without paying for a browser."""

import httpx
import pytest

from framework.api import ApiError, RocketChatApi
from framework.config import Settings
from framework.data import Room, User, unique

pytestmark = pytest.mark.api


@pytest.mark.smoke
def test_server_is_up_and_reports_version(admin_api: RocketChatApi) -> None:
    info = admin_api.server_info()
    assert info["success"] is True
    assert info["version"]


@pytest.mark.smoke
def test_login_rejects_wrong_password(settings: Settings, user: User) -> None:
    with RocketChatApi(settings.url) as api, pytest.raises(ApiError) as error:
        api.login(user.username, "wrong-password")
    assert error.value.status == 401


@pytest.mark.regression
def test_protected_endpoint_requires_authentication(settings: Settings) -> None:
    response = httpx.get(f"{settings.url}/api/v1/me")
    assert response.status_code == 401


@pytest.mark.regression
def test_logged_in_user_identity(user_api: RocketChatApi, user: User) -> None:
    me = user_api.me()
    assert me["username"] == user.username
    assert me["_id"] == user.id


@pytest.mark.regression
def test_member_can_post_and_read_messages(user_api: RocketChatApi, channel: Room) -> None:
    text = unique("api-message")
    posted = user_api.post_message(channel.id, text)
    assert posted["msg"] == text
    assert any(m["_id"] == posted["_id"] for m in user_api.messages(channel))


@pytest.mark.regression
def test_non_member_cannot_read_private_channel(
    admin_api: RocketChatApi, user_api: RocketChatApi, cleanup
) -> None:
    secret = admin_api.create_channel(private=True)
    cleanup(lambda: admin_api.delete_room(secret))
    with pytest.raises(ApiError):
        user_api.messages(secret)


@pytest.mark.regression
def test_regular_user_cannot_delete_users(user_api: RocketChatApi, admin_api: RocketChatApi, cleanup) -> None:
    victim = admin_api.create_user()
    cleanup(lambda: admin_api.delete_user(victim.id))
    with pytest.raises(ApiError) as error:
        user_api.delete_user(victim.id)
    assert error.value.status in (401, 403)
    assert admin_api.find_user(victim.username) is not None
