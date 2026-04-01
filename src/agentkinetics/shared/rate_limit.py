"""
Sliding Window Rate Limiter (REM-07)

Thread-safe, in-process rate limiter. Tracks request timestamps per key and
rejects requests when the count exceeds the limit within the sliding window.

Trade-offs vs alternatives:
- No external dependency (Redis, memcached) — suitable for single-process deployment.
- Window state is lost on restart, which is acceptable for a local operator tool.
- Per-key isolation means one abusive key cannot block others.
"""
from __future__ import annotations

import threading
import time
from collections import deque

from agentkinetics.shared.logging import get_logger


logger = get_logger("rate_limit")


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding window rate limiter.

    Args:
        limit: Maximum number of allowed requests within the window.
        window_seconds: Duration of the sliding window in seconds.
    """

    def __init__(self, limit: int, window_seconds: int, name: str = "unnamed") -> None:
        self._limit = limit
        self._window = window_seconds
        self._name = name
        self._buckets: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """
        Check whether a request from the given key is within the rate limit.
        Records the attempt if allowed.

        Returns:
            True if the request is permitted, False if the limit is exceeded.
        """
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = deque()
            bucket = self._buckets[key]
            # Evict expired timestamps
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self._limit:
                logger.warning(
                    "Rate limit denied",
                    ledger_id="LDR-003",
                    limiter=self._name,
                    key=key,
                    current_count=len(bucket),
                    limit=self._limit,
                    window_seconds=self._window,
                )
                return False
            bucket.append(now)
            logger.debug(
                "Rate limit allowed",
                ledger_id="LDR-003",
                limiter=self._name,
                key=key,
                current_count=len(bucket),
                limit=self._limit,
                window_seconds=self._window,
            )
            return True

    def reset(self, key: str) -> None:
        """Clear the rate limit bucket for a given key (useful in tests)."""
        with self._lock:
            self._buckets.pop(key, None)
