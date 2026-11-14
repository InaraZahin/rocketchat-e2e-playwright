"""Thin, typed wrapper over the Rocket.Chat REST API (``/api/v1``).

The suite uses the API for two things UI tests should never do through the UI:

* **Arrange** - create users, rooms and teams quickly and deterministically.
* **Assert** - confirm that an action performed in the UI really changed server state.
"""

from __future__ import annotations

from typing import Any

import httpx

from framework.data import Room, Team, User, strong_password, unique


class ApiError(RuntimeError):
    def __init__(self, method: str, path: str, status: int, body: Any) -> None:
        super().__init__(f"{method} {path} -> HTTP {status}: {body}")
        self.status = status
        self.body = body


class RocketChatApi:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=f"{self.base_url}/api/v1", timeout=timeout)
        self.user_id: str | None = None
        self.auth_token: str | None = None

    # ------------------------------------------------------------------ plumbing
    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> RocketChatApi:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._http.request(method, path, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = response.text
        if response.is_error or (isinstance(body, dict) and body.get("success") is False):
            raise ApiError(method, path, response.status_code, body)
        return body

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        return self._request("GET", path, params=params)

    def post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("POST", path, json=payload or {})

    # ---------------------------------------------------------------- auth
    def login(self, username: str, password: str) -> RocketChatApi:
        data = self.post("login", {"user": username, "password": password})["data"]
        self.user_id, self.auth_token = data["userId"], data["authToken"]
        self._http.headers.update({"X-User-Id": self.user_id, "X-Auth-Token": self.auth_token})
        return self

    def logout(self) -> None:
        if self.auth_token:
            self.post("logout")
            self.user_id = self.auth_token = None
            self._http.headers.pop("X-User-Id", None)
            self._http.headers.pop("X-Auth-Token", None)

    def me(self) -> dict[str, Any]:
        return self.get("me")

    def setting(self, setting_id: str) -> Any:
        return self.get(f"settings/{setting_id}")["value"]

    def server_info(self) -> dict[str, Any]:
        # Lives at /api/info, outside the versioned namespace (absolute URLs bypass base_url).
        return self.get(f"{self.base_url}/api/info")

    # ---------------------------------------------------------------- users
    def create_user(self, *, username: str | None = None, name: str | None = None) -> User:
        username = username or unique("user")
        password = strong_password()
        payload = {
            "username": username,
            "name": name or username.replace("-", " ").title(),
            "email": f"{username}@example.com",
            "password": password,
            "verified": True,
            "requirePasswordChange": False,
            "joinDefaultChannels": False,
            "sendWelcomeEmail": False,
        }
        user = self.post("users.create", payload)["user"]
        return User(user["_id"], username, password, payload["name"], payload["email"])

    def find_user(self, username: str) -> dict[str, Any] | None:
        try:
            return self.get("users.info", username=username)["user"]
        except ApiError as err:
            if err.status in (400, 404):
                return None
            raise

    def delete_user(self, user_id: str) -> None:
        self.post("users.delete", {"userId": user_id, "confirmRelinquish": True})

    def preferences(self) -> dict[str, Any]:
        return self.get("users.getPreferences")["preferences"]

    # ---------------------------------------------------------------- rooms
    def create_channel(
        self, *, name: str | None = None, private: bool = False, members: list[str] | None = None
    ) -> Room:
        endpoint = "groups.create" if private else "channels.create"
        key = "group" if private else "channel"
        room = self.post(endpoint, {"name": name or unique("room"), "members": members or []})[key]
        return Room(room["_id"], room["name"], room["t"])

    def room_info(self, *, room_name: str | None = None, room_id: str | None = None) -> dict[str, Any] | None:
        params = {"roomName": room_name} if room_name else {"roomId": room_id}
        try:
            return self.get("rooms.info", **params)["room"]
        except ApiError as err:
            if err.status in (400, 404):
                return None
            raise

    def delete_room(self, room: Room) -> None:
        # rooms.delete works for admins on any room type, including private groups they are not in.
        self.post("rooms.delete", {"roomId": room.id})

    def subscription(self, room_id: str) -> dict[str, Any] | None:
        return self.get("subscriptions.getOne", roomId=room_id).get("subscription")

    # ---------------------------------------------------------------- teams
    def create_team(self, *, members: list[str] | None = None) -> Team:
        team = self.post("teams.create", {"name": unique("team"), "type": 0, "members": members or []})[
            "team"
        ]
        return Team(team["_id"], team["name"], team["roomId"])

    def team_info(self, team_name: str) -> dict[str, Any] | None:
        try:
            return self.get("teams.info", teamName=team_name)["teamInfo"]
        except ApiError as err:
            if err.status in (400, 404):
                return None
            raise

    def team_room_names(self, team_name: str) -> set[str]:
        rooms = self.get("teams.listRooms", teamName=team_name)["rooms"]
        return {room["name"] for room in rooms}

    def delete_team(self, team_name: str) -> None:
        self.post("teams.delete", {"teamName": team_name})

    # ---------------------------------------------------------------- messages
    def post_message(self, room_id: str, text: str) -> dict[str, Any]:
        return self.post("chat.postMessage", {"roomId": room_id, "text": text})["message"]

    def messages(self, room: Room, count: int = 50) -> list[dict[str, Any]]:
        endpoint = {"c": "channels.messages", "p": "groups.messages", "d": "im.messages"}[room.type]
        return self.get(endpoint, roomId=room.id, count=count, sort='{"ts": -1}')["messages"]

    def thread_messages(self, thread_id: str) -> list[dict[str, Any]]:
        return self.get("chat.getThreadMessages", tmid=thread_id)["messages"]
