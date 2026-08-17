"""
Fiverr Freelance Client Brief & Buyer Request Collector.
Collects and structures direct buyer briefs, project requests, and client gigs from Fiverr freelance channels.
"""

import html
import logging
import re
from datetime import UTC, datetime
from typing import Any

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class FiverrCollector(BaseCollector):
    """
    Collector for discovering direct buyer briefs, project specifications, and client inquiries
    tailored for Fiverr marketplace opportunities.
    """

    DEFAULT_NICHE_QUERIES = (
        "Python FastAPI backend",
        "AI automation agent LLM",
        "Full stack web development",
        "Custom web scraper API",
        "React UI UX design frontend",
    )

    def __init__(
        self,
        source_name: str = "Fiverr",
        queries: tuple[str, ...] | None = None,
        http_client: HttpClient | None = None,
        max_projects: int = 30,
        min_budget: float | None = 50.0,
    ):
        super().__init__(source_name)
        self.queries = queries or self.DEFAULT_NICHE_QUERIES
        self.http_client = http_client or HttpClient(
            timeout=15.0,
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ClientFinder/2.0"
            },
        )
        self.max_projects = max_projects
        self.min_budget = min_budget

    def _strip_html(self, text: str) -> str:
        """Clean HTML markup."""
        if not text:
            return ""
        decoded = html.unescape(text)
        decoded = re.sub(r"<(p|br\s*/?|li)>", "\n", decoded, flags=re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", "", decoded)
        lines = [line.strip() for line in clean.splitlines() if line.strip()]
        return "\n".join(lines)

    def _parse_brief_metadata(self, text: str) -> dict[str, Any]:
        """
        Parse budget, delivery timeframe, and skills from a Fiverr buyer brief.
        """
        meta: dict[str, Any] = {
            "budget": None,
            "currency": "USD",
            "project_type": "Fiverr Custom Project",
            "skills": [],
        }

        # Budget extraction: e.g. "Budget: $300", "$500 - $1,000", "Price: $250"
        budget_match = re.search(
            r"(?:Budget|Price|Offer)\s*[:\-]?\s*(?:[\$€£])?([0-9,]+(?:\.[0-9]+)?)(?:\s*-\s*(?:[\$€£])?([0-9,]+(?:\.[0-9]+)?))?",
            text,
            re.IGNORECASE,
        )
        if budget_match:
            try:
                b_val = budget_match.group(2) or budget_match.group(1)
                meta["budget"] = float(b_val.replace(",", ""))
            except ValueError:
                pass

        # Detect skills from keyword list
        known_skills = [
            "Python", "FastAPI", "Django", "Flask", "React", "Next.js", "Vue",
            "Node.js", "TypeScript", "JavaScript", "AI", "LLM", "RAG", "OpenAI",
            "LangChain", "Web Scraping", "Automation", "PostgreSQL", "MongoDB",
            "Docker", "TailwindCSS", "Figma", "UI/UX Design",
        ]
        for skill in known_skills:
            if re.search(r"\b" + re.escape(skill) + r"\b", text, re.IGNORECASE):
                if skill not in meta["skills"]:
                    meta["skills"].append(skill)

        return meta

    def parse_incoming_brief(self, brief_data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize an incoming raw Fiverr buyer brief / request payload into standard project dict.
        """
        title = brief_data.get("title") or brief_data.get("subject") or "Fiverr Buyer Project Request"
        description = self._strip_html(brief_data.get("description") or brief_data.get("text") or "")
        budget = brief_data.get("budget")
        currency = brief_data.get("currency") or "USD"
        buyer = brief_data.get("buyer_name") or brief_data.get("client_name") or "Fiverr Client"
        item_id = str(brief_data.get("id") or brief_data.get("brief_id") or "")
        link = brief_data.get("url") or f"https://www.fiverr.com/users/{buyer}"

        meta = self._parse_brief_metadata(f"{title}\n{description}")
        if budget is not None:
            try:
                meta["budget"] = float(budget)
            except (ValueError, TypeError):
                pass
        if brief_data.get("skills"):
            meta["skills"] = list(set(meta["skills"] + list(brief_data["skills"])))

        return {
            "title": title,
            "description": description or f"Fiverr client brief: {title}",
            "source": self.source_name,
            "source_url": link,
            "external_id": item_id or link,
            "client_name": buyer,
            "skills": meta["skills"],
            "budget": meta["budget"],
            "currency": currency,
            "project_type": "Fiverr Buyer Brief",
            "posted_at": datetime.now(UTC).isoformat(),
            "location": brief_data.get("country") or "Remote",
            "is_direct_client": True,
        }

    def collect(self) -> list[dict[str, Any]]:
        """
        Collect buyer opportunities and search freelance client requests for configured niches.
        """
        projects: list[dict[str, Any]] = []

        logger.info("FiverrCollector initialized for direct buyer briefs and client opportunities.")
        # Return structured sample queries/client opportunities if external feed endpoint is integrated
        return projects
