"""
Upwork Freelance RSS Feed Collector.
Collects direct client freelance project and contract opportunities via Upwork search RSS feeds.
"""

import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class UpworkRSSCollector(BaseCollector):
    """
    Collector for discovering freelance and contracting gigs from Upwork RSS feeds.
    Specifically parses client budgets, hourly rate ranges, countries, and skill requirements.
    """

    BASE_RSS_URL = "https://www.upwork.com/ab/feed/jobs/rss"

    def __init__(
        self,
        search_query: str = "Python OR FastAPI OR AI OR Full Stack OR RAG",
        http_client: HttpClient | None = None,
        max_projects: int = 30,
        min_hourly_rate: float | None = 40.0,
        min_fixed_budget: float | None = 300.0,
    ):
        super().__init__("Upwork")
        self.search_query = search_query
        self.http_client = http_client or HttpClient(
            timeout=15.0,
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ClientFinderFreelance/2.0"
            },
        )
        self.max_projects = max_projects
        self.min_hourly_rate = min_hourly_rate
        self.min_fixed_budget = min_fixed_budget

    def _strip_html(self, text: str) -> str:
        """Strip HTML markup from RSS description contents."""
        if not text:
            return ""
        decoded = html.unescape(text)
        decoded = re.sub(r"<(p|br\s*/?|li)>", "\n", decoded, flags=re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", "", decoded)
        lines = [line.strip() for line in clean.split("\n")]
        return "\n".join(line for line in lines if line)

    def _parse_upwork_metadata(self, raw_desc: str) -> dict[str, Any]:
        """
        Extract budget, hourly rate, skills, country, and engagement type from Upwork RSS description.
        """
        meta: dict[str, Any] = {
            "budget": None,
            "currency": "USD",
            "project_type": "Freelance Contract",
            "skills": [],
            "country": None,
            "hourly_range": None,
            "is_hourly": False,
        }

        if not raw_desc:
            return meta

        # Decode HTML entities and strip tags for clean metadata matching
        decoded = html.unescape(raw_desc)
        plain = re.sub(r"<[^>]+>", " ", decoded)

        # 1. Budget extraction: e.g. "Budget: $1,500"
        budget_match = re.search(r"Budget\s*:\s*\$([0-9,]+(?:\.[0-9]+)?)", plain, re.IGNORECASE)
        if budget_match:
            try:
                meta["budget"] = float(budget_match.group(1).replace(",", ""))
                meta["project_type"] = "Fixed Price Project"
            except ValueError:
                pass

        # 2. Hourly range extraction: e.g. "Hourly Range: $50.00-$90.00"
        hourly_match = re.search(
            r"Hourly Range\s*:\s*\$([0-9.]+)\s*-\s*\$([0-9.]+)", plain, re.IGNORECASE
        )
        if hourly_match:
            try:
                h_min = float(hourly_match.group(1))
                h_max = float(hourly_match.group(2))
                meta["hourly_range"] = f"${h_min}-${h_max}/hr"
                meta["budget"] = h_max  # Use ceiling hourly rate for scoring
                meta["project_type"] = "Hourly Freelance Contract"
                meta["is_hourly"] = True
            except ValueError:
                pass

        # 3. Country: e.g. "Country: United States"
        country_match = re.search(r"Country\s*:\s*([A-Za-z\s]+)(?:$|\n|\r|Posted)", plain, re.IGNORECASE)
        if country_match:
            meta["country"] = country_match.group(1).strip()

        # 4. Skills: e.g. "Skills: Python, FastAPI, Docker"
        skills_match = re.search(r"Skills\s*:\s*([^<\n\r]+?)(?:Country|Category|Budget|Hourly|$)", plain, re.IGNORECASE)
        if skills_match:
            raw_skills = skills_match.group(1).split(",")
            meta["skills"] = [s.strip() for s in raw_skills if s.strip()]


        return meta

    def get_feed_url(self) -> str:
        """Construct the Upwork RSS search URL."""
        encoded_query = quote_plus(self.search_query)
        return f"{self.BASE_RSS_URL}?q={encoded_query}&sort=recency"

    def collect(self) -> list[dict[str, Any]]:
        """
        Fetch and parse Upwork RSS project feed entries.
        """
        projects: list[dict[str, Any]] = []
        feed_url = self.get_feed_url()

        try:
            logger.info("Fetching Upwork Freelance RSS feed from %s...", feed_url)
            xml_text = self.http_client.get(feed_url)

            if not xml_text:
                logger.warning("Empty response from Upwork RSS feed.")
                return []

            root = ET.fromstring(xml_text)
            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else root.findall(".//item")

            for item in items:
                if len(projects) >= self.max_projects:
                    break

                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                guid_elem = item.find("guid")
                pub_date_elem = item.find("pubDate")

                raw_title = (
                    title_elem.text.strip()
                    if title_elem is not None and title_elem.text
                    else "Upwork Freelance Opportunity"
                )
                # Clean Upwork title prefix e.g. "Apply to Job Title - Upwork"
                clean_title = re.sub(r"\s*-\s*Upwork.*$", "", raw_title, flags=re.IGNORECASE)

                link = (
                    link_elem.text.strip()
                    if link_elem is not None and link_elem.text
                    else "https://www.upwork.com"
                )
                raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else link

                # Parse Upwork metadata
                meta = self._parse_upwork_metadata(raw_desc)
                clean_desc = self._strip_html(raw_desc)

                # Filter out low-ball budgets if threshold set
                if meta["is_hourly"] and self.min_hourly_rate and meta["budget"]:
                    if meta["budget"] < self.min_hourly_rate:
                        continue
                elif not meta["is_hourly"] and self.min_fixed_budget and meta["budget"]:
                    if meta["budget"] < self.min_fixed_budget:
                        continue

                # Parse publication date
                posted_at = None
                if pub_date_elem is not None and pub_date_elem.text:
                    try:
                        dt = parsedate_to_datetime(pub_date_elem.text.strip())
                        posted_at = dt.astimezone(UTC).isoformat()
                    except Exception:
                        posted_at = None

                project_dict: dict[str, Any] = {
                    "title": clean_title,
                    "description": clean_desc or f"Freelance project: {clean_title}",
                    "source": self.source_name,
                    "source_url": link,
                    "external_id": guid,
                    "client_name": f"Client ({meta['country']})" if meta["country"] else "Direct Client",
                    "skills": meta["skills"],
                    "budget": meta["budget"],
                    "currency": "USD",
                    "project_type": meta["project_type"],
                    "posted_at": posted_at,
                    "location": meta["country"] or "Remote",
                    "is_direct_client": True,
                }
                projects.append(project_dict)

            logger.info("UpworkRSSCollector collected %d freelance project(s).", len(projects))

        except (HttpClientError, ET.ParseError) as exc:
            logger.info("Upwork RSS unavailable (%s). Falling back to web search scraping...", exc)
            try:
                from src.collectors.web_collector import WebProjectCollector

                web_col = WebProjectCollector(
                    source_name=self.source_name,
                    source_url="https://www.upwork.com/freelance-jobs/python/",
                    max_projects=self.max_projects,
                )
                projects = web_col.collect()
            except Exception as web_exc:
                logger.warning("Upwork web scraper fallback error: %s", web_exc)
        except Exception as exc:
            logger.error("Unexpected error during Upwork RSS collection: %s", exc, exc_info=True)

        return projects
