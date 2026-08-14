"""
Search endpoints providing keyword and multi-field query matching across projects.
"""

from fastapi import APIRouter, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from src.api.routes.projects import model_to_project_response
from src.api.schemas import ProjectListResponse
from src.database.connection import SessionLocal
from src.database.models import ProjectModel

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("", response_model=ProjectListResponse)
def search_projects(
    q: str = Query("", description="Keyword search query"),
    category: str | None = Query(None, description="Filter by category"),
    source: str | None = Query(None, description="Filter by source"),
    min_score: float | None = Query(None, description="Minimum score"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> ProjectListResponse:
    """
    Search projects by keywords across title, description, skills, and source.
    """
    with SessionLocal() as session:
        query = select(ProjectModel).options(selectinload(ProjectModel.opportunity))

        if q.strip():
            term = f"%{q.strip()}%"
            query = query.where(
                or_(
                    ProjectModel.title.ilike(term),
                    ProjectModel.description.ilike(term),
                    ProjectModel.source.ilike(term),
                )
            )

        if source:
            query = query.where(ProjectModel.source.ilike(f"%{source}%"))
        if min_score is not None:
            query = query.where(ProjectModel.score >= min_score)

        query = query.order_by(
            ProjectModel.score.desc().nullslast(), ProjectModel.created_at.desc()
        )

        all_matches = session.scalars(query).all()

        # Apply in-memory filtering for JSON attributes and skills if query matches
        filtered_items = []
        for pm in all_matches:
            item = model_to_project_response(pm)
            if category and (not item.category or category.lower() not in item.category.lower()):
                continue
            if q.strip() and not (
                q.lower() in item.title.lower()
                or q.lower() in item.description.lower()
                or any(q.lower() in s.lower() for s in item.skills)
            ):
                continue
            filtered_items.append(item)

        total = len(filtered_items)
        offset = (page - 1) * limit
        paginated_items = filtered_items[offset : offset + limit]
        pages = max(1, (total + limit - 1) // limit)

        return ProjectListResponse(
            items=paginated_items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )
