"""
Universal Web Project & Gigs Collector.
Extracts live client opportunities, contracts, and project listings from arbitrary web pages and directories.
"""

import html
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class WebProjectCollector(BaseCollector):
    """
    Intelligent web scraper collector that parses live opportunities from web HTML directories and portals.
    """

    KNOWN_SKILLS = [
        "Python", "FastAPI", "Django", "Flask", "React", "Next.js", "Vue",
        "Node.js", "TypeScript", "JavaScript", "AI", "LLM", "RAG", "OpenAI",
        "LangChain", "Web Scraping", "Automation", "PostgreSQL", "MongoDB",
        "Docker", "TailwindCSS", "Figma", "UI/UX Design", "Machine Learning",
    ]

    def __init__(
        self,
        source_name: str,
        source_url: str,
        http_client: HttpClient | None = None,
        max_projects: int = 20,
    ):
        super().__init__(source_name)
        self.source_url = source_url
        self.http_client = http_client or HttpClient(
            timeout=8.0,
            max_retries=1,
            default_headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36 ClientFinder/2.0"
                )
            },
        )
        self.max_projects = max_projects

    def _strip_html(self, text: str) -> str:
        """Strip HTML tags and collapse whitespace."""
        if not text:
            return ""
        decoded = html.unescape(text)
        clean = re.sub(r"\s+", " ", decoded).strip()
        return clean

    def _extract_budget(self, text: str) -> tuple[float | None, str]:
        """Extract currency and budget amount from text snippet."""
        currency = "USD"
        if "₹" in text or "INR" in text:
            currency = "INR"
        elif "€" in text or "EUR" in text:
            currency = "EUR"
        elif "£" in text or "GBP" in text:
            currency = "GBP"

        # Match e.g. "$1,500 - $3,000" or "$2500" or "₹50,000"
        match = re.search(r"[\$€£₹]\s*([0-9,]+(?:\.[0-9]+)?)(?:\s*-\s*[\$€£₹]?\s*([0-9,]+(?:\.[0-9]+)?))?", text)
        if match:
            try:
                val = match.group(2) or match.group(1)
                return float(val.replace(",", "")), currency
            except ValueError:
                pass
        return None, currency

    def _extract_skills(self, text: str) -> list[str]:
        """Extract matching tech skills from snippet."""
        skills: list[str] = []
        for skill in self.KNOWN_SKILLS:
            if re.search(r"\b" + re.escape(skill) + r"\b", text, re.IGNORECASE):
                skills.append(skill)
        return skills

    def collect(self) -> list[dict[str, Any]]:
        """
        Fetch web page and parse project/job opportunities.
        """
        projects: list[dict[str, Any]] = []

        try:
            logger.info("Scraping web source '%s' from %s...", self.source_name, self.source_url)
            html_text = self.http_client.get(self.source_url)

            if not html_text:
                logger.warning("Empty response received from '%s'.", self.source_name)
                return []

            soup = BeautifulSoup(html_text, "html.parser")

            # Remove noise scripts/styles
            for s in soup(["script", "style", "nav", "footer"]):
                s.decompose()

            # Identify repeating card/listing elements
            card_selectors = [
                "article",
                "div[class*='job']",
                "div[class*='project']",
                "div[class*='listing']",
                "div[class*='card']",
                "li[class*='job']",
                "li[class*='listing']",
                "tr[class*='job']",
            ]

            cards = []
            for sel in card_selectors:
                elements = soup.select(sel)
                if len(elements) >= 2:
                    cards = elements
                    break

            # Fallback: Find relevant anchor links matching job/project patterns
            if not cards:
                cards = soup.find_all(
                    "a",
                    href=re.compile(
                        r"/(?:job|jobs|project|projects|gig|gigs|post|contract|opportunity)/",
                        re.IGNORECASE,
                    ),
                )

            seen_titles: set[str] = set()

            for card in cards:
                if len(projects) >= self.max_projects:
                    break

                # Extract title
                title_elem = card.find(["h1", "h2", "h3", "h4", "h5", "strong", "a"])
                raw_title = title_elem.get_text(strip=True) if title_elem else card.get_text(strip=True)
                raw_title = self._strip_html(raw_title)

                if not raw_title or len(raw_title) < 5 or len(raw_title) > 200:
                    continue

                if raw_title in seen_titles:
                    continue
                seen_titles.add(raw_title)

                # Extract link
                link_elem = card if card.name == "a" else card.find("a")
                rel_url = link_elem.get("href", "") if link_elem else ""
                full_url = urljoin(self.source_url, rel_url) if rel_url else self.source_url

                # Extract description
                card_text = self._strip_html(card.get_text(" ", strip=True))
                desc = card_text if len(card_text) > len(raw_title) else f"Client opportunity on {self.source_name}: {raw_title}"

                budget, currency = self._extract_budget(card_text)
                skills = self._extract_skills(card_text)

                project_dict: dict[str, Any] = {
                    "title": raw_title,
                    "description": desc[:1000],
                    "source": self.source_name,
                    "source_url": full_url,
                    "external_id": full_url,
                    "client_name": f"{self.source_name} Client",
                    "skills": skills,
                    "budget": budget,
                    "currency": currency,
                    "project_type": "Freelance / Contract Opportunity",
                    "posted_at": datetime.now(UTC).isoformat(),
                    "location": "Remote",
                    "is_direct_client": True,
                }
                projects.append(project_dict)

            logger.info("WebProjectCollector '%s' collected %d project(s).", self.source_name, len(projects))

        except HttpClientError as exc:
            logger.warning("HTTP error scraping '%s': %s", self.source_name, exc)
        except Exception as exc:
            logger.warning("Unexpected error scraping '%s': %s", self.source_name, exc)

        return projects
