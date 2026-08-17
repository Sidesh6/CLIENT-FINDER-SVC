"""
Generic RSS & Atom XML feed collector.
Allows querying any custom freelance, contract board, or job board RSS/Atom endpoint.
"""

import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class RSSFeedCollector(BaseCollector):
    """
    Generic collector for ingesting RSS 2.0 and Atom XML project opportunity feeds.
    """

    def __init__(
        self,
        source_name: str,
        feed_url: str,
        http_client: HttpClient | None = None,
        max_projects: int = 30,
    ):
        super().__init__(source_name)
        self.feed_url = feed_url
        self.http_client = http_client or HttpClient(
            timeout=8.0,
            max_retries=1,
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
        Fetch and parse generic RSS / Atom feed.
        """
        projects: list[dict[str, Any]] = []

        try:
            logger.info("Fetching RSS feed for '%s' from %s...", self.source_name, self.feed_url)
            xml_text = self.http_client.get(self.feed_url)

            if not xml_text:
                logger.warning("Empty response received from feed '%s'.", self.source_name)
                return []

            root = ET.fromstring(xml_text)

            # Check RSS 2.0 (<item>) vs Atom (<entry>)
            items = root.findall(".//item")
            is_atom = False
            if not items:
                items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
                if not items:
                    items = root.findall(".//entry")
                if items:
                    is_atom = True

            for item in items:
                if len(projects) >= self.max_projects:
                    break

                if is_atom:
                    project_dict = self._parse_atom_entry(item)
                else:
                    project_dict = self._parse_rss_item(item)

                if project_dict:
                    projects.append(project_dict)

            logger.info(
                "RSSFeedCollector '%s' collected %d project(s).", self.source_name, len(projects)
            )

        except ET.ParseError as exc:
            logger.error("XML parsing error in feed '%s': %s", self.source_name, exc)
        except HttpClientError as exc:
            logger.error("HTTP error fetching feed '%s': %s", self.source_name, exc)
        except Exception as exc:
            logger.error(
                "Unexpected error collecting from '%s': %s", self.source_name, exc, exc_info=True
            )

        return projects

    def _parse_rss_item(self, item: ET.Element) -> dict[str, Any] | None:
        title_elem = item.find("title")
        link_elem = item.find("link")
        desc_elem = item.find("description")
        guid_elem = item.find("guid")
        pub_date_elem = item.find("pubDate")

        title = (
            title_elem.text.strip() if title_elem is not None and title_elem.text else "Opportunity"
        )
        link = link_elem.text.strip() if link_elem is not None and link_elem.text else self.feed_url
        raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
        guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else link

        posted_at = None
        if pub_date_elem is not None and pub_date_elem.text:
            try:
                dt = parsedate_to_datetime(pub_date_elem.text.strip())
                posted_at = dt.astimezone(UTC).isoformat()
            except Exception:
                posted_at = None

        return {
            "title": title,
            "description": self._strip_html(raw_desc) or f"Opportunity from {self.source_name}",
            "source": self.source_name,
            "source_url": link,
            "external_id": guid,
            "skills": [],
            "budget": None,
            "currency": "USD",
            "posted_at": posted_at,
        }

    def _find_child(self, parent: ET.Element, candidates: list[str]) -> ET.Element | None:
        """Helper to find first matching child element without truthiness bugs."""
        for name in candidates:
            elem = parent.find(name)
            if elem is not None:
                return elem
        return None

    def _parse_atom_entry(self, entry: ET.Element) -> dict[str, Any] | None:
        # Find tags with or without namespace
        title_elem = self._find_child(entry, ["{http://www.w3.org/2005/Atom}title", "title"])
        link_elem = self._find_child(entry, ["{http://www.w3.org/2005/Atom}link", "link"])
        content_elem = self._find_child(
            entry,
            [
                "{http://www.w3.org/2005/Atom}content",
                "{http://www.w3.org/2005/Atom}summary",
                "content",
                "summary",
            ],
        )
        id_elem = self._find_child(entry, ["{http://www.w3.org/2005/Atom}id", "id"])
        published_elem = self._find_child(
            entry,
            [
                "{http://www.w3.org/2005/Atom}published",
                "{http://www.w3.org/2005/Atom}updated",
                "published",
                "updated",
            ],
        )

        title = (
            title_elem.text.strip() if title_elem is not None and title_elem.text else "Opportunity"
        )
        link = self.feed_url
        if link_elem is not None:
            link = link_elem.attrib.get("href") or (
                link_elem.text.strip() if link_elem.text else self.feed_url
            )

        raw_desc = content_elem.text if content_elem is not None and content_elem.text else ""
        guid = id_elem.text.strip() if id_elem is not None and id_elem.text else link

        posted_at = None
        if published_elem is not None and published_elem.text:
            try:
                date_str = published_elem.text.strip().replace("Z", "+00:00")
                posted_at = datetime.fromisoformat(date_str).isoformat()
            except Exception:
                posted_at = None

        return {
            "title": title,
            "description": self._strip_html(raw_desc) or f"Opportunity from {self.source_name}",
            "source": self.source_name,
            "source_url": link,
            "external_id": guid,
            "skills": [],
            "budget": None,
            "currency": "USD",
            "posted_at": posted_at,
        }
