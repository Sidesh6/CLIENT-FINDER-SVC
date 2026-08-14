"""
Pydantic schemas and enums for AI requirement extraction.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ProjectCategory(StrEnum):
    """Normalized high-level category of software/AI projects."""

    AI_DEVELOPMENT = "AI Development"
    WEB_DEVELOPMENT = "Web Development"
    MOBILE_DEVELOPMENT = "Mobile Development"
    DATA_ENGINEERING = "Data Engineering"
    AUTOMATION_SCRAPING = "Automation & Scraping"
    DEVOPS_CLOUD = "DevOps & Cloud"
    SYSTEMS_BACKEND = "Systems & Backend"
    OTHER = "Other"


class ProjectComplexity(StrEnum):
    """Estimated technical complexity level."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    EXPERT = "Expert"


class PaymentType(StrEnum):
    """Project payment and engagement structure."""

    FIXED_PRICE = "Fixed Price"
    HOURLY = "Hourly"
    CONTRACT = "Contract"
    FULL_TIME = "Full Time"
    UNKNOWN = "Unknown"


class ExperienceLevel(StrEnum):
    """Target developer experience level."""

    JUNIOR = "Junior"
    MID = "Mid-Level"
    SENIOR = "Senior"
    LEAD = "Lead/Architect"
    NOT_SPECIFIED = "Not Specified"


class ExtractedRequirements(BaseModel):
    """
    Structured project requirements extracted by LLM or heuristic analyzer.
    """

    category: ProjectCategory = Field(
        default=ProjectCategory.OTHER,
        description="High-level classification of the project.",
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description="List of essential technologies, libraries, and languages explicitly required.",
    )
    optional_skills: list[str] = Field(
        default_factory=list,
        description="List of nice-to-have or optional technologies.",
    )
    estimated_complexity: ProjectComplexity = Field(
        default=ProjectComplexity.MEDIUM,
        description="Estimated difficulty and technical depth required.",
    )
    project_type: PaymentType = Field(
        default=PaymentType.UNKNOWN,
        description="Engagement payment structure (e.g. Hourly, Fixed Price).",
    )
    experience_level: ExperienceLevel = Field(
        default=ExperienceLevel.NOT_SPECIFIED,
        description="Requested engineer seniority.",
    )
    budget_min: float | None = Field(
        default=None,
        ge=0,
        description="Minimum parsed budget amount (numerical value only).",
    )
    budget_max: float | None = Field(
        default=None,
        ge=0,
        description="Maximum parsed budget amount (numerical value only).",
    )
    currency: str | None = Field(
        default=None,
        description="3-letter currency code (e.g. USD, EUR, INR, GBP).",
    )
    deliverables: list[str] = Field(
        default_factory=list,
        description="List of concrete tasks or deliverables expected by the client.",
    )
    technical_requirements: list[str] = Field(
        default_factory=list,
        description="Key technical architecture or constraint details.",
    )
    risk_signals: list[str] = Field(
        default_factory=list,
        description="Potential red flags (e.g. vague specifications, unrealistic budget).",
    )
    confidence_score: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence level in the parsed data (0.0 to 1.0).",
    )
    summary: str | None = Field(
        default=None,
        description="A concise 1-2 sentence executive summary of the opportunity.",
    )
