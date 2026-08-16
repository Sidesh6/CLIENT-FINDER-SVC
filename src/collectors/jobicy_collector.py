"""
Jobicy remote developer jobs collector.
Collects remote software engineering, AI, and developer opportunities from the Jobicy public API.
"""

import html
import logging
import re
from datetime import datetime
from typing import Any

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class JobicyCollector(BaseCollector):
    """
    Collector for discovering remote developer and engineering opportunities from Jobicy.
    """

    JOBICY_API_URL = "https://jobicy.com/api/v2/remote-jobs"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        industry: str = "engineering",
        tag: str | None = "developer",
        max_projects: int = 30,
    ):
        super().__init__("Jobicy")
        self.http_client = http_client or HttpClient(
            timeout=15.0,
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ClientFinderBot/1.0"
            },
        )
        self.industry = industry
        self.tag = tag
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
        Fetch and normalize job postings from Jobicy.
        """
        projects: list[dict[str, Any]] = []

        params: dict[str, Any] = {"count": min(self.max_projects * 2, 50)}
        if self.industry:
            params["industry"] = self.industry
        if self.tag:
            params["tag"] = self.tag

        try:
            logger.info("Fetching Jobicy listings from %s...", self.JOBICY_API_URL)
            data = self.http_client.get_json(self.JOBICY_API_URL, params=params)

            if not isinstance(data, dict) or "jobs" not in data:
                logger.warning("Jobicy returned unexpected payload: %s", type(data))
                return []

            jobs = data.get("jobs", [])
            for item in jobs:
                if len(projects) >= self.max_projects:
                    break

                title = item.get("jobTitle", "").strip()
                company = item.get("companyName", "").strip()
                description = self._strip_html(item.get("jobDescription", ""))
                url = item.get("url") or f"https://jobicy.com/jobs/{item.get('id', '')}"
                raw_job_type = item.get("jobType", "Full-Time")
                if isinstance(raw_job_type, list):
                    job_type = str(raw_job_type[0]) if raw_job_type else "Full-Time"
                else:
                    job_type = str(raw_job_type) if raw_job_type else "Full-Time"




                # Budget calculation from salary min/max
                budget = None
                salary_max = item.get("annualSalaryMax")
                salary_min = item.get("annualSalaryMin")
                if salary_max and float(salary_max) > 0:
                    budget = float(salary_max)
                elif salary_min and float(salary_min) > 0:
                    budget = float(salary_min)

                currency = item.get("salaryCurrency") or "USD"

                posted_at = None
                date_str = item.get("pubDate")
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
                    "skills": [],
                    "budget": budget,
                    "currency": currency,
                    "project_type": job_type,
                    "posted_at": posted_at,
                    "location": item.get("jobGeo") or "Remote",
                }
                projects.append(project_dict)

            logger.info("JobicyCollector collected %d project(s).", len(projects))

        except HttpClientError as exc:
            logger.error("HTTP error fetching Jobicy feed: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error during Jobicy collection: %s", exc, exc_info=True)

        return projects
