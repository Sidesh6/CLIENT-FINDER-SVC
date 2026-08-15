"""
Pydantic Schemas and Enums for Autonomous Outreach Sequences, Inbound Intent Analysis, and A/B Testing.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from src.proposal.schemas import PitchAngle


class SequenceStatus(StrEnum):
    """Lifecycle state of an automated multi-touch outreach sequence."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SequenceStepType(StrEnum):
    """Standardized touchpoints in a multi-touch outreach cadence."""

    INITIAL_PROPOSAL = "INITIAL_PROPOSAL"
    DAY_3_DIAGNOSIS = "DAY_3_DIAGNOSIS"
    DAY_7_CASE_STUDY = "DAY_7_CASE_STUDY"
    DAY_14_BREAKUP = "DAY_14_BREAKUP"
    DAY_30_REVIVE = "DAY_30_REVIVE"


class StepStatus(StrEnum):
    """Execution status for an individual cadence touchpoint."""

    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"


class IntentType(StrEnum):
    """Classified commercial intent of an inbound client response."""

    POSITIVE_INTEREST = "POSITIVE_INTEREST"
    SCHEDULE_CALL = "SCHEDULE_CALL"
    RATE_PUSHBACK = "RATE_PUSHBACK"
    SCOPE_QUESTION = "SCOPE_QUESTION"
    REJECTION = "REJECTION"
    OUT_OF_OFFICE = "OUT_OF_OFFICE"
    UNCERTAIN = "UNCERTAIN"


class OutreachStep(BaseModel):
    """A discrete step in an outreach sequence with delay trigger and synthesized copy."""

    step_index: int
    step_type: SequenceStepType
    delay_days: int
    subject: str
    message_content: str
    status: StepStatus = StepStatus.PENDING
    scheduled_for: datetime | None = None
    executed_at: datetime | None = None


class OutreachSequenceCreate(BaseModel):
    """Inbound request to initiate an outreach sequence for an application."""

    application_id: int = Field(description="Target application identifier")
    project_title: str = Field(description="Target project opportunity title")
    project_description: str = Field(default="", description="Original project requirements")
    client_name: str | None = Field(default="Client", description="Client or company name")
    pitch_angle: PitchAngle = Field(
        default=PitchAngle.TECHNICAL_EXPERT, description="Selected proposal pitch angle"
    )
    target_skills: list[str] = Field(
        default_factory=list, description="Target technologies or skills"
    )
    proposed_budget: float | None = Field(
        default=None, description="Proposed milestone or project fee"
    )
    auto_start: bool = Field(
        default=True, description="Immediately mark sequence as ACTIVE and execute step 1"
    )


class OutreachSequenceResult(BaseModel):
    """Complete multi-touch outreach sequence record."""

    sequence_id: str
    application_id: int
    project_title: str
    client_name: str
    pitch_angle: PitchAngle
    status: SequenceStatus = SequenceStatus.ACTIVE
    current_step_index: int = 1
    total_steps: int = 5
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    steps: list[OutreachStep] = Field(default_factory=list)


class InboundReplyRequest(BaseModel):
    """Inbound client message for parsing and intent classification."""

    message_text: str = Field(description="Raw message text received from client")
    application_id: int | None = Field(
        default=None, description="Associated application identifier if known"
    )
    project_title: str | None = Field(
        default=None, description="Project title for context enrichment"
    )
    client_name: str | None = Field(default=None, description="Client name if available")


class InboundReplyAnalysisResult(BaseModel):
    """Classified client intent, sentiment metrics, recommended funnel transition, and draft reply."""

    classified_intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    sentiment_score: float = Field(
        ge=-1.0, le=1.0, description="-1.0 negative to +1.0 enthusiastic"
    )
    detected_objections: list[str] = Field(default_factory=list)
    key_extracted_points: list[str] = Field(default_factory=list)
    recommended_funnel_status: str
    recommended_next_action: str
    suggested_response_draft: str
    application_status_updated: bool = False


class ABTestPitchMetric(BaseModel):
    """Statistical conversion performance metrics for a specific pitch angle."""

    pitch_angle: PitchAngle
    impressions_sent: int = 0
    replies_received: int = 0
    wins_recorded: int = 0
    reply_rate_percent: float = 0.0
    win_rate_percent: float = 0.0
    conversion_score: float = 0.0
    confidence_interval_low: float = 0.0
    confidence_interval_high: float = 0.0
    is_statistically_significant: bool = False


class ABExperimentSummary(BaseModel):
    """Aggregated multi-armed bandit A/B pitch testing performance report."""

    total_outreach_events: int
    total_replies: int
    overall_reply_rate: float
    best_performing_pitch: PitchAngle
    best_performing_win_pitch: PitchAngle
    pitch_metrics: list[ABTestPitchMetric]
    category_recommendations: dict[str, PitchAngle] = Field(default_factory=dict)
