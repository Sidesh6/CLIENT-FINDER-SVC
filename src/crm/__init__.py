"""
Enterprise CRM Synchronization & Deal Pipeline Package.
"""

from src.crm.connectors.airtable import AirtableConnector
from src.crm.connectors.base import BaseCRMConnector
from src.crm.connectors.hubspot import HubSpotConnector
from src.crm.connectors.linear import LinearConnector
from src.crm.connectors.notion import NotionConnector
from src.crm.schemas import (
    ConflictResolutionStrategy,
    CRMConnectionConfig,
    CRMProvider,
    CRMSyncLog,
    CRMSyncRecordResult,
    CRMSyncRequest,
    CRMSyncResult,
    SyncDirection,
)
from src.crm.syncer import (
    GLOBAL_CRM_SYNCER,
    CRMSyncCoordinator,
)

__all__ = [
    "CRMProvider",
    "SyncDirection",
    "ConflictResolutionStrategy",
    "CRMConnectionConfig",
    "CRMSyncRequest",
    "CRMSyncRecordResult",
    "CRMSyncResult",
    "CRMSyncLog",
    "BaseCRMConnector",
    "HubSpotConnector",
    "NotionConnector",
    "AirtableConnector",
    "LinearConnector",
    "CRMSyncCoordinator",
    "GLOBAL_CRM_SYNCER",
]
