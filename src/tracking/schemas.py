"""
Pydantic schemas for project and job application tracking.
Defines request, response, and filtering models for the application lifecycle.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.database.models import ApplicationStatus
from src.proposal.schemas import PitchAngle


class ApplicationBase(BaseModel):
    """Base fields for application tracking."""

    project_id: int = Field(description="Database ID of the associated project opportunity")
    status: ApplicationStatus = Field(
        default=ApplicationStatus.APPLIED, description="Current lifecycle state"
    )
    proposed_budget: float | None = Field(
        default=None, ge=0.0, description="Proposed pricing / rate"
    )
    currency: str = Field(default="USD", description="Currency symbol / ISO code")
    proposal_text: str | None = Field(
        default=None, description="Proposal or cover letter text sent"
    )
    pitch_angle: PitchAngle | None = Field(default=None, description="Pitch angle used")
    notes: str | None = Field(default=None, description="Private notes or developer logs")


class ApplicationCreate(ApplicationBase):
    """Payload for submitting or tracking a new application."""

    pass


class ApplicationStatusUpdate(BaseModel):
    """Payload for transitioning application state in the lifecycle."""

    status: ApplicationStatus = Field(description="New application status")
    client_feedback: str | None = Field(default=None, description="Feedback received from client")
    final_revenue: float | None = Field(default=None, ge=0.0, description="Realized revenue if won")
    notes: str | None = Field(default=None, description="Updated notes")


class ApplicationUpdate(BaseModel):
    """Payload for updating application details."""

    status: ApplicationStatus | None = Field(default=None, description="New application status")
    proposed_budget: float | None = Field(default=None, ge=0.0, description="Proposed rate/budget")
    final_revenue: float | None = Field(default=None, ge=0.0, description="Realized contract value")
    proposal_text: str | None = Field(default=None, description="Updated proposal text")
    pitch_angle: PitchAngle | None = Field(default=None, description="Pitch angle")
    client_feedback: str | None = Field(default=None, description="Client feedback")
    notes: str | None = Field(default=None, description="Private notes")


class ApplicationResponse(ApplicationBase):
    """Standardized response schema for application records."""

    id: int = Field(description="Application record primary key")
    applied_at: datetime = Field(description="Timestamp when application was submitted")
    response_at: datetime | None = Field(
        default=None, description="Timestamp when client first replied"
    )
    interview_at: datetime | None = Field(default=None, description="Timestamp of interview/call")
    closed_at: datetime | None = Field(
        default=None, description="Timestamp when application reached a terminal state (WON/LOST)"
    )
    final_revenue: float | None = Field(default=None, description="Realized revenue if project won")
    client_feedback: str | None = Field(default=None, description="Client feedback received")
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Record last updated timestamp")

    # Embedded project context
    project_title: str | None = Field(default=None, description="Title of the applied project")
    project_source: str | None = Field(default=None, description="Source platform name")
    project_url: str | None = Field(default=None, description="URL of the original posting")
    overall_score: float | None = Field(default=None, description="Original opportunity score")

    model_config = ConfigDict(from_attributes=True)


class ApplicationFilter(BaseModel):
    """Query filter parameters for listing applications."""

    status: ApplicationStatus | None = Field(default=None, description="Filter by status")
    pitch_angle: PitchAngle | None = Field(default=None, description="Filter by pitch angle")
    min_revenue: float | None = Field(default=None, ge=0.0, description="Filter by minimum revenue")
    limit: int = Field(default=50, ge=1, le=200, description="Pagination limit")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
