"""
Identity and User-Agent Rotator for collectors in CLIENT-FINDER-SVC (Fix 4).
Rotates headers, client fingerprints, and session identifiers.
"""

import itertools
import random
from dataclasses import dataclass
from threading import Lock


@dataclass
class ScraperIdentity:
    user_agent: str
    accept_language: str = "en-US,en;q=0.9"
    sec_ch_ua: str = '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"'
    sec_ch_ua_platform: str = '"Windows"'


class ScraperIdentityRotator:
    """
    Rotates User-Agents and HTTP client headers across collection passes.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._pool = [
            ScraperIdentity(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                sec_ch_ua_platform='"Windows"',
            ),
            ScraperIdentity(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                sec_ch_ua_platform='"macOS"',
            ),
            ScraperIdentity(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                sec_ch_ua_platform='"Linux"',
            ),
            ScraperIdentity(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
                sec_ch_ua_platform='"Windows"',
            ),
        ]
        self._cycle = itertools.cycle(self._pool)

    def get_headers(self) -> dict[str, str]:
        with self._lock:
            ident = next(self._cycle)
        return {
            "User-Agent": ident.user_agent,
            "Accept-Language": ident.accept_language,
            "Sec-CH-UA": ident.sec_ch_ua,
            "Sec-CH-UA-Platform": ident.sec_ch_ua_platform,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }


GLOBAL_SCRAPER_IDENTITY_ROTATOR = ScraperIdentityRotator()
