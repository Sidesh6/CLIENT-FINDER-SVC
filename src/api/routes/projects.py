"""
REST endpoints for project discovery, retrieval, status management, and filtering.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.api.schemas import (
    ProjectListResponse,
    ProjectResponse,
    ProjectStatusUpdateRequest,
)
from src.database.connection import SessionLocal
from src.database.models import ProjectModel
from src.scoring.schemas import OpportunityScoreBreakdown

router = APIRouter(prefix="/api/projects", tags=["Projects"])


def model_to_project_response(pm: ProjectModel) -> ProjectResponse:
    """Helper converting ORM ProjectModel to API ProjectResponse schema."""
    meta: dict[str, Any] = pm.raw_data if isinstance(pm.raw_data, dict) else {}
    breakdown = None
    if pm.opportunity:
        opp = pm.opportunity
        breakdown = OpportunityScoreBreakdown(
            overall_score=opp.overall_score,
            skill_match_score=opp.skill_match_score or 0.0,
            budget_score=opp.budget_score or 0.0,
            client_score=opp.client_score or 0.0,
            competition_score=opp.competition_score or 0.0,
            complexity_score=opp.complexity_score or 0.0,
            freshness_score=opp.freshness_score or 0.0,
            win_probability=opp.win_probability or 0.0,
            explanation=opp.explanation or "",
        )
    return ProjectResponse(
        id=pm.id,
        title=pm.title,
        description=pm.description,
        source=pm.source,
        source_url=pm.source_url,
        skills=pm.skills or [],
        category=meta.get("category"),
        budget=pm.budget,
        currency=pm.currency or "USD",
        score=pm.score,
        status=pm.status,
        published_at=pm.posted_at,
        created_at=pm.created_at,
        score_breakdown=breakdown,
        extracted_requirements=meta,
    )


@router.get("", response_model=ProjectListResponse)
def list_projects(
    category: str | None = Query(None, description="Filter by category e.g. AI Development"),
    source: str | None = Query(None, description="Filter by source e.g. Hacker News"),
    min_score: float | None = Query(None, description="Filter by minimum overall score (0-100)"),
    status: str | None = Query(None, description="Filter by workflow status"),
    skill: str | None = Query(None, description="Filter by required skill"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ProjectListResponse:
    """
    List opportunities with advanced multi-facet filtering and pagination.
    """
    with SessionLocal() as session:
        query = select(ProjectModel).options(selectinload(ProjectModel.opportunity))

        if source:
            query = query.where(ProjectModel.source.ilike(f"%{source}%"))
        if status:
            query = query.where(ProjectModel.status.ilike(status))
        if min_score is not None:
            query = query.where(ProjectModel.score >= min_score)

        # Execute total count query
        count_query = select(func.count(ProjectModel.id))
        if source:
            count_query = count_query.where(ProjectModel.source.ilike(f"%{source}%"))
        if status:
            count_query = count_query.where(ProjectModel.status.ilike(status))
        if min_score is not None:
            count_query = count_query.where(ProjectModel.score >= min_score)

        total = session.scalar(count_query) or 0

        # Apply ordering and pagination
        offset = (page - 1) * limit
        query = query.order_by(
            ProjectModel.score.desc().nullslast(), ProjectModel.created_at.desc()
        )
        query = query.offset(offset).limit(limit)

        results = session.scalars(query).all()

        items = []
        for pm in results:
            item = model_to_project_response(pm)
            # Post-filter for JSON category and skills if requested
            if category and (not item.category or category.lower() not in item.category.lower()):
                continue
            if skill and not any(skill.lower() in s.lower() for s in item.skills):
                continue
            items.append(item)

        pages = max(1, (total + limit - 1) // limit)

        return ProjectListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int) -> ProjectResponse:
    """
    Get detailed information for a specific project by ID.
    """
    with SessionLocal() as session:
        query = (
            select(ProjectModel)
            .where(ProjectModel.id == project_id)
            .options(selectinload(ProjectModel.opportunity))
        )
        pm = session.scalars(query).first()
        if not pm:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
        return model_to_project_response(pm)


@router.patch("/{project_id}/status", response_model=ProjectResponse)
def update_project_status(
    project_id: int,
    payload: ProjectStatusUpdateRequest,
) -> ProjectResponse:
    """
    Update workflow status for a project (e.g. APPLIED, REVIEWED, ARCHIVED).
    """
    with SessionLocal() as session:
        query = (
            select(ProjectModel)
            .where(ProjectModel.id == project_id)
            .options(selectinload(ProjectModel.opportunity))
        )
        pm = session.scalars(query).first()
        if not pm:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")

        pm.status = payload.status.upper()
        session.commit()
        session.refresh(pm)
        return model_to_project_response(pm)


@router.delete("/{project_id}")
def delete_project(project_id: int) -> dict[str, Any]:
    """
    Delete a project and its associated evaluations.
    """
    with SessionLocal() as session:
        pm = session.get(ProjectModel, project_id)
        if not pm:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
        session.delete(pm)
        session.commit()
        return {"status": "deleted", "id": project_id}
