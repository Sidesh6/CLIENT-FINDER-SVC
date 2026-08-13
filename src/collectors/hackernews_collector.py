import html
import logging
import re
from typing import Any

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class HackerNewsCollector(BaseCollector):
    """
    Collector for discovering freelance and project opportunities from Hacker News.

    Uses public Algolia Hacker News Search API (no API key required).
    Specifically targets:
      - 'Ask HN: Freelancer? Seeking Freelancer?' monthly threads (SEEKING FREELANCER comments)
      - 'Ask HN: Who is hiring?' monthly threads (Freelance / Contract positions)
      - Keyword searches for public contracting and freelance opportunities
    """

    ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
    ALGOLIA_SEARCH_BY_DATE_URL = "https://hn.algolia.com/api/v1/search_by_date"
    ALGOLIA_ITEMS_URL = "https://hn.algolia.com/api/v1/items"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        search_query: str | None = None,
        max_projects: int = 30,
    ):
        super().__init__("Hacker News")
        self.http_client = http_client or HttpClient(timeout=15.0)
        self.search_query = search_query
        self.max_projects = max_projects

    def _strip_html(self, text: str) -> str:
        """Convert HTML comment markup to clean plain text."""
        if not text:
            return ""
        # Unescape HTML entities first (&gt;, &#x27;, &quot;, etc.)
        decoded = html.unescape(text)
        # Convert <p> and <br> to newlines
        decoded = re.sub(r"<(p|br\s*/?)>", "\n", decoded, flags=re.IGNORECASE)
        # Remove remaining HTML tags
        clean = re.sub(r"<[^>]+>", "", decoded)
        # Normalize whitespace while preserving line breaks
        lines = [line.strip() for line in clean.split("\n")]
        return "\n".join(line for line in lines if line)

    def _find_latest_hiring_thread(self, query: str = "Freelancer? Seeking Freelancer?") -> str | None:
        """
        Find the story ID of the latest monthly freelance or hiring thread.
        """
        try:
            params = {
                "tags": "story,ask_hn",
                "query": query,
                "hitsPerPage": 5,
            }
            data = self.http_client.get_json(self.ALGOLIA_SEARCH_BY_DATE_URL, params=params)
            hits = data.get("hits", [])
            if hits:
                story_id = str(hits[0].get("objectID"))
                story_title = hits[0].get("title", "")
                logger.info("Found Hacker News thread '%s' (ID: %s)", story_title, story_id)
                return story_id
        except (HttpClientError, Exception) as exc:
            logger.warning("Failed to locate Hacker News thread for query '%s': %s", query, exc)
        return None

    def _parse_comment(self, comment: dict[str, Any]) -> dict[str, Any] | None:
        """
        Parse an individual HN comment into a standardized raw project dictionary.
        """
        raw_text = comment.get("text") or comment.get("comment_text") or ""
        if not raw_text:
            return None

        clean_text = self._strip_html(raw_text)
        if len(clean_text) < 30:
            return None

        comment_id = comment.get("id") or comment.get("objectID")
        author = comment.get("author", "Hacker News User")
        source_url = f"https://news.ycombinator.com/item?id={comment_id}" if comment_id else "https://news.ycombinator.com"

        lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
        first_line = lines[0] if lines else "HN Project Opportunity"
        title = first_line[:100]

        return {
            "title": title,
            "description": clean_text,
            "source": self.source_name,
            "source_url": source_url,
            "client_name": author,
            "budget": None,
            "currency": None,
            "project_type": "Freelance / Contract",
            "skills": [],
        }

    def collect(self) -> list[dict[str, Any]]:
        """
        Collect project opportunities from Hacker News.

        Returns:
            List of raw project dictionaries.
        """
        projects: list[dict[str, Any]] = []

        try:
            # Mode 1: Custom search query if specified
            if self.search_query:
                params = {
                    "tags": "comment",
                    "query": self.search_query,
                    "hitsPerPage": self.max_projects,
                }
                data = self.http_client.get_json(self.ALGOLIA_SEARCH_URL, params=params)
                hits = data.get("hits", [])
                for hit in hits:
                    parsed = self._parse_comment(hit)
                    if parsed:
                        projects.append(parsed)
                logger.info("Collected %d projects from custom HN query '%s'", len(projects), self.search_query)
                return projects[: self.max_projects]

            # Mode 2: "Ask HN: Freelancer? Seeking Freelancer?" thread
            thread_id = self._find_latest_hiring_thread("Freelancer? Seeking Freelancer?")
            if thread_id:
                # Query comments under this story
                params = {
                    "tags": f"comment,story_{thread_id}",
                    "hitsPerPage": 100,
                }
                data = self.http_client.get_json(self.ALGOLIA_SEARCH_URL, params=params)
                hits = data.get("hits", [])
                for hit in hits:
                    comment_text = hit.get("comment_text") or hit.get("text") or ""
                    # Filter for clients looking to hire freelancers
                    upper_text = comment_text.upper()
                    if "SEEKING FREELANCER" in upper_text or "LOOKING FOR FREELANCER" in upper_text or "HIRING" in upper_text:
                        parsed = self._parse_comment(hit)
                        if parsed:
                            projects.append(parsed)

            # Mode 3: If not enough results from monthly thread, supplement with recent freelance comments
            if len(projects) < self.max_projects:
                needed = self.max_projects - len(projects)
                params = {
                    "tags": "comment",
                    "query": "SEEKING FREELANCER",
                    "hitsPerPage": needed,
                }
                data = self.http_client.get_json(self.ALGOLIA_SEARCH_URL, params=params)
                for hit in data.get("hits", []):
                    parsed = self._parse_comment(hit)
                    if parsed and not any(p["source_url"] == parsed["source_url"] for p in projects):
                        projects.append(parsed)

        except (HttpClientError, Exception) as exc:
            logger.error("Error during Hacker News collection: %s", exc)

        logger.info("Successfully collected %d total opportunities from Hacker News", len(projects))
        return projects[: self.max_projects]
