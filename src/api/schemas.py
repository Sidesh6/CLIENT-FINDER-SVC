"""
Pydantic API models for REST endpoints and dashboard data exchange.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from src.proposal.schemas import PitchAngle, ProposalTone
from src.scoring.schemas import OpportunityScoreBreakdown


class HealthCheckResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    database_connected: bool = True
    total_projects: int = 0
    total_opportunities: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectResponse(BaseModel):
    id: int
    title: str
    description: str
    source: str
    source_url: str
    skills: list[str] = Field(default_factory=list)
    category: str | None = None
    budget: float | None = None
    currency: str = "USD"
    score: float | None = None
    status: str = "NEW"
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    score_breakdown: OpportunityScoreBreakdown | None = None
    extracted_requirements: dict[str, Any] | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    limit: int
    pages: int


class ProjectStatusUpdateRequest(BaseModel):
    status: str = Field(description="Project workflow status e.g. NEW, REVIEWED, APPLIED, ARCHIVED")


class OpportunityStatsResponse(BaseModel):
    total_projects: int
    total_opportunities: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    average_score: float
    average_budget: float
    top_skills: list[dict[str, Any]] = Field(default_factory=list)
    category_distribution: dict[str, int] = Field(default_factory=dict)


class ProposalGenerateRequest(BaseModel):
    project_id: int | None = None
    project_data: dict[str, Any] | None = None
    pitch_angle: PitchAngle = PitchAngle.TECHNICAL_EXPERT
    tone: ProposalTone = ProposalTone.CONFIDENT
    include_pricing: bool = True
    custom_instructions: str | None = None


class ProposalAutoPitchRequest(BaseModel):
    project_id: int | None = None
    project_data: dict[str, Any] | None = None
    tone: ProposalTone = ProposalTone.CONFIDENT
    include_pricing: bool = True
    custom_instructions: str | None = None


class ProposalApiResponse(BaseModel):
    subject_line: str
    hook: str
    body: str
    relevant_projects: list[str]
    call_to_action: str
    pricing_quote: str | None = None
    full_proposal_text: str
    pitch_angle: str
    quality_score: float


class UserProfileUpdateRequest(BaseModel):
    name: str | None = None
    title: str | None = None
    bio: str | None = None
    target_hourly_rate: float | None = None
    minimum_hourly_rate: float | None = None
    preferred_categories: list[str] | None = None
    skills: list[dict[str, Any]] | None = None


class CollectorTriggerResponse(BaseModel):
    collector_name: str
    status: str
    collected_count: int
    enriched_count: int
    scored_count: int
    message: str
