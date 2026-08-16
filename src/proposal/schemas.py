"""
Pydantic schemas and enums for AI proposal and cover letter generation.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from src.models.profile import UserProfile
from src.models.project import Project
from src.scoring.schemas import OpportunityScoreBreakdown


class PitchAngle(StrEnum):
    """Different strategic positioning angles for proposals."""

    TECHNICAL_EXPERT = "TECHNICAL_EXPERT"  # Architecture, deep technical precision, stack mastery
    FAST_DELIVERY = "FAST_DELIVERY"  # Immediate availability, rapid sprint delivery, MVP focus
    VALUE_ROI = "VALUE_ROI"  # Business outcomes, revenue generation, operational efficiency
    PORTFOLIO_PROOF = "PORTFOLIO_PROOF"  # Case studies, proven track record, reference links
    CONSULTATIVE_ADVISOR = "CONSULTATIVE_ADVISOR"  # Discovery questions, architectural options
    DIRECT_FOUNDER_PITCH = "DIRECT_FOUNDER_PITCH"  # High-impact 3-paragraph cold founder pitch
    FIXED_MILESTONE_QUOTE = "FIXED_MILESTONE_QUOTE"  # Phased delivery roadmap with milestone quotes
    FRACTIONAL_ADVISOR = "FRACTIONAL_ADVISOR"  # Fractional lead & weekly sprint retainer



class ProposalTone(StrEnum):
    """Voice and tone styling of the proposal."""

    CONFIDENT = "CONFIDENT"
    PROFESSIONAL = "PROFESSIONAL"
    CONVERSATIONAL = "CONVERSATIONAL"
    DIRECT = "DIRECT"
    CONSULTATIVE = "CONSULTATIVE"


class ProposalRequest(BaseModel):
    """
    Request model containing all context needed to generate a customized proposal.
    """

    project: Project | dict = Field(description="Target opportunity details")
    score_breakdown: OpportunityScoreBreakdown | None = Field(
        default=None, description="Optional opportunity score breakdown"
    )
    user_profile: UserProfile | None = Field(
        default=None, description="Developer profile with skills & rates"
    )
    pitch_angle: PitchAngle = Field(
        default=PitchAngle.TECHNICAL_EXPERT,
        description="Strategic positioning angle",
    )
    tone: ProposalTone = Field(
        default=ProposalTone.CONFIDENT,
        description="Tone of voice",
    )
    include_pricing: bool = Field(
        default=True,
        description="Whether to include rate or milestone pricing quote",
    )
    custom_instructions: str | None = Field(
        default=None,
        description="Optional custom focus directives",
    )


class ProposalResult(BaseModel):
    """
    Generated proposal output with structured sections and full text.
    """

    subject_line: str = Field(description="High-converting email or message subject")
    hook: str = Field(description="Engaging opening hook addressing client's core challenge")
    body: str = Field(description="Main technical approach, proof, and execution plan")
    relevant_projects: list[str] = Field(
        default_factory=list,
        description="Highlight references and past project case studies",
    )
    call_to_action: str = Field(description="Clear next step or meeting link invitation")
    pricing_quote: str | None = Field(
        default=None,
        description="Proposed compensation rate or milestone estimate",
    )
    full_proposal_text: str = Field(
        description="Complete, ready-to-send proposal text formatted in Markdown",
    )
    pitch_angle: PitchAngle = Field(description="Pitch angle utilized")
    quality_score: float = Field(
        default=85.0,
        ge=0.0,
        le=100.0,
        description="Internal proposal quality and completeness rating (0-100)",
    )


# Compatibility alias
GeneratedProposal = ProposalResult
