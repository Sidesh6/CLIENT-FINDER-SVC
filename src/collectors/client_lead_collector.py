"""Public client-lead collector for freelance project opportunities.

This collector intentionally searches for buyers seeking help, rather than people
advertising themselves for employment.  It uses Hacker News' public Algolia API,
which requires no account or marketplace scraping.
"""

import html
import logging
import re
from datetime import datetime
from typing import Any

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class ClientLeadCollector(BaseCollector):
    """Discover public freelance client requests across the supported tech niches."""

    ALGOLIA_SEARCH_BY_DATE_URL = "https://hn.algolia.com/api/v1/search_by_date"
    DEFAULT_QUERIES = (
        "seeking freelancer",
        "need freelance developer",
        "need contract web developer",
        "need contract python developer",
        "need freelance AI developer",
        "need freelance designer",
    )
    _CLIENT_INTENT = re.compile(
        r"(?:^|[.!?]\s+)(?:"
        r"we(?:'re|\s+are)?|i(?:'m|\s+am)|our\s+(?:team|company|startup|business)|"
        r"my\s+(?:company|startup|business)"
        r")\s+(?:are\s+)?(?:looking\s+for|seeking|need|hiring|want\s+to\s+hire)\b|"
        r"\b(?:seeking|hiring)\s+(?:a\s+)?(?:freelance|contract)\b",
        re.IGNORECASE,
    )
    _PROJECT_SCOPE = re.compile(
        r"\b(freelance|contract(?:or)?|fixed[ -]price|budget|project\s+(?:budget|brief|scope))\b",
        re.IGNORECASE,
    )
    _TECH_NICHE = re.compile(
        r"\b(web|website|frontend|backend|full[ -]?stack|python|fastapi|django|"
        r"ai|llm|rag|automation|scrap(?:e|ing)|design(?:er)?|ux|ui)\b",
        re.IGNORECASE,
    )
    _FREELANCER_SELF_PROMOTION = re.compile(
        r"\b(seeking work|available for hire|i(?:'m| am) (?:a |an )?(?:freelance|"
        r"developer|designer)|my services|portfolio available)|^\s*location\s*:",
        re.IGNORECASE,
    )

    def __init__(
        self,
        http_client: HttpClient | None = None,
        queries: tuple[str, ...] | None = None,
        max_projects: int = 30,
    ):
        super().__init__("Client Leads")
        self.http_client = http_client or HttpClient(timeout=15.0)
        self.queries = queries or self.DEFAULT_QUERIES
        self.max_projects = max_projects

    @staticmethod
    def _strip_html(value: str) -> str:
        decoded = html.unescape(value or "")
        decoded = re.sub(r"<(p|br\s*/?)>", "\n", decoded, flags=re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", "", decoded)
        return "\n".join(line.strip() for line in clean.splitlines() if line.strip())

    def _is_client_lead(self, text: str) -> bool:
        """Accept a buyer request and reject freelancer self-promotion."""
        return bool(
            text
            and self._CLIENT_INTENT.search(text)
            and self._TECH_NICHE.search(text)
            and self._PROJECT_SCOPE.search(text)
            and not self._FREELANCER_SELF_PROMOTION.search(text)
        )

    def _parse_hit(self, hit: dict[str, Any]) -> dict[str, Any] | None:
        description = self._strip_html(hit.get("comment_text") or hit.get("text") or "")
        if not self._is_client_lead(description):
            return None

        item_id = str(hit.get("objectID") or hit.get("id") or "")
        if not item_id:
            return None

        title = description.splitlines()[0][:120]
        posted_at = hit.get("created_at")
        if posted_at:
            try:
                posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00")).isoformat()
            except ValueError:
                posted_at = None

        return {
            "title": title or "Freelance client lead",
            "description": description,
            "source": self.source_name,
            "source_url": f"https://news.ycombinator.com/item?id={item_id}",
            "external_id": item_id,
            "client_name": hit.get("author") or "Hacker News user",
            "skills": self._matched_niches(description),
            "budget": None,
            "currency": "USD",
            "project_type": "Freelance Client Lead",
            "posted_at": posted_at,
        }

    @staticmethod
    def _matched_niches(text: str) -> list[str]:
        labels = {
            "Web Development": r"\b(web|website|frontend|backend|full[ -]?stack)\b",
            "Python / FastAPI": r"\b(python|fastapi|django)\b",
            "AI / Automation": r"\b(ai|llm|rag|automation|scrap(?:e|ing))\b",
            "Design": r"\b(design(?:er)?|ux|ui)\b",
        }
        return [label for label, pattern in labels.items() if re.search(pattern, text, re.IGNORECASE)]

    def collect(self) -> list[dict[str, Any]]:
        """Fetch recent HN comments and retain only client-side project requests."""
        leads: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for query in self.queries:
            if len(leads) >= self.max_projects:
                break
            try:
                payload = self.http_client.get_json(
                    self.ALGOLIA_SEARCH_BY_DATE_URL,
                    params={"tags": "comment", "query": query, "hitsPerPage": 30},
                )
            except HttpClientError as exc:
                logger.warning("Could not collect client leads for query '%s': %s", query, exc)
                continue

            for hit in payload.get("hits", []) if isinstance(payload, dict) else []:
                lead = self._parse_hit(hit)
                if not lead or lead["external_id"] in seen_ids:
                    continue
                seen_ids.add(lead["external_id"])
                leads.append(lead)
                if len(leads) >= self.max_projects:
                    break

        logger.info("ClientLeadCollector collected %d freelance client lead(s).", len(leads))
        return leads
