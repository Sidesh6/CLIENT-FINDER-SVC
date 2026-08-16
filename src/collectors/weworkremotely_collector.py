"""
WeWorkRemotely RSS job board collector.
Collects remote software engineering, AI, and developer opportunities via WeWorkRemotely RSS feeds.
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


class WeWorkRemotelyCollector(BaseCollector):
    """
    Collector for discovering remote developer and AI contracting opportunities from WeWorkRemotely RSS.
    """

    DEFAULT_FEED_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        feed_url: str | None = None,
        max_projects: int = 30,
        source_name: str = "WeWorkRemotely",
    ):
        super().__init__(source_name)
        self.http_client = http_client or HttpClient(
            timeout=15.0,
            default_headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ClientFinderBot/1.0"
            },
        )
        self.feed_url = feed_url or self.DEFAULT_FEED_URL
        self.max_projects = max_projects

    def _strip_html(self, text: str) -> str:
        """Strip HTML markup from RSS description contents."""
        if not text:
            return ""
        decoded = html.unescape(text)
        decoded = re.sub(r"<(p|br\s*/?|li)>", "\n", decoded, flags=re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", "", decoded)
        lines = [line.strip() for line in clean.split("\n")]
        return "\n".join(line for line in lines if line)

    def collect(self) -> list[dict[str, Any]]:
        """
        Fetch and parse RSS XML entries from WeWorkRemotely.
        """
        projects: list[dict[str, Any]] = []

        try:
            logger.info("Fetching WeWorkRemotely RSS feed from %s...", self.feed_url)
            xml_text = self.http_client.get(self.feed_url)

            if not xml_text:
                logger.warning("Empty response from WeWorkRemotely RSS feed.")
                return []

            root = ET.fromstring(xml_text)
            channel = root.find("channel")
            if channel is None:
                items = root.findall(".//item")
            else:
                items = channel.findall("item")

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
                    else "Remote Job"
                )
                link = (
                    link_elem.text.strip()
                    if link_elem is not None and link_elem.text
                    else "https://weworkremotely.com"
                )
                raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else link

                # Extract company name if title is in format "Company: Job Title"
                client_name = None
                if ":" in raw_title:
                    parts = raw_title.split(":", 1)
                    client_name = parts[0].strip()
                    title = parts[1].strip()
                else:
                    title = raw_title

                cleaned_desc = self._strip_html(raw_desc)

                # Parse pubDate (RFC 2822 / RFC 822 format)
                posted_at = None
                if pub_date_elem is not None and pub_date_elem.text:
                    try:
                        dt = parsedate_to_datetime(pub_date_elem.text.strip())
                        posted_at = dt.astimezone(UTC).isoformat()
                    except Exception:
                        posted_at = None

                project_dict: dict[str, Any] = {
                    "title": f"{client_name}: {title}" if client_name else title,
                    "description": cleaned_desc or f"Opportunity for {title}",
                    "source": self.source_name,
                    "source_url": link,
                    "external_id": guid,
                    "client_name": client_name,
                    "skills": [],
                    "budget": None,
                    "currency": "USD",
                    "project_type": "Remote",
                    "posted_at": posted_at,
                }
                projects.append(project_dict)

            logger.info(
                "WeWorkRemotelyCollector successfully collected %d project(s).", len(projects)
            )

        except ET.ParseError as exc:
            logger.error("XML parse error on WeWorkRemotely RSS feed: %s", exc)
        except HttpClientError as exc:
            logger.error("HTTP error fetching WeWorkRemotely RSS feed: %s", exc)
        except Exception as exc:
            logger.error(
                "Unexpected error during WeWorkRemotely collection: %s", exc, exc_info=True
            )

        return projects
