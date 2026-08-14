"""
RemoteOK job board collector.
Collects remote software engineering, AI, and developer opportunities from RemoteOK API.
"""

import html
import logging
import re
from datetime import datetime
from typing import Any

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class RemoteOKCollector(BaseCollector):
    """
    Collector for discovering remote developer and AI contracting opportunities from RemoteOK.
    """

    REMOTEOK_API_URL = "https://remoteok.com/api"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        tag_filters: list[str] | None = None,
        max_projects: int = 30,
    ):
        super().__init__("RemoteOK")
        self.http_client = http_client or HttpClient(
            timeout=15.0,
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ClientFinderBot/1.0"
            },
        )
        self.tag_filters = [t.lower() for t in tag_filters] if tag_filters else None
        self.max_projects = max_projects

    def _strip_html(self, text: str) -> str:
        """Strip HTML markup from job descriptions."""
        if not text:
            return ""
        decoded = html.unescape(text)
        decoded = re.sub(r"<(p|br\s*/?|li)>", "\n", decoded, flags=re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", "", decoded)
        lines = [line.strip() for line in clean.split("\n")]
        return "\n".join(line for line in lines if line)

    def collect(self) -> list[dict[str, Any]]:
        """
        Fetch and normalize job postings from RemoteOK.
        """
        projects: list[dict[str, Any]] = []

        try:
            logger.info("Fetching RemoteOK listings from %s...", self.REMOTEOK_API_URL)
            data = self.http_client.get_json(self.REMOTEOK_API_URL)

            if not isinstance(data, list):
                logger.warning("RemoteOK returned non-list response: %s", type(data))
                return []

            # RemoteOK typically includes a disclaimer/meta object as the first array element
            job_entries = [item for item in data if isinstance(item, dict) and "position" in item]

            for item in job_entries:
                if len(projects) >= self.max_projects:
                    break

                title = item.get("position", "").strip()
                company = item.get("company", "").strip()
                description = self._strip_html(item.get("description", ""))
                url = item.get("url") or f"https://remoteok.com/l/{item.get('id', '')}"
                tags = item.get("tags") or []
                raw_tags = [str(t).strip() for t in tags if str(t).strip()]

                # Apply tag filters if provided
                if self.tag_filters:
                    lower_tags = [t.lower() for t in raw_tags]
                    if not any(f in lower_tags for f in self.tag_filters):
                        continue

                # Parse salary budget if present
                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                budget = None
                if salary_max and float(salary_max) > 0:
                    budget = float(salary_max)
                elif salary_min and float(salary_min) > 0:
                    budget = float(salary_min)

                # Parse publication date
                posted_at = None
                date_str = item.get("date")
                if date_str:
                    try:
                        posted_at = datetime.fromisoformat(
                            date_str.replace("Z", "+00:00")
                        ).isoformat()
                    except Exception:
                        posted_at = None

                project_dict = {
                    "title": f"{title} at {company}" if company else title,
                    "description": description or f"{title} opportunity at {company}.",
                    "source": self.source_name,
                    "source_url": url,
                    "external_id": str(item.get("id", "")),
                    "client_name": company or None,
                    "skills": raw_tags,
                    "budget": budget,
                    "currency": "USD",
                    "project_type": "Contract"
                    if "contract" in [t.lower() for t in raw_tags]
                    else "Full Time",
                    "posted_at": posted_at,
                    "location": item.get("location") or "Remote",
                }
                projects.append(project_dict)

            logger.info("RemoteOKCollector successfully collected %d project(s).", len(projects))

        except HttpClientError as exc:
            logger.error("HTTP error fetching RemoteOK feed: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error during RemoteOK collection: %s", exc, exc_info=True)

        return projects
