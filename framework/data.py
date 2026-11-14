"""Test-data builders.

Every entity gets a unique name so tests are independent, can run in parallel and
can be re-run against the same server without collisions.
"""

import os
import secrets
import string
import uuid
from dataclasses import dataclass


def unique(prefix: str) -> str:
    """Return a lowercase, URL-safe name such as ``channel-gw0-1a2b3c4d``."""
    worker = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
    return f"{prefix}-{worker}-{uuid.uuid4().hex[:8]}"


def strong_password() -> str:
    """Generate a password that satisfies Rocket.Chat's default password policy."""
    alphabet = string.ascii_letters + string.digits
    body = "".join(secrets.choice(alphabet) for _ in range(16))
    return f"Aa1!{body}"


@dataclass(frozen=True)
class User:
    id: str
    username: str
    password: str
    name: str
    email: str


@dataclass(frozen=True)
class Room:
    id: str
    name: str
    type: str  # "c" public channel, "p" private group, "d" direct message

    @property
    def path(self) -> str:
        return f"/{'group' if self.type == 'p' else 'channel'}/{self.name}"


@dataclass(frozen=True)
class Team:
    id: str
    name: str
    room_id: str
