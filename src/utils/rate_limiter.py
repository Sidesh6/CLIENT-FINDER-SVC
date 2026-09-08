"""
Rate Limiter for scrapers and collectors in CLIENT-FINDER-SVC (Fix 4).
Protects scraper sessions and network identities from platform rate limits and anti-bot bans.
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Optional


@dataclass
class ScraperLimit:
    max_requests_per_minute: int = 15
    min_delay_between_requests: float = 1.5


class CollectorRateLimiter:
    """
    Per-domain rate limiter with sliding window tracking and jitter delays.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._domain_configs: dict[str, ScraperLimit] = {
            "upwork.com": ScraperLimit(max_requests_per_minute=6, min_delay_between_requests=5.0),
            "freelancer.com": ScraperLimit(max_requests_per_minute=10, min_delay_between_requests=3.0),
            "news.ycombinator.com": ScraperLimit(max_requests_per_minute=20, min_delay_between_requests=1.0),
            "remoteok.com": ScraperLimit(max_requests_per_minute=15, min_delay_between_requests=2.0),
            "weworkremotely.com": ScraperLimit(max_requests_per_minute=15, min_delay_between_requests=2.0),
            "jobicy.com": ScraperLimit(max_requests_per_minute=20, min_delay_between_requests=1.0),
        }
        self._request_history: dict[str, list[float]] = defaultdict(list)
        self._last_request_time: dict[str, float] = defaultdict(float)

    def _extract_domain(self, url_or_domain: str) -> str:
        s = url_or_domain.lower().replace("https://", "").replace("http://", "")
        domain = s.split("/")[0].split("?")[0]
        for configured in self._domain_configs:
            if configured in domain:
                return configured
        return domain

    def can_request(self, url_or_domain: str) -> tuple[bool, float]:
        domain = self._extract_domain(url_or_domain)
        config = self._domain_configs.get(domain, ScraperLimit())

        with self._lock:
            now = time.time()
            last_time = self._last_request_time[domain]

            # Spacing check
            elapsed = now - last_time
            if elapsed < config.min_delay_between_requests:
                wait_needed = config.min_delay_between_requests - elapsed
                return False, round(wait_needed, 2)

            # Sliding window check
            window_start = now - 60.0
            history = [t for t in self._request_history[domain] if t >= window_start]
            self._request_history[domain] = history

            if len(history) >= config.max_requests_per_minute:
                wait_needed = 60.0 - (now - history[0])
                return False, round(max(0.1, wait_needed), 2)

            return True, 0.0

    def record_request(self, url_or_domain: str) -> None:
        domain = self._extract_domain(url_or_domain)
        with self._lock:
            now = time.time()
            self._last_request_time[domain] = now
            self._request_history[domain].append(now)


GLOBAL_SCRAPER_RATE_LIMITER = CollectorRateLimiter()
