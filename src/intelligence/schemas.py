"""
Pydantic Schemas and Enums for Client Dossier, Deep Background Intelligence, Scam Risk Sentinel, and Budget Feasibility.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskTier(StrEnum):
    """Categorical fraud and scam risk tier."""

    LOW = "LOW"  # Normal, legitimate project parameters
    MEDIUM = "MEDIUM"  # Elevated caution, non-standard terms or minor ambiguity
    HIGH = "HIGH"  # Multiple red flags, potential scam or severe scope creep
    CRITICAL = "CRITICAL"  # Definite scam indicators (check cashing, off-platform wire trap)


class ScamPatternType(StrEnum):
    """Classified scam and exploitation patterns."""

    OFF_PLATFORM_PAYMENT = "OFF_PLATFORM_PAYMENT"
    UNREALISTIC_BUDGET_RATIO = "UNREALISTIC_BUDGET_RATIO"
    CHECK_CASHING_EQUIPMENT_SCAM = "CHECK_CASHING_EQUIPMENT_SCAM"
    FREE_WORK_TEST_TASK = "FREE_WORK_TEST_TASK"
    DISPOSABLE_CONTACT = "DISPOSABLE_CONTACT"
    CRYPTO_UNVERIFIED_ESCROW = "CRYPTO_UNVERIFIED_ESCROW"
    SUSPICIOUS_DEPOSIT_REQUEST = "SUSPICIOUS_DEPOSIT_REQUEST"


class FeasibilityRating(StrEnum):
    """Feasibility rating comparing requested scope with proposed budget."""

    REALISTIC = "REALISTIC"
    SLIGHTLY_UNDERBUDGETED = "SLIGHTLY_UNDERBUDGETED"
    UNREALISTIC_LOW_BUDGET = "UNREALISTIC_LOW_BUDGET"
    HIGH_RISK_SCOPE_CREEP = "HIGH_RISK_SCOPE_CREEP"


class RedFlagTrigger(BaseModel):
    """A detected fraud or risk indicator with evidence and defensive guidance."""

    pattern_type: ScamPatternType
    severity: str = Field(description="Severity: WARNING, DANGER, CRITICAL")
    evidence_snippet: str = Field(description="Matched text snippet or trigger condition")
    risk_explanation: str = Field(description="Why this pattern presents a commercial risk")
    defensive_action: str = Field(description="Recommended action to protect the developer")


class ClientTrustBreakdown(BaseModel):
    """Granular multi-factor breakdown of client trust and credibility."""

    domain_credibility: float = Field(ge=0.0, le=100.0)
    hiring_history_score: float = Field(ge=0.0, le=100.0)
    budget_transparency: float = Field(ge=0.0, le=100.0)
    requirement_clarity: float = Field(ge=0.0, le=100.0)
    payment_security_score: float = Field(ge=0.0, le=100.0)


class ClientDossierRequest(BaseModel):
    """Inbound request to synthesize a client intelligence dossier."""

    client_name: str = Field(default="Client", description="Client or company name")
    project_title: str = Field(description="Project opportunity title")
    project_description: str = Field(default="", description="Full project text")
    source: str = Field(default="Public Web", description="Discovery source platform")
    source_url: str | None = Field(default=None, description="Original posting URL")
    claimed_budget: float | None = Field(default=None, description="Advertised project budget")


class ClientDossierResult(BaseModel):
    """Comprehensive client background intelligence profile and trust evaluation."""

    client_name: str
    inferred_company_domain: str | None
    detected_tech_stack: list[str] = Field(default_factory=list)
    overall_trust_score: float = Field(ge=0.0, le=100.0)
    trust_grade: str = Field(description="EXCELLENT, VERIFIED, MODERATE, UNVERIFIED, SUSPICIOUS")
    trust_breakdown: ClientTrustBreakdown
    positive_signals: list[str] = Field(default_factory=list)
    caution_warnings: list[str] = Field(default_factory=list)
    recommended_commercial_posture: str = Field(
        description="Tactical positioning and contract strategy"
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScamAuditRequest(BaseModel):
    """Inbound request to scan opportunity text for fraud patterns and red flags."""

    project_title: str = Field(description="Target project title")
    project_description: str = Field(description="Full text description to audit")
    client_name: str | None = Field(default=None, description="Client or poster name")
    claimed_budget: float | None = Field(default=None, description="Advertised budget")


class ScamAuditResult(BaseModel):
    """Risk sentinel assessment output."""

    scam_risk_score: float = Field(
        ge=0.0, le=100.0, description="0 is completely safe, 100 is confirmed fraud"
    )
    risk_tier: RiskTier
    is_safe_to_apply: bool
    detected_red_flags: list[RedFlagTrigger] = Field(default_factory=list)
    legitimacy_confidence: float = Field(ge=0.0, le=1.0)
    defensive_recommendations: list[str] = Field(default_factory=list)


class BudgetFeasibilityRequest(BaseModel):
    """Inbound request to evaluate scope vs. budget feasibility."""

    project_title: str
    project_description: str = Field(default="")
    proposed_budget: float = Field(ge=1.0, description="Offered budget amount")
    currency: str = Field(default="USD")
    target_skills: list[str] = Field(default_factory=list)
    expected_timeline_weeks: int | None = Field(default=None)


class BudgetFeasibilityResult(BaseModel):
    """Feasibility estimation and market price calibration result."""

    feasibility_rating: FeasibilityRating
    feasibility_score: float = Field(ge=0.0, le=100.0)
    estimated_engineering_hours_min: int
    estimated_engineering_hours_max: int
    estimated_market_rate_hourly: float
    estimated_fair_market_budget: float
    budget_variance_percent: float = Field(
        description="Positive if proposed budget is above market, negative if underfunded"
    )
    scope_creep_risk_level: str
    scope_reduction_suggestions: list[str] = Field(default_factory=list)
    recommended_counter_budget: float
