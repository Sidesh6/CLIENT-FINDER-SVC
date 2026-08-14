"""
Client Closing, Negotiation, Follow-Up, and Technical Interview Prep REST Endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.routes.profile import get_current_active_profile
from src.database.connection import SessionLocal
from src.database.models import ApplicationModel, ProjectModel
from src.proposal.followup import (
    FollowUpManager,
    FollowUpRequest,
    FollowUpResponse,
    FollowUpStage,
)
from src.proposal.interview_prep import InterviewPrepAdvisor, InterviewPrepSheet
from src.proposal.negotiation import (
    NegotiationAdvisor,
    NegotiationRequest,
    NegotiationResponse,
)

router = APIRouter(prefix="/api/closing", tags=["Closing, Negotiation & Interview Prep"])


class InterviewPrepRequest(BaseModel):
    """Inbound request payload for technical interview prep sheet generation."""

    project_title: str = Field(description="Title of project opportunity")
    project_description: str = Field(default="", description="Scope description")
    skills: list[str] = Field(default_factory=list, description="Target technologies")


@router.post("/negotiate", response_model=NegotiationResponse)
def generate_negotiation_counter_offer(req: NegotiationRequest) -> NegotiationResponse:
    """
    Generate strategic objection responses, value anchoring counter-proposals, and concession guidelines.
    """
    profile = get_current_active_profile()
    advisor = NegotiationAdvisor(default_profile=profile)
    return advisor.advise(req, profile=profile)


@router.post("/followup", response_model=FollowUpResponse)
def generate_followup_message(req: FollowUpRequest) -> FollowUpResponse:
    """
    Synthesize strategic follow-up message based on elapsed days (Day 3 Checkin, Day 7 Value-Add, Day 14 Breakup).
    """
    profile = get_current_active_profile()
    mgr = FollowUpManager(default_profile=profile)
    return mgr.generate(req, profile=profile)


@router.post("/from-application/{application_id}/followup", response_model=FollowUpResponse)
def generate_followup_from_tracked_application(
    application_id: int,
    stage: Annotated[
        FollowUpStage, Query(description="Cadence stage")
    ] = FollowUpStage.DAY_3_CHECKIN,
) -> FollowUpResponse:
    """
    Convenience endpoint generating a follow-up directly from a tracked application ID.
    """
    with SessionLocal() as session:
        app_rec = session.get(ApplicationModel, application_id)
        if not app_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application #{application_id} not found.",
            )

        proj = session.get(ProjectModel, app_rec.project_id)
        if not proj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project #{app_rec.project_id} not found.",
            )

        title = proj.title
        desc = proj.description
        client_name = proj.client_name

    req = FollowUpRequest(
        project_title=title,
        project_description=desc,
        client_name=client_name,
        stage=stage,
    )
    profile = get_current_active_profile()
    mgr = FollowUpManager(default_profile=profile)
    return mgr.generate(req, profile=profile)


@router.post("/interview-prep", response_model=InterviewPrepSheet)
def generate_interview_prep(req: InterviewPrepRequest) -> InterviewPrepSheet:
    """
    Generate tailored technical questions, model answers based on developer stack, and reverse questions for clients.
    """
    profile = get_current_active_profile()
    advisor = InterviewPrepAdvisor(default_profile=profile)
    return advisor.generate(
        project_title=req.project_title,
        project_description=req.project_description,
        skills=req.skills,
        profile=profile,
    )
