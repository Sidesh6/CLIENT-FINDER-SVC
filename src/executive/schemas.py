"""
Pydantic Schemas for AI Executive Agent & Autonomous Lead Acquisition Orchestrator.
Covers autonomy policies, execution logs, cycle results, and executive telemetry KPIs.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class AutonomyMode(str, Enum):
    """Execution autonomy level for the Executive Agent."""

    DISABLED = "DISABLED"
    SEMI_AUTONOMOUS = "SEMI_AUTONOMOUS"  # Drafts proposals, contracts & outreach for human review
    FULLY_AUTONOMOUS = "FULLY_AUTONOMOUS"  # Automatically dispatches proposals, outreach & contracts


class ActionCategory(str, Enum):
    """Lifecycle phase of an executive decision action."""

    HARVEST_AND_SCORE = "HARVEST_AND_SCORE"
    DOSSIER_AND_RISK = "DOSSIER_AND_RISK"
    PROPOSAL_SYNTHESIS = "PROPOSAL_SYNTHESIS"
    OUTREACH_SEQUENCE = "OUTREACH_SEQUENCE"
    INBOUND_NEGOTIATION = "INBOUND_NEGOTIATION"
    CONTRACT_GENERATION = "CONTRACT_GENERATION"
    INVOICE_LEDGER = "INVOICE_LEDGER"


class AutonomousPolicyConfig(BaseModel):
    """Policy rules and risk floors governing autonomous agent actions."""

    tenant_id: str = "default_tenant"
    autonomy_mode: AutonomyMode = AutonomyMode.SEMI_AUTONOMOUS
    min_score_threshold: float = Field(default=75.0, ge=0.0, le=100.0, description="Minimum score to trigger automated workflow")
    scam_risk_floor: float = Field(default=35.0, ge=0.0, le=100.0, description="Maximum acceptable scam risk score")
    daily_lead_quota: int = Field(default=10, ge=1, le=100, description="Max outreach actions per 24 hours")
    auto_generate_sow: bool = True
    auto_issue_deposit_invoice: bool = True
    target_hourly_rate: float = 120.0


class ExecutiveActionLog(BaseModel):
    """Audit record of a discrete decision or action taken by the Executive Agent."""

    action_id: str
    tenant_id: str = "default_tenant"
    category: ActionCategory
    project_id: str | None = None
    opportunity_title: str
    action_description: str
    autonomy_level: AutonomyMode
    was_auto_executed: bool
    estimated_time_saved_mins: float = 15.0
    created_at: datetime


class ExecutiveCycleResult(BaseModel):
    """Summary of an autonomous lead acquisition execution cycle."""

    cycle_id: str
    tenant_id: str = "default_tenant"
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    opportunities_scanned: int
    qualified_leads: int
    proposals_drafted: int
    outreach_sequences_initiated: int
    contracts_generated: int
    actions: list[ExecutiveActionLog] = Field(default_factory=list)


class ExecutiveTelemetryKPIs(BaseModel):
    """Aggregated operational metrics for executive AI autonomy."""

    tenant_id: str = "default_tenant"
    current_mode: AutonomyMode
    active_policies: AutonomousPolicyConfig
    total_cycles_run: int
    total_actions_taken: int
    total_proposals_auto_drafted: int
    total_outreach_auto_queued: int
    total_contracts_auto_generated: int
    total_time_saved_hours: float
    pipeline_velocity_multiplier: float = 3.5
    last_cycle_at: datetime | None = None
