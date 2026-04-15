"""Small in-memory TTL cache for forecast responses."""

from __future__ import annotations

import threading
import time
from typing import Any, Hashable


class TTLCache:
    """Thread-safe TTL cache suitable for short-lived API response reuse."""

    def __init__(self, ttl_seconds: int, max_entries: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._data: dict[Hashable, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: Hashable) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None

            expires_at, value = entry
            if expires_at <= time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._prune_expired()
            if len(self._data) >= self.max_entries:
                oldest_key = min(self._data, key=lambda item: self._data[item][0])
                self._data.pop(oldest_key, None)
            self._data[key] = (time.time() + self.ttl_seconds, value)

    def _prune_expired(self) -> None:
        now = time.time()
        expired_keys = [key for key, (expires_at, _) in self._data.items() if expires_at <= now]
        for key in expired_keys:
            self._data.pop(key, None)


def build_forecast_cache_key(
    lat: float,
    lon: float,
    system_size_kw: float,
    tilt: float | None,
    azimuth: float | None,
    losses: float,
    efficiency: float,
) -> tuple[float, float, float, float | None, float | None, float, float]:
    """Normalize request values so semantically identical requests reuse cache entries."""

    def _round(value: float | None, digits: int = 4) -> float | None:
        return None if value is None else round(value, digits)

    return (
        round(lat, 4),
        round(lon, 4),
        round(system_size_kw, 3),
        _round(tilt, 2),
        _round(azimuth, 2),
        round(losses, 2),
        round(efficiency, 2),
    )
