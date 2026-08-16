"""
Arbeitnow remote & tech job board collector.
Collects remote software engineering, AI, and developer opportunities from the Arbeitnow public API.
"""

import html
import logging
import re
from datetime import datetime
from typing import Any

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class ArbeitnowCollector(BaseCollector):
    """
    Collector for discovering remote and global developer opportunities from Arbeitnow.
    """

    ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        max_projects: int = 30,
    ):
        super().__init__("Arbeitnow")
        self.http_client = http_client or HttpClient(
            timeout=15.0,
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ClientFinderBot/1.0"
            },
        )
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

    def collect(self) -> list[dict[str, Any]]:
        """
        Fetch and normalize job postings from Arbeitnow.
        """
        projects: list[dict[str, Any]] = []

        try:
            logger.info("Fetching Arbeitnow listings from %s...", self.ARBEITNOW_API_URL)
            data = self.http_client.get_json(self.ARBEITNOW_API_URL)

            if not isinstance(data, dict) or "data" not in data:
                logger.warning("Arbeitnow returned unexpected payload: %s", type(data))
                return []

            items = data.get("data", [])
            for item in items:
                if len(projects) >= self.max_projects:
                    break

                title = item.get("title", "").strip()
                company = item.get("company_name", "").strip()
                description = self._strip_html(item.get("description", ""))
                url = item.get("url") or f"https://www.arbeitnow.com/view/{item.get('slug', '')}"
                tags = item.get("tags") or []
                raw_tags = [str(t).strip() for t in tags if str(t).strip()]
                job_types = item.get("job_types") or ["Full Time"]
                job_type = job_types[0] if isinstance(job_types, list) and job_types else "Full Time"

                created_epoch = item.get("created_at")
                posted_at = None
                if created_epoch:
                    try:
                        posted_at = datetime.fromtimestamp(created_epoch).isoformat()
                    except Exception:
                        posted_at = None

                project_dict = {
                    "title": f"{title} at {company}" if company else title,
                    "description": description or f"{title} position at {company}.",
                    "source": self.source_name,
                    "source_url": url,
                    "external_id": str(item.get("slug", "")),
                    "client_name": company or None,
                    "skills": raw_tags,
                    "budget": None,
                    "currency": "EUR" if "EU" in (item.get("location") or "") else "USD",
                    "project_type": str(job_type),
                    "posted_at": posted_at,
                    "location": item.get("location") or "Remote",
                }
                projects.append(project_dict)

            logger.info("ArbeitnowCollector collected %d project(s).", len(projects))

        except HttpClientError as exc:
            logger.error("HTTP error fetching Arbeitnow feed: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error during Arbeitnow collection: %s", exc, exc_info=True)

        return projects
