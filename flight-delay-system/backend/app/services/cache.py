"""Simple in-memory TTL cache."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class CacheEntry:
    """Stores a cached value and its expiration epoch timestamp."""

    value: Any
    expires_at: float


class TTLCache:
    """Thread-safe in-memory TTL cache.

    Parameters:
        default_ttl_seconds: Expiry window applied when set() receives no ttl override.

    Returns:
        None.

    Failure modes:
        Does not raise on missing keys; returns None for stale or absent entries.
    """

    def __init__(self, default_ttl_seconds: int) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._entries: dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        """Reads a value from cache if it is still valid.

        Parameters:
            key: Cache key.

        Returns:
            Cached value or None if key is missing/expired.

        Failure modes:
            Never raises for missing keys; silently evicts expired entries.
        """

        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if time.time() > entry.expires_at:
                self._entries.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Writes a value into cache with TTL.

        Parameters:
            key: Cache key.
            value: Serializable or non-serializable Python object to cache.
            ttl_seconds: Optional TTL override in seconds.

        Returns:
            None.

        Failure modes:
            No explicit failure mode; overwrites existing key.
        """

        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        with self._lock:
            self._entries[key] = CacheEntry(value=value, expires_at=time.time() + ttl)

