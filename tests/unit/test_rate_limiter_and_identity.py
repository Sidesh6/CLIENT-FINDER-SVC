"""
Unit tests for CollectorRateLimiter and ScraperIdentityRotator (Fix 4).
"""

from src.utils.identity_rotator import ScraperIdentityRotator
from src.utils.rate_limiter import CollectorRateLimiter


def test_scraper_rate_limiter():
    limiter = CollectorRateLimiter()

    # First request on upwork.com is allowed
    can_req, wait = limiter.can_request("https://www.upwork.com/nx/search/jobs")
    assert can_req is True
    assert wait == 0.0

    limiter.record_request("https://www.upwork.com/nx/search/jobs")

    # Immediate second request on upwork.com requires delay spacing
    can_req_2, wait_2 = limiter.can_request("https://www.upwork.com/nx/search/jobs")
    assert can_req_2 is False
    assert wait_2 > 0.0


def test_scraper_identity_rotator():
    rotator = ScraperIdentityRotator()
    h1 = rotator.get_headers()
    h2 = rotator.get_headers()
    h3 = rotator.get_headers()

    assert "User-Agent" in h1
    assert "Sec-CH-UA" in h1
    assert h1["User-Agent"] != h2["User-Agent"]
