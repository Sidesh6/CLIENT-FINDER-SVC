"""
Pydantic Schemas for Enterprise CRM Two-Way Sync Engine & Deal Pipeline Orchestrator.
Supports HubSpot, Notion, Airtable, Linear, and Custom Webhook Integrations.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CRMProvider(str, Enum):
    """Supported external CRM and project tracking platforms."""

    HUBSPOT = "HUBSPOT"
    NOTION = "NOTION"
    AIRTABLE = "AIRTABLE"
    LINEAR = "LINEAR"
    CUSTOM_WEBHOOK = "CUSTOM_WEBHOOK"


class SyncDirection(str, Enum):
    """Direction of data synchronization."""

    PUSH_TO_CRM = "PUSH_TO_CRM"
    PULL_FROM_CRM = "PULL_FROM_CRM"
    BI_DIRECTIONAL = "BI_DIRECTIONAL"


class ConflictResolutionStrategy(str, Enum):
    """Strategy to resolve concurrent field edits between Client Finder and external CRM."""

    CLIENT_FINDER_WINS = "CLIENT_FINDER_WINS"
    CRM_WINS = "CRM_WINS"
    LATEST_TIMESTAMP_WINS = "LATEST_TIMESTAMP_WINS"


class CRMConnectionConfig(BaseModel):
    """Connection credentials and configuration for a CRM provider."""

    provider: CRMProvider
    is_enabled: bool = True
    api_key: str = Field(
        default="", description="Secret API key, Bearer token, or OAuth access token"
    )
    base_or_db_id: str = Field(
        default="",
        description="Database ID (Notion), Base ID (Airtable), Team ID (Linear), or Portal ID (HubSpot)",
    )
    table_or_pipeline_id: str = Field(
        default="",
        description="Table name / ID (Airtable), Pipeline ID (HubSpot), or Project ID (Linear)",
    )
    webhook_secret: str = Field(
        default="", description="Optional HMAC secret for verifying inbound webhook payloads"
    )
    default_direction: SyncDirection = SyncDirection.BI_DIRECTIONAL
    conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LATEST_TIMESTAMP_WINS
    custom_field_mappings: dict[str, str] = Field(
        default_factory=dict, description="Custom field mappings {client_finder_field: crm_field}"
    )
    last_synced_at: datetime | None = None


class CRMSyncRequest(BaseModel):
    """Request payload to trigger on-demand CRM synchronization."""

    provider: CRMProvider = Field(default=CRMProvider.HUBSPOT)
    project_ids: list[str] | None = Field(
        default=None, description="Optional list of specific project IDs to sync"
    )
    direction: SyncDirection = Field(default=SyncDirection.PUSH_TO_CRM)
    dry_run: bool = Field(
        default=False,
        description="If True, simulates synchronization without writing to external CRM",
    )


class CRMSyncRecordResult(BaseModel):
    """Per-record sync status detail."""

    project_id: str
    project_title: str
    crm_record_id: str
    action: str  # CREATED, UPDATED, SKIPPED, CONFLICT_RESOLVED, ERROR
    provider: CRMProvider
    details: str
    synced_at: datetime


class CRMSyncResult(BaseModel):
    """Summary of completed CRM synchronization run."""

    provider: CRMProvider
    direction: SyncDirection
    records_processed: int
    records_created: int
    records_updated: int
    records_skipped: int
    records_failed: int
    is_dry_run: bool
    duration_ms: float
    record_results: list[CRMSyncRecordResult] = Field(default_factory=list)
    timestamp: datetime


class CRMSyncLog(BaseModel):
    """Audit log entry for CRM sync events."""

    id: str
    tenant_id: str = "default_tenant"
    provider: CRMProvider
    status: str  # SUCCESS, PARTIAL_SUCCESS, FAILED
    records_synced: int
    message: str
    timestamp: datetime
    error_details: str | None = None
