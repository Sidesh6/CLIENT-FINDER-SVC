"""
Core domain Pydantic model for project opportunities.
"""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class Project(BaseModel):
    """
    Validated project opportunity data model.
    """

    title: str = Field(min_length=1, description="Title of the project")
    description: str = Field(min_length=1, description="Description of the project")
    source: str = Field(min_length=1, description="Source of the project")
    source_url: HttpUrl = Field(description="URL of the project source")

    client_name: str | None = Field(default=None, description="Client or poster identity")
    budget: float | None = Field(default=None, ge=0, description="Parsed budget or compensation")
    currency: str | None = Field(default=None, description="ISO 4217 currency code")
    project_type: str | None = Field(default=None, description="Contract or payment structure")

    skills: list[str] = Field(default_factory=list, description="Extracted required technologies")
    category: str | None = Field(default=None, description="High-level project classification")
    complexity: str | None = Field(default=None, description="Estimated technical complexity")
    deliverables: list[str] = Field(
        default_factory=list, description="Concrete milestones or tasks"
    )
    confidence_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Extraction confidence"
    )

    project_start_date: datetime | None = Field(default=None, description="Posting or start date")
    project_end_date: datetime | None = Field(default=None, description="Deadline or expiry date")

    score: float | None = Field(default=None, ge=0, le=100, description="Opportunity ranking score")
