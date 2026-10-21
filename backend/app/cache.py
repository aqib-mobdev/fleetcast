import time
from typing import Any


class TTLStore:
    """Small in-process TTL store; swap for Redis in a multi-worker deployment."""

    def __init__(self) -> None:
        self._rows: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        row = self._rows.get(key)
        if row is None:
            return None
        expires, value = row
        if expires < time.monotonic():
            self._rows.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_s: int) -> None:
        if len(self._rows) > 2048:
            now = time.monotonic()
            self._rows = {k: v for k, v in self._rows.items() if v[0] >= now}
        self._rows[key] = (time.monotonic() + ttl_s, value)

    def clear(self) -> None:
        self._rows.clear()


store = TTLStore()
