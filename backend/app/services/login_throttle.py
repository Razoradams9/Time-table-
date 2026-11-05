"""In-memory login-failure throttle (per email + client IP).

Process-local: resets on restart and is not shared between workers. That is
enough to stop casual password guessing without adding a dependency."""
from __future__ import annotations

import threading
import time
from collections import deque

from app.config import settings

_lock = threading.Lock()
_failures: dict[tuple[str, str], deque[float]] = {}


def _prune(q: deque[float], now: float) -> None:
    cutoff = now - settings.login_window_seconds
    while q and q[0] <= cutoff:
        q.popleft()


def retry_after(key: tuple[str, str]) -> int:
    """Seconds until another attempt is allowed (0 if allowed now)."""
    now = time.monotonic()
    with _lock:
        q = _failures.get(key)
        if not q:
            return 0
        _prune(q, now)
        if not q:
            _failures.pop(key, None)
            return 0
        if len(q) < settings.login_max_attempts:
            return 0
        return max(1, int(q[0] + settings.login_window_seconds - now) + 1)


def record_failure(key: tuple[str, str]) -> None:
    now = time.monotonic()
    with _lock:
        q = _failures.setdefault(key, deque())
        _prune(q, now)
        q.append(now)


def reset(key: tuple[str, str]) -> None:
    with _lock:
        _failures.pop(key, None)
