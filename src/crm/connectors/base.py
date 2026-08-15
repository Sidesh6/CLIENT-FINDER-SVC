"""
Abstract Base Class for Enterprise CRM Connectors.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.crm.schemas import CRMConnectionConfig, CRMProvider


class BaseCRMConnector(ABC):
    """
    Abstract interface for all external CRM and project management connectors.
    """

    @property
    @abstractmethod
    def provider(self) -> CRMProvider:
        """The CRM provider identifier."""
        ...

    @abstractmethod
    def test_connection(self, config: CRMConnectionConfig) -> tuple[bool, str]:
        """
        Verify API credentials, base connectivity, and permissions.
        Returns: (is_success, status_message)
        """
        ...

    @abstractmethod
    def push_deal(
        self,
        config: CRMConnectionConfig,
        project_data: dict[str, Any],
        dry_run: bool = False,
    ) -> tuple[str, str]:
        """
        Create or update a deal/record in the external CRM.
        Returns: (crm_record_id, action_taken) e.g. ("deal_12345", "CREATED")
        """
        ...

    @abstractmethod
    def pull_updates(
        self,
        config: CRMConnectionConfig,
    ) -> list[dict[str, Any]]:
        """
        Fetch remote updates and status transitions from the CRM.
        Returns: list of updated record dictionaries.
        """
        ...

    def map_stage(self, local_status: str) -> str:
        """
        Default stage mapper translating internal status to standard CRM pipeline stages.
        """
        stage_map = {
            "DISCOVERED": "Lead / Qualified",
            "SCORED": "Lead / Qualified",
            "PROPOSAL_GENERATED": "Proposal Sent",
            "APPLIED": "Proposal Sent",
            "REPLIED": "In Discussion",
            "INTERVIEWING": "Technical Interview",
            "NEGOTIATING": "Contract Negotiation",
            "ACCEPTED": "Closed Won",
            "REJECTED": "Closed Lost",
            "ARCHIVED": "Archived",
        }
        return stage_map.get(local_status.upper(), "Lead / Qualified")
