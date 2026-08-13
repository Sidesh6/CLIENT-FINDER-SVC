from typing import Any

import httpx

from src.collectors.base_collector import BaseCollector
from src.utils.http_client import HttpClient


class WebProjectCollector(BaseCollector):
    """
    A collector that retrieves project opportunities from web pages.

    This collector uses HTTP requests to fetch web pages and parses the HTML
    content to extract relevant project information.
    """

    def __init__(self, source_name: str, source_url: str):
        super().__init__(source_name)
        self.source_url = source_url
        self.http_client = HttpClient()

    def collect(self) -> list[dict[str, Any]]:
        """
        Collect raw project opportunities from the specified web page.

        Returns:
            A list of dictionaries containing raw project data.
        """
        try:
            html = self.http_client.get(self.source_url)

        except httpx.HTTPStatusError as exc:
            print(f"HTTP error while collecting " f"{self.source_name}: {exc}")

            return []

        except httpx.RequestError as exc:
            print(f"Request failed while collecting " f"{self.source_name}: {exc}")

            return []

        # TODO: Parse HTML with BeautifulSoup to extract projects
        # soup = BeautifulSoup(html, 'html.parser')

        projects = []

        return projects
