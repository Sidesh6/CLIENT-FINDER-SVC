"""
Freelancer.com Direct Project & Gig RSS Collector.
Collects live freelance client project opportunities with fixed budgets and hourly rates from Freelancer.com.
"""

import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class FreelancerCollector(BaseCollector):
    """
    Collector for discovering freelance contracts and project briefs from Freelancer.com RSS feeds.
    Parses client project briefs, fixed-price budgets, hourly rates, currencies, and skill requirements.
    """

    BASE_RSS_URL = "https://www.freelancer.com/rss.xml"

    def __init__(
        self,
        source_name: str = "Freelancer",
        feed_url: str | None = None,
        search_query: str = "Python OR FastAPI OR AI OR Web Development OR Full Stack",
        http_client: HttpClient | None = None,
        max_projects: int = 30,
        min_budget: float | None = 100.0,
    ):
        super().__init__(source_name)
        self.feed_url = feed_url
        self.search_query = search_query
        self.http_client = http_client or HttpClient(
            timeout=15.0,
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ClientFinder/2.0"
            },
        )
        self.max_projects = max_projects
        self.min_budget = min_budget

    def _strip_html(self, text: str) -> str:
        """Strip HTML tags and clean whitespace."""
        if not text:
            return ""
        decoded = html.unescape(text)
        decoded = re.sub(r"<(p|br\s*/?|li)>", "\n", decoded, flags=re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", "", decoded)
        lines = [line.strip() for line in clean.split("\n")]
        return "\n".join(line for line in lines if line)

    def _parse_budget_and_meta(self, raw_desc: str) -> dict[str, Any]:
        """
        Extract budget, currency, and skills from Freelancer project description.
        e.g., "Budget: $250.00 - $750.00 USD" or "Budget: $500 USD"
        """
        meta: dict[str, Any] = {
            "budget": None,
            "currency": "USD",
            "project_type": "Freelance Fixed Project",
            "skills": [],
        }

        if not raw_desc:
            return meta

        decoded = html.unescape(raw_desc)
        plain = re.sub(r"<[^>]+>", " ", decoded)

        # Budget Range: e.g. "Budget: $250.00 - $750.00 USD" or "Budget: $500"
        budget_range_match = re.search(
            r"Budget\s*:\s*(?:[\$€£])?([0-9,]+(?:\.[0-9]+)?)\s*-\s*(?:[\$€£])?([0-9,]+(?:\.[0-9]+)?)\s*([A-Z]{3})?",
            plain,
            re.IGNORECASE,
        )
        if budget_range_match:
            try:
                b_max = float(budget_range_match.group(2).replace(",", ""))
                meta["budget"] = b_max
                if budget_range_match.group(3):
                    meta["currency"] = budget_range_match.group(3).upper()
            except ValueError:
                pass
        else:
            single_budget_match = re.search(
                r"Budget\s*:\s*(?:[\$€£])?([0-9,]+(?:\.[0-9]+)?)\s*([A-Z]{3})?",
                plain,
                re.IGNORECASE,
            )
            if single_budget_match:
                try:
                    meta["budget"] = float(single_budget_match.group(1).replace(",", ""))
                    if single_budget_match.group(2):
                        meta["currency"] = single_budget_match.group(2).upper()
                except ValueError:
                    pass

        # Hourly check
        if re.search(r"\b(hourly|per hour|/hr)\b", plain, re.IGNORECASE):
            meta["project_type"] = "Hourly Freelance Contract"

        # Skills: e.g. "Categories / Skills: Python, Django, FastAPI"
        skills_match = re.search(
            r"(?:Categories|Skills|Tags)\s*:\s*([^<\n\r]+?)(?:Budget|Status|$)", plain, re.IGNORECASE
        )
        if skills_match:
            raw_skills = skills_match.group(1).split(",")
            meta["skills"] = [s.strip() for s in raw_skills if s.strip()]

        return meta

    def get_feed_url(self) -> str:
        """Construct the RSS feed URL."""
        if self.feed_url:
            return self.feed_url
        if self.search_query:
            encoded = quote_plus(self.search_query)
            return f"{self.BASE_RSS_URL}?q={encoded}"
        return self.BASE_RSS_URL

    def collect(self) -> list[dict[str, Any]]:
        """
        Fetch and parse Freelancer RSS entries.
        """
        projects: list[dict[str, Any]] = []
        feed_url = self.get_feed_url()

        try:
            logger.info("Fetching Freelancer project RSS feed from %s...", feed_url)
            xml_text = self.http_client.get(feed_url)

            if not xml_text:
                logger.warning("Empty response from Freelancer RSS feed.")
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
                    else "Freelancer Client Project"
                )
                link = (
                    link_elem.text.strip()
                    if link_elem is not None and link_elem.text
                    else "https://www.freelancer.com"
                )
                raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else link

                meta = self._parse_budget_and_meta(raw_desc)
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
                    "client_name": "Freelancer Direct Client",
                    "skills": meta["skills"],
                    "budget": meta["budget"],
                    "currency": meta["currency"],
                    "project_type": meta["project_type"],
                    "posted_at": posted_at,
                    "location": "Remote",
                    "is_direct_client": True,
                }
                projects.append(project_dict)

            logger.info("FreelancerCollector collected %d freelance project(s).", len(projects))

        except ET.ParseError as exc:
            logger.error("XML parse error on Freelancer RSS: %s", exc)
        except HttpClientError as exc:
            logger.error("HTTP error fetching Freelancer RSS: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error during Freelancer RSS collection: %s", exc, exc_info=True)

        return projects
