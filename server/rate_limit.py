"""Small per-process sliding-window limiter for the single-instance app."""
from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class SlidingWindowLimiter:
    def __init__(self, max_keys: int = 5000) -> None:
        self._entries: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._max_keys = max_keys

    def consume(self, key: str, limit: int, window_seconds: int) -> int:
        now = monotonic()
        with self._lock:
            events = self._entries[key]
            while events and now - events[0] >= window_seconds:
                events.popleft()
            if len(events) >= limit:
                return max(1, int(window_seconds - (now - events[0])))
            events.append(now)
            if len(self._entries) > self._max_keys:
                expired = [
                    item for item, timestamps in self._entries.items()
                    if not timestamps or now - timestamps[-1] >= window_seconds
                ]
                for item in expired:
                    self._entries.pop(item, None)
            return 0


limiter = SlidingWindowLimiter()
