"""
Notification rate limiting and deduplication tracker.
"""

import logging
from collections import deque
from datetime import UTC, datetime, timedelta

logger = logging.getLogger("NotificationRateLimiter")


class NotificationRateLimiter:
    """
    Prevents duplicate alerts and throttles outbound notifications to external webhooks.
    """

    def __init__(
        self,
        cooldown_seconds: float = 86400.0,  # 24 hours per unique project
        max_alerts_per_minute: int = 15,
    ):
        self.cooldown_seconds = cooldown_seconds
        self.max_alerts_per_minute = max_alerts_per_minute

        # Track last alert timestamp per project key (URL or hash)
        self._project_last_alert: dict[str, datetime] = {}
        # Sliding window timestamps for global rate limiting
        self._sliding_window: deque[datetime] = deque()

    def should_send(self, project_key: str) -> tuple[bool, str | None]:
        """
        Check if an alert should be dispatched or throttled.
        Returns (allowed, reason_if_blocked).
        """
        now = datetime.now(UTC)

        # 1. Project-level deduplication / cooldown check
        last_sent = self._project_last_alert.get(project_key)
        if last_sent:
            elapsed = (now - last_sent).total_seconds()
            if elapsed < self.cooldown_seconds:
                remaining_hrs = round((self.cooldown_seconds - elapsed) / 3600.0, 1)
                return (
                    False,
                    f"Project already notified {round(elapsed/60.0, 1)}m ago (Cooldown: {remaining_hrs}h remaining)",
                )

        # 2. Global rate limit check (sliding window 60s)
        cutoff = now - timedelta(seconds=60)
        while self._sliding_window and self._sliding_window[0] < cutoff:
            self._sliding_window.popleft()

        if len(self._sliding_window) >= self.max_alerts_per_minute:
            return False, f"Global rate limit reached ({self.max_alerts_per_minute} alerts/min)"

        return True, None

    def record_sent(self, project_key: str) -> None:
        """Mark a project alert as successfully sent."""
        now = datetime.now(UTC)
        self._project_last_alert[project_key] = now
        self._sliding_window.append(now)

    def clear(self) -> None:
        """Reset internal rate limiting history."""
        self._project_last_alert.clear()
        self._sliding_window.clear()
