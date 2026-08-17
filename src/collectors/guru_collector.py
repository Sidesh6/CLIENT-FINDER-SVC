"""
Guru.com Direct Freelance Gig & Client Project RSS Collector.
Collects live freelance project opportunities from Guru.com RSS feeds.
"""

import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Any

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class GuruCollector(BaseCollector):
    """
    Collector for discovering direct client freelance jobs and contracts from Guru.com RSS feeds.
    Parses client project descriptions, budgets, hourly rates, and skills.
    """

    DEFAULT_RSS_URL = "https://www.guru.com/rss/jobs/c/programming-development/"

    def __init__(
        self,
        source_name: str = "Guru",
        feed_url: str | None = None,
        http_client: HttpClient | None = None,
        max_projects: int = 30,
        min_budget: float | None = 150.0,
    ):
        super().__init__(source_name)
        self.feed_url = feed_url or self.DEFAULT_RSS_URL
        self.http_client = http_client or HttpClient(
            timeout=15.0,
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ClientFinder/2.0"
            },
        )
        self.max_projects = max_projects
        self.min_budget = min_budget

    def _strip_html(self, text: str) -> str:
        """Clean HTML markup from descriptions."""
        if not text:
            return ""
        decoded = html.unescape(text)
        decoded = re.sub(r"<(p|br\s*/?|li)>", "\n", decoded, flags=re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", "", decoded)
        lines = [line.strip() for line in clean.split("\n")]
        return "\n".join(line for line in lines if line)

    def _parse_guru_meta(self, raw_desc: str) -> dict[str, Any]:
        """
        Extract budget, rate, and skills from Guru description text.
        e.g., "Budget: Fixed Price ($1,000 - $2,500)" or "Hourly: $35 - $60 / hr"
        """
        meta: dict[str, Any] = {
            "budget": None,
            "currency": "USD",
            "project_type": "Freelance Milestone Contract",
            "skills": [],
            "location": "Remote",
        }

        if not raw_desc:
            return meta

        decoded = html.unescape(raw_desc)
        plain = re.sub(r"<[^>]+>", " ", decoded)

        # 1. Fixed Price / Budget: e.g. "$1,000 - $2,500" or "Fixed Price ($2,000 - $4,000)"
        budget_match = re.search(
            r"[\$€£]\s*([0-9,]+(?:\.[0-9]+)?)(?:\s*-\s*[\$€£]?\s*([0-9,]+(?:\.[0-9]+)?))?",
            plain,
            re.IGNORECASE,
        )
        if budget_match:
            try:
                high_val = budget_match.group(2) or budget_match.group(1)
                meta["budget"] = float(high_val.replace(",", ""))
                meta["project_type"] = "Fixed Price Project"
            except ValueError:
                pass

        # 2. Hourly: e.g. "Hourly Rate: $40-$80/hr"
        hourly_match = re.search(
            r"(?:Hourly(?:\s*Rate)?)\s*[:\-]?\s*(?:[\$€£])?([0-9,.]+)(?:\s*-\s*(?:[\$€£])?([0-9,.]+))?\s*(?:\/|\s*per\s*)?hr",
            plain,
            re.IGNORECASE,
        )
        if hourly_match:
            try:
                h_val = hourly_match.group(2) or hourly_match.group(1)
                meta["budget"] = float(h_val.replace(",", ""))
                meta["project_type"] = "Hourly Freelance Contract"
            except ValueError:
                pass

        # 3. Skills: e.g. "Skills: Python, FastAPI, React"
        skills_match = re.search(
            r"(?:Skills|Required\s*Skills|Categories)\s*:\s*([^<\n\r]+?)(?:Location|Budget|Posted|$)",
            plain,
            re.IGNORECASE,
        )
        if skills_match:
            raw_skills = skills_match.group(1).split(",")
            meta["skills"] = [s.strip() for s in raw_skills if s.strip()]

        # 4. Location: e.g. "Location: United States"
        loc_match = re.search(r"Location\s*:\s*([A-Za-z\s]+)(?:$|\n|\r|Skills|Budget)", plain, re.IGNORECASE)
        if loc_match:
            meta["location"] = loc_match.group(1).strip()

        return meta

    def collect(self) -> list[dict[str, Any]]:
        """
        Fetch and parse Guru RSS project opportunities.
        """
        projects: list[dict[str, Any]] = []

        try:
            logger.info("Fetching Guru project RSS feed from %s...", self.feed_url)
            xml_text = self.http_client.get(self.feed_url)

            if not xml_text:
                logger.warning("Empty response from Guru RSS feed.")
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
                    else "Guru Freelance Project"
                )
                link = (
                    link_elem.text.strip()
                    if link_elem is not None and link_elem.text
                    else "https://www.guru.com"
                )
                raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else link

                meta = self._parse_guru_meta(raw_desc)
                clean_desc = self._strip_html(raw_desc)

                if self.min_budget and meta["budget"] and meta["budget"] < self.min_budget:
                    continue

                posted_at = None
                if pub_date_elem is not None and pub_date_elem.text:
                    try:
                        dt = parsedate_to_datetime(pub_date_elem.text.strip())
                        posted_at = dt.astimezone(UTC).isoformat()
                    except Exception:
                        posted_at = None

                project_dict: dict[str, Any] = {
                    "title": raw_title,
                    "description": clean_desc or f"Freelance project: {raw_title}",
                    "source": self.source_name,
                    "source_url": link,
                    "external_id": guid,
                    "client_name": f"Guru Client ({meta['location']})" if meta["location"] != "Remote" else "Guru Client",
                    "skills": meta["skills"],
                    "budget": meta["budget"],
                    "currency": meta["currency"],
                    "project_type": meta["project_type"],
                    "posted_at": posted_at,
                    "location": meta["location"],
                    "is_direct_client": True,
                }
                projects.append(project_dict)

            logger.info("GuruCollector collected %d freelance project(s).", len(projects))

        except (HttpClientError, ET.ParseError) as exc:
            logger.info("Guru RSS unavailable (%s). Falling back to direct web scraping...", exc)
            try:
                from src.collectors.web_collector import WebProjectCollector

                web_col = WebProjectCollector(
                    source_name=self.source_name,
                    source_url="https://www.guru.com/d/jobs/c/programming-development/",
                    max_projects=self.max_projects,
                )
                projects = web_col.collect()
            except Exception as web_exc:
                logger.warning("Guru web scraper fallback error: %s", web_exc)
        except Exception as exc:
            logger.error("Unexpected error during Guru collection: %s", exc, exc_info=True)

        return projects
