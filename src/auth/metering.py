"""
Tenant Quota Metering & Sliding-Window Rate Limiting Engine.
Enforces monthly request caps and per-minute throughput limits across tenant workspaces.
"""

import logging
import time
from collections import deque
from datetime import UTC, datetime, timedelta

from src.auth.schemas import PlanTier, QuotaUsageResponse

logger = logging.getLogger("TenantQuotaMeter")


class TenantQuotaMeter:
    """
    In-memory rate limiter and monthly request consumption meter.
    """

    def __init__(self):
        # tenant_id -> deque of timestamps in current minute
        self._minute_windows: dict[str, deque[float]] = {}
        # tenant_id -> monthly request count
        self._monthly_counts: dict[str, int] = {}
        self._last_reset_month: int = datetime.now(UTC).month

    def _check_monthly_reset(self) -> None:
        """Reset monthly counters if calendar month rolled over."""
        current_month = datetime.now(UTC).month
        if current_month != self._last_reset_month:
            self._monthly_counts.clear()
            self._last_reset_month = current_month
            logger.info("Reset all tenant monthly request quotas for new month: %d.", current_month)

    def check_and_consume(
        self,
        tenant_id: str,
        plan_tier: PlanTier = PlanTier.FREE,
        tokens: int = 1,
    ) -> tuple[bool, QuotaUsageResponse, dict[str, str]]:
        """
        Evaluate rate limit and monthly quota. Consumes tokens if allowed.
        Returns: (is_allowed, telemetry, headers)
        """
        self._check_monthly_reset()
        now = time.time()
        minute_ago = now - 60.0

        # 1. Clean sliding minute window
        if tenant_id not in self._minute_windows:
            self._minute_windows[tenant_id] = deque()

        window = self._minute_windows[tenant_id]
        while window and window[0] < minute_ago:
            window.popleft()

        # 2. Check minute rate limit
        rate_limit = plan_tier.rate_limit_per_minute
        current_min_count = len(window)
        is_minute_throttled = (current_min_count + tokens) > rate_limit

        # 3. Check monthly quota
        monthly_quota = plan_tier.monthly_request_quota
        current_monthly_count = self._monthly_counts.get(tenant_id, 0)
        is_monthly_exhausted = (current_monthly_count + tokens) > monthly_quota

        is_allowed = not (is_minute_throttled or is_monthly_exhausted)

        if is_allowed:
            for _ in range(tokens):
                window.append(now)
            self._monthly_counts[tenant_id] = current_monthly_count + tokens
            current_monthly_count += tokens
            current_min_count += tokens

        # Telemetry & Headers
        remaining_min = max(0, rate_limit - current_min_count)
        remaining_month = max(0, monthly_quota - current_monthly_count)
        percent_consumed = round(
            (current_monthly_count / monthly_quota) * 100.0 if monthly_quota > 0 else 0.0,
            1,
        )

        now_dt = datetime.now(UTC)
        next_month = (
            now_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)
        ).replace(day=1)

        telemetry = QuotaUsageResponse(
            tenant_id=tenant_id,
            plan_tier=plan_tier,
            requests_this_month=current_monthly_count,
            monthly_quota_limit=monthly_quota,
            quota_percent_consumed=percent_consumed,
            current_minute_requests=current_min_count,
            minute_rate_limit=rate_limit,
            is_throttled=not is_allowed,
            resets_at=next_month,
        )

        headers = {
            "X-RateLimit-Limit": str(rate_limit),
            "X-RateLimit-Remaining": str(remaining_min),
            "X-Quota-Monthly-Limit": str(monthly_quota),
            "X-Quota-Monthly-Remaining": str(remaining_month),
        }

        return is_allowed, telemetry, headers

    def get_quota_status(
        self, tenant_id: str, plan_tier: PlanTier = PlanTier.FREE
    ) -> QuotaUsageResponse:
        """Query current consumption without deducting tokens."""
        self._check_monthly_reset()
        window = self._minute_windows.get(tenant_id, deque())
        now = time.time()
        active_window = [t for t in window if t >= (now - 60.0)]

        monthly_quota = plan_tier.monthly_request_quota
        current_monthly_count = self._monthly_counts.get(tenant_id, 0)
        percent_consumed = round(
            (current_monthly_count / monthly_quota) * 100.0 if monthly_quota > 0 else 0.0,
            1,
        )

        now_dt = datetime.now(UTC)
        next_month = (
            now_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)
        ).replace(day=1)

        return QuotaUsageResponse(
            tenant_id=tenant_id,
            plan_tier=plan_tier,
            requests_this_month=current_monthly_count,
            monthly_quota_limit=monthly_quota,
            quota_percent_consumed=percent_consumed,
            current_minute_requests=len(active_window),
            minute_rate_limit=plan_tier.rate_limit_per_minute,
            is_throttled=current_monthly_count >= monthly_quota,
            resets_at=next_month,
        )


# Global Singleton Meter
GLOBAL_QUOTA_METER = TenantQuotaMeter()
