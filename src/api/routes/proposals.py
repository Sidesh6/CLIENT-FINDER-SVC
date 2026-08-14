"""
Endpoints for generating context-aware proposals and automated pitch letters.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    ProposalApiResponse,
    ProposalAutoPitchRequest,
    ProposalGenerateRequest,
)
from src.database.connection import SessionLocal
from src.database.models import ProjectModel
from src.models.profile import get_default_profile
from src.models.project import Project
from src.proposal.generator import ProposalGenerator
from src.proposal.schemas import ProposalRequest

router = APIRouter(prefix="/api/proposals", tags=["Proposals"])


def _resolve_project(
    project_id: int | None, project_data: dict[str, Any] | None
) -> Project | dict[str, Any]:
    """Helper to fetch or construct project data from request inputs."""
    if project_id is not None:
        with SessionLocal() as session:
            pm = session.get(ProjectModel, project_id)
            if not pm:
                raise HTTPException(status_code=404, detail=f"Project ID {project_id} not found")
            return pm.to_pydantic()
    elif project_data:
        return project_data
    else:
        raise HTTPException(
            status_code=400, detail="Must provide either project_id or project_data"
        )


@router.post("/generate", response_model=ProposalApiResponse)
def generate_proposal(payload: ProposalGenerateRequest) -> ProposalApiResponse:
    """
    Generate tailored proposal using a specified pitch angle and tone.
    """
    project = _resolve_project(payload.project_id, payload.project_data)
    profile = get_default_profile()
    generator = ProposalGenerator(default_profile=profile)

    req = ProposalRequest(
        project=project,
        user_profile=profile,
        pitch_angle=payload.pitch_angle,
        tone=payload.tone,
        include_pricing=payload.include_pricing,
        custom_instructions=payload.custom_instructions,
    )

    result = generator.generate(req)

    return ProposalApiResponse(
        subject_line=result.subject_line,
        hook=result.hook,
        body=result.body,
        relevant_projects=result.relevant_projects,
        call_to_action=result.call_to_action,
        pricing_quote=result.pricing_quote,
        full_proposal_text=result.full_proposal_text,
        pitch_angle=result.pitch_angle.value,
        quality_score=result.quality_score,
    )


@router.post("/auto", response_model=ProposalApiResponse)
def auto_generate_proposal(payload: ProposalAutoPitchRequest) -> ProposalApiResponse:
    """
    Auto-detect the optimal pitch angle based on project signals and synthesize a proposal.
    """
    project = _resolve_project(payload.project_id, payload.project_data)
    profile = get_default_profile()
    generator = ProposalGenerator(default_profile=profile)

    result = generator.generate_for_project(
        project=project,
        profile=profile,
        tone=payload.tone,
        include_pricing=payload.include_pricing,
        custom_instructions=payload.custom_instructions,
    )

    return ProposalApiResponse(
        subject_line=result.subject_line,
        hook=result.hook,
        body=result.body,
        relevant_projects=result.relevant_projects,
        call_to_action=result.call_to_action,
        pricing_quote=result.pricing_quote,
        full_proposal_text=result.full_proposal_text,
        pitch_angle=result.pitch_angle.value,
        quality_score=result.quality_score,
    )
