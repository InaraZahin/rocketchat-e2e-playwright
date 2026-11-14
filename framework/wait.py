"""Polling helper for asserting eventually-consistent server state.

The UI often renders optimistically before the server has persisted a change, so API-side
assertions made right after a UI action are retried until they pass (or time out) instead
of sprinkling fixed ``time.sleep`` calls around the suite.
"""

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def eventually(check: Callable[[], T], *, timeout: float = 10.0, interval: float = 0.25) -> T:
    """Call ``check`` until it stops raising ``AssertionError`` and return its result."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            return check()
        except AssertionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(interval)
