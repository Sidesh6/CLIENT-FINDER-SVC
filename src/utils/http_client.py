import logging
import time
from typing import Any

import httpx

from src.utils.identity_rotator import GLOBAL_SCRAPER_IDENTITY_ROTATOR
from src.utils.rate_limiter import GLOBAL_SCRAPER_RATE_LIMITER

logger = logging.getLogger(__name__)


class HttpClientError(Exception):
    """Base exception for all HttpClient errors."""

    pass


class HttpTimeoutError(HttpClientError):
    """Raised when an HTTP request times out."""

    pass


class HttpRateLimitError(HttpClientError):
    """Raised when an HTTP request is rate-limited (HTTP 429)."""

    pass


class HttpStatusError(HttpClientError):
    """Raised when an HTTP request returns an error status code."""

    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} for {url}: {message}")


class HttpClient:
    """
    Robust HTTP client with built-in retries, timeouts, rate limiting, and identity rotation (Fix 4).
    """

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_backoff_factor: float = 1.5,
        rate_limit_delay: float = 0.0,
        user_agent: str = "ClientFinder/1.0 (Opportunity Discovery Service)",
        default_headers: dict[str, str] | None = None,
        rotate_identities: bool = False,
        respect_domain_limits: bool = True,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.rate_limit_delay = rate_limit_delay
        self.rotate_identities = rotate_identities
        self.respect_domain_limits = respect_domain_limits
        self._last_request_time: float = 0.0

        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/html, */*",
        }
        if default_headers:
            headers.update(default_headers)
        self.headers = headers

    def _apply_rate_limiting(self, url: str = "") -> None:
        """Throttle requests according to rate_limit_delay and per-domain limits."""
        if self.rate_limit_delay > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)

        if self.respect_domain_limits and url:
            can_req, wait_secs = GLOBAL_SCRAPER_RATE_LIMITER.can_request(url)
            if not can_req and wait_secs > 0:
                time.sleep(min(wait_secs, 2.0))
            GLOBAL_SCRAPER_RATE_LIMITER.record_request(url)

        self._last_request_time = time.time()

    def request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute an HTTP request with retry logic and error handling.
        """
        rot_headers = (
            GLOBAL_SCRAPER_IDENTITY_ROTATOR.get_headers()
            if self.rotate_identities
            else {}
        )
        request_headers = {**self.headers, **rot_headers, **(headers or {})}
        attempt = 0
        backoff = 1.0

        while attempt <= self.max_retries:
            attempt += 1
            self._apply_rate_limiting(url)
            start_time = time.time()

            try:
                logger.debug(
                    "Executing %s request to %s (attempt %d/%d)",
                    method,
                    url,
                    attempt,
                    self.max_retries + 1,
                )
                with httpx.Client(
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=request_headers,
                        **kwargs,
                    )

                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "%s %s responded with status %d in %.2fms",
                    method,
                    url,
                    response.status_code,
                    duration_ms,
                )

                if response.status_code == 429:
                    if attempt <= self.max_retries:
                        sleep_time = backoff
                        logger.warning(
                            "Rate limited (429) on %s. Retrying in %.2fs (attempt %d/%d)...",
                            url,
                            sleep_time,
                            attempt,
                            self.max_retries,
                        )
                        time.sleep(sleep_time)
                        backoff *= self.retry_backoff_factor
                        continue
                    raise HttpRateLimitError(f"Rate limited (HTTP 429) for URL: {url}")

                if 500 <= response.status_code < 600:
                    if attempt <= self.max_retries:
                        sleep_time = backoff
                        logger.warning(
                            "Server error (%d) on %s. Retrying in %.2fs (attempt %d/%d)...",
                            response.status_code,
                            url,
                            sleep_time,
                            attempt,
                            self.max_retries,
                        )
                        time.sleep(sleep_time)
                        backoff *= self.retry_backoff_factor
                        continue
                    raise HttpStatusError(
                        status_code=response.status_code,
                        message=response.text[:200],
                        url=url,
                    )

                if response.status_code >= 400:
                    raise HttpStatusError(
                        status_code=response.status_code,
                        message=response.text[:200],
                        url=url,
                    )

                return response

            except httpx.TimeoutException as exc:
                duration_ms = (time.time() - start_time) * 1000
                logger.warning(
                    "Timeout after %.2fms on %s (attempt %d/%d): %s",
                    duration_ms,
                    url,
                    attempt,
                    self.max_retries + 1,
                    exc,
                )
                if attempt <= self.max_retries:
                    time.sleep(backoff)
                    backoff *= self.retry_backoff_factor
                    continue
                raise HttpTimeoutError(
                    f"Request timed out after {self.timeout}s for {url}"
                ) from exc

            except httpx.RequestError as exc:
                duration_ms = (time.time() - start_time) * 1000
                logger.warning(
                    "Network error after %.2fms on %s (attempt %d/%d): %s",
                    duration_ms,
                    url,
                    attempt,
                    self.max_retries + 1,
                    exc,
                )
                if attempt <= self.max_retries:
                    time.sleep(backoff)
                    backoff *= self.retry_backoff_factor
                    continue
                raise HttpClientError(f"Request failed for {url}: {exc}") from exc

        raise HttpClientError(f"Maximum retries ({self.max_retries}) exceeded for {url}")

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Execute GET request and return the text content.
        """
        response = self.request("GET", url, params=params, headers=headers, **kwargs)
        return response.text

    def get_text(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Alias for get() to return text content.
        """
        return self.get(url, params=params, headers=headers, **kwargs)

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute GET request and return parsed JSON data.
        """
        response = self.request("GET", url, params=params, headers=headers, **kwargs)
        try:
            return response.json()
        except Exception as exc:
            raise HttpClientError(f"Failed to parse JSON response from {url}: {exc}") from exc

    def post(
        self,
        url: str,
        data: Any = None,
        json: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute POST request and return the HTTP Response object.
        """
        return self.request(
            "POST",
            url,
            params=params,
            headers=headers,
            data=data,
            json=json,
            **kwargs,
        )

    def post_json(
        self,
        url: str,
        json: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute POST request with JSON payload and return the HTTP Response object.
        """
        return self.post(url, json=json, params=params, headers=headers, **kwargs)
