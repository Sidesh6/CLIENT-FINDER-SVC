"""
Remotive job board collector.
Collects remote software engineering, AI, and developer opportunities from the Remotive public API.
"""

import html
import logging
import re
from datetime import datetime
from typing import Any

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class RemotiveCollector(BaseCollector):
    """
    Collector for discovering remote developer and AI opportunities from Remotive.
    """

    REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        category: str = "software-dev",
        search_query: str | None = None,
        max_projects: int = 30,
    ):
        super().__init__("Remotive")
        self.http_client = http_client or HttpClient(
            timeout=15.0,
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ClientFinderBot/1.0"
            },
        )
        self.category = category
        self.search_query = search_query
        self.max_projects = max_projects

    def _strip_html(self, text: str) -> str:
        """Strip HTML tags from description content."""
        if not text:
            return ""
        decoded = html.unescape(text)
        decoded = re.sub(r"<(p|br\s*/?|li)>", "\n", decoded, flags=re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", "", decoded)
        lines = [line.strip() for line in clean.split("\n")]
        return "\n".join(line for line in lines if line)

    def _parse_salary(self, salary_str: str | None) -> tuple[float | None, str]:
        """Attempt to extract numeric salary and currency from salary string."""
        if not salary_str:
            return None, "USD"
        currency = "USD"
        if "€" in salary_str or "EUR" in salary_str:
            currency = "EUR"
        elif "£" in salary_str or "GBP" in salary_str:
            currency = "GBP"

        # Look for numbers like 120k or 120,000 or $120,000 - $150,000
        numbers = re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:k|K|000)?", salary_str)
        if numbers:
            try:
                # Get the highest figure mentioned in range
                val = numbers[-1].replace(",", "")
                num = float(val)
                if num < 1000 and ("k" in salary_str.lower() or "000" in salary_str):
                    num *= 1000
                return num, currency
            except ValueError:
                pass
        return None, currency

    def collect(self) -> list[dict[str, Any]]:
        """
        Fetch and normalize job postings from Remotive.
        """
        projects: list[dict[str, Any]] = []

        params: dict[str, Any] = {}
        if self.category:
            params["category"] = self.category
        if self.search_query:
            params["search"] = self.search_query
        if self.max_projects:
            params["limit"] = min(self.max_projects * 2, 100)

        try:
            logger.info("Fetching Remotive listings from %s...", self.REMOTIVE_API_URL)
            data = self.http_client.get_json(self.REMOTIVE_API_URL, params=params)

            if not isinstance(data, dict) or "jobs" not in data:
                logger.warning("Remotive returned unexpected payload: %s", type(data))
                return []

            jobs = data.get("jobs", [])
            for item in jobs:
                if len(projects) >= self.max_projects:
                    break

                title = item.get("title", "").strip()
                company = item.get("company_name", "").strip()
                description = self._strip_html(item.get("description", ""))
                url = item.get("url") or f"https://remotive.com/job/{item.get('id', '')}"
                tags = item.get("tags") or []
                raw_tags = [str(t).strip() for t in tags if str(t).strip()]
                job_type = item.get("job_type", "full_time").replace("_", " ").title()

                salary_raw = item.get("salary")
                budget, currency = self._parse_salary(salary_raw)

                posted_at = None
                date_str = item.get("publication_date")
                if date_str:
                    try:
                        posted_at = datetime.fromisoformat(
                            date_str.replace("Z", "+00:00")
                        ).isoformat()
                    except Exception:
                        posted_at = None

                project_dict = {
                    "title": f"{title} at {company}" if company else title,
                    "description": description or f"{title} position at {company}.",
                    "source": self.source_name,
                    "source_url": url,
                    "external_id": str(item.get("id", "")),
                    "client_name": company or None,
                    "skills": raw_tags,
                    "budget": budget,
                    "currency": currency,
                    "project_type": job_type,
                    "posted_at": posted_at,
                    "location": item.get("candidate_required_location") or "Remote",
                }
                projects.append(project_dict)

            logger.info("RemotiveCollector collected %d project(s).", len(projects))

        except HttpClientError as exc:
            logger.error("HTTP error fetching Remotive feed: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error during Remotive collection: %s", exc, exc_info=True)

        return projects
