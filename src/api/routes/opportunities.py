"""
Endpoints for high-priority opportunity analytics, ranking, and batch scoring.
"""

from collections import Counter
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.api.routes.projects import model_to_project_response
from src.api.schemas import OpportunityStatsResponse, ProjectResponse
from src.database.connection import SessionLocal
from src.database.models import OpportunityModel, ProjectModel
from src.models.profile import get_default_profile
from src.scoring.engine import OpportunityScorer

router = APIRouter(prefix="/api/opportunities", tags=["Opportunities"])


@router.get("/top", response_model=list[ProjectResponse])
def get_top_opportunities(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of top opportunities"),
    min_score: float = Query(50.0, ge=0.0, le=100.0, description="Minimum overall score"),
) -> list[ProjectResponse]:
    """
    Retrieve top ranked opportunities above the specified score threshold.
    """
    with SessionLocal() as session:
        query = (
            select(ProjectModel)
            .options(selectinload(ProjectModel.opportunity))
            .where(ProjectModel.score >= min_score)
            .order_by(ProjectModel.score.desc())
            .limit(limit)
        )
        results = session.scalars(query).all()
        return [model_to_project_response(pm) for pm in results]


@router.get("/stats", response_model=OpportunityStatsResponse)
def get_opportunity_statistics() -> OpportunityStatsResponse:
    """
    Aggregate key performance indicators, score distributions, top skills, and categories.
    """
    with SessionLocal() as session:
        total_projects = session.scalar(select(func.count(ProjectModel.id))) or 0
        total_opps = session.scalar(select(func.count(OpportunityModel.id))) or 0

        # Score distributions
        high_priority = (
            session.scalar(select(func.count(ProjectModel.id)).where(ProjectModel.score >= 75.0))
            or 0
        )
        medium_priority = (
            session.scalar(
                select(func.count(ProjectModel.id)).where(
                    ProjectModel.score >= 50.0, ProjectModel.score < 75.0
                )
            )
            or 0
        )
        low_priority = (
            session.scalar(select(func.count(ProjectModel.id)).where(ProjectModel.score < 50.0))
            or 0
        )

        avg_score = session.scalar(select(func.avg(ProjectModel.score))) or 0.0
        avg_budget = (
            session.scalar(
                select(func.avg(ProjectModel.budget)).where(ProjectModel.budget.isnot(None))
            )
            or 0.0
        )

        # Calculate top skills and categories across active projects
        all_projects = session.scalars(select(ProjectModel)).all()
        skills_counter: Counter[str] = Counter()
        categories_counter: Counter[str] = Counter()

        for pm in all_projects:
            if pm.skills:
                for s in pm.skills:
                    skills_counter[s] += 1
            meta = pm.raw_data if isinstance(pm.raw_data, dict) else {}
            cat = meta.get("category") or "Software Engineering"
            categories_counter[cat] += 1

        top_skills_list = [
            {"skill": skill, "count": count} for skill, count in skills_counter.most_common(10)
        ]

        return OpportunityStatsResponse(
            total_projects=total_projects,
            total_opportunities=total_opps,
            high_priority_count=high_priority,
            medium_priority_count=medium_priority,
            low_priority_count=low_priority,
            average_score=round(float(avg_score), 1),
            average_budget=round(float(avg_budget), 2),
            top_skills=top_skills_list,
            category_distribution=dict(categories_counter.most_common(8)),
        )


@router.post("/score-all")
def score_all_opportunities() -> dict[str, Any]:
    """
    Execute scoring engine across all stored projects against the active developer profile.
    """
    profile = get_default_profile()
    scorer = OpportunityScorer(default_profile=profile)
    scored_count = 0

    with SessionLocal() as session:
        projects = session.scalars(select(ProjectModel)).all()
        for pm in projects:
            p_obj = pm.to_pydantic()
            scorer.score_and_persist(p_obj, profile=profile, session=session)
            scored_count += 1

    return {
        "status": "completed",
        "scored_count": scored_count,
        "profile_name": profile.name,
    }
