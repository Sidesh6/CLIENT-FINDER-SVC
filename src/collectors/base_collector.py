from abc import ABC, abstractmethod
from typing import Any


class BaseCollector(ABC):
    """
    Base interface for all project opportunity collectors.

    Every collector is responsible for retrieving raw project
    information from a particular source.
    """

    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    def collect(self) -> list[dict[str, Any]]:
        """
        Collect raw project opportunities.

        Returns:
            A list of dictionaries containing raw project data.
        """
        pass

    @property
    def name(self) -> str:
        """Alias for source_name."""
        return self.source_name

    def get_source_name(self) -> str:
        """
        Return the name of the source being collected.
        """
        return self.source_name
