"""
Data schemas and recommendation enums for multi-factor opportunity scoring.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ScoringRecommendation(StrEnum):
    """Actionable recommendation tier based on overall score."""

    APPLY_IMMEDIATELY = "APPLY_IMMEDIATELY"  # Score >= 85
    STRONG_PROSPECT = "STRONG_PROSPECT"  # Score 70 - 84
    CONSIDER = "CONSIDER"  # Score 50 - 69
    SKIP = "SKIP"  # Score < 50


class OpportunityScoreBreakdown(BaseModel):
    """
    Complete multi-factor score breakdown for a project opportunity.
    """

    overall_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Composite weighted opportunity score (0-100)",
    )
    skill_match_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Skill capability fit score (Weight: 30%)",
    )
    budget_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Budget attractiveness & rate alignment score (Weight: 20%)",
    )
    client_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Client clarity, credibility, and specs detail score (Weight: 15%)",
    )
    competition_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Friction/barrier-to-entry score (Weight: 10%)",
    )
    complexity_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Complexity fit vs. target seniority level (Weight: 10%)",
    )
    freshness_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Posting freshness and time-decay score (Weight: 10%)",
    )
    win_probability: float = Field(
        ge=0.0,
        le=100.0,
        description="Estimated probability of winning engagement (Weight: 5%)",
    )

    recommendation: ScoringRecommendation = Field(
        default=ScoringRecommendation.CONSIDER,
        description="Actionable decision tier",
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Identified risk signals or scope ambiguities",
    )
    explanation: str = Field(
        description="Comprehensive multi-factor justification summary",
    )
