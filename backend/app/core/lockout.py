"""Per-email login lockout: after too many failed logins, block that email for a cooldown.

In-process (single-worker) state. For multi-process/replicated deploys, back this with
Redis (settings.rate_limit_storage) — the interface (is_locked/record_failure/record_success)
stays the same. This complements the global IP rate limit in core/rate_limit.py.
"""

from __future__ import annotations

import time
from collections import defaultdict

MAX_FAILURES = 5          # failures within the window before locking
WINDOW_SEC = 15 * 60      # rolling window for counting failures
LOCK_SEC = 15 * 60        # how long the lock lasts

_attempts: dict[str, list[float]] = defaultdict(list)
_locked_until: dict[str, float] = {}


def is_locked(email: str) -> float:
    """Return remaining lock time in seconds (0.0 if not locked)."""
    e = email.lower()
    until = _locked_until.get(e)
    if until is None:
        return 0.0
    remaining = until - time.time()
    if remaining <= 0:
        _locked_until.pop(e, None)
        _attempts.pop(e, None)
        return 0.0
    return remaining


def record_failure(email: str) -> None:
    e = email.lower()
    now = time.time()
    window = [t for t in _attempts[e] if now - t < WINDOW_SEC]
    window.append(now)
    _attempts[e] = window
    if len(window) >= MAX_FAILURES:
        _locked_until[e] = now + LOCK_SEC


def record_success(email: str) -> None:
    e = email.lower()
    _attempts.pop(e, None)
    _locked_until.pop(e, None)


def reset() -> None:
    """Clear all state (tests)."""
    _attempts.clear()
    _locked_until.clear()
