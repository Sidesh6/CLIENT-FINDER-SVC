"""
Data models and response structures for skill matching results.
"""

from pydantic import BaseModel, Field


class SkillMatchResult(BaseModel):
    """
    Detailed, explainable result of matching a project opportunity against a user profile.
    """

    match_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Overall skill match score on a 0-100 percentage scale",
    )
    matched_skills: list[str] = Field(
        default_factory=list,
        description="List of project skills directly matched in the user's profile",
    )
    missing_skills: list[str] = Field(
        default_factory=list,
        description="List of required project skills missing from the user's profile",
    )
    implied_skills: list[str] = Field(
        default_factory=list,
        description="Skills satisfied through related framework/language ontology graph",
    )
    coverage_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Ratio of required project skills satisfied by the user (0.0 to 1.0)",
    )
    average_proficiency: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Average skill proficiency level (1-10 scale) on matched technologies",
    )
    category_match: bool = Field(
        default=True,
        description="Whether the project's category aligns with user preferred categories",
    )
    budget_fit: bool = Field(
        default=True,
        description="Whether the project's compensation satisfies user minimum hourly/fixed thresholds",
    )
    is_strong_match: bool = Field(
        default=False,
        description="True if match_score >= 70.0 and project aligns with profile",
    )
    explanation: str = Field(
        description="Comprehensive natural language summary explaining the match evaluation",
    )
