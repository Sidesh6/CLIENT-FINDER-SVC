"""
Data Export Endpoints.
Provides downloadable CSV, JSON, and Markdown files for opportunities, leads, and generated proposals.
"""

import csv
import io
import json
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database.connection import SessionLocal
from src.database.models import ApplicationModel, ProjectModel

router = APIRouter(prefix="/api/export", tags=["Data Export & Reports"])


@router.get("/csv")
def export_opportunities_csv(
    min_score: Annotated[
        float, Query(ge=0, le=100, description="Minimum overall match score")
    ] = 0.0,
    category: Annotated[str | None, Query(description="Filter by category")] = None,
    source: Annotated[str | None, Query(description="Filter by source")] = None,
) -> Response:
    """
    Export opportunity records as an RFC 4180 compliant CSV spreadsheet file.
    """
    with SessionLocal() as session:
        stmt = (
            select(ProjectModel)
            .options(selectinload(ProjectModel.opportunity))
            .order_by(ProjectModel.created_at.desc())
        )
        projects = session.scalars(stmt).all()

    # Filter
    filtered: list[ProjectModel] = []
    for pm in projects:
        score = pm.opportunity.overall_score if pm.opportunity else 0.0
        if score < min_score:
            continue
        if source and pm.source.lower() != source.lower():
            continue
        if category:
            raw_cat = (
                (pm.raw_data or {}).get("category", "") if isinstance(pm.raw_data, dict) else ""
            )
            if category.lower() not in str(raw_cat).lower():
                continue
        filtered.append(pm)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Headers
    writer.writerow(
        [
            "ID",
            "Title",
            "Source",
            "Source URL",
            "Client Name",
            "Skills",
            "Budget",
            "Currency",
            "Project Type",
            "Overall Score",
            "Skill Match Score",
            "Budget Score",
            "Client Score",
            "Win Probability",
            "Status",
            "Posted Date",
            "Discovered Date",
        ]
    )

    for pm in filtered:
        opp = pm.opportunity
        skills_str = ", ".join(pm.skills) if pm.skills else ""
        writer.writerow(
            [
                pm.id,
                pm.title,
                pm.source,
                pm.source_url,
                pm.client_name or "Unstated",
                skills_str,
                pm.budget if pm.budget is not None else "",
                pm.currency or "USD",
                pm.project_type or "",
                f"{opp.overall_score:.1f}" if opp else "0.0",
                f"{opp.skill_match_score:.1f}" if opp and opp.skill_match_score else "0.0",
                f"{opp.budget_score:.1f}" if opp and opp.budget_score else "0.0",
                f"{opp.client_score:.1f}" if opp and opp.client_score else "0.0",
                f"{opp.win_probability * 100:.1f}%" if opp and opp.win_probability else "0%",
                pm.status,
                pm.posted_at.isoformat() if pm.posted_at else "",
                pm.created_at.isoformat() if pm.created_at else "",
            ]
        )

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="opportunities_export.csv"'},
    )


@router.get("/json")
def export_opportunities_json(
    min_score: Annotated[
        float, Query(ge=0, le=100, description="Minimum overall match score")
    ] = 0.0,
    source: Annotated[str | None, Query(description="Filter by source")] = None,
) -> Response:
    """
    Export opportunity records as a formatted JSON document.
    """
    with SessionLocal() as session:
        stmt = (
            select(ProjectModel)
            .options(selectinload(ProjectModel.opportunity))
            .order_by(ProjectModel.created_at.desc())
        )
        projects = session.scalars(stmt).all()

    items: list[dict[str, Any]] = []
    for pm in projects:
        opp = pm.opportunity
        score = opp.overall_score if opp else 0.0
        if score < min_score:
            continue
        if source and pm.source.lower() != source.lower():
            continue

        items.append(
            {
                "id": pm.id,
                "title": pm.title,
                "description": pm.description,
                "source": pm.source,
                "source_url": pm.source_url,
                "client_name": pm.client_name,
                "skills": pm.skills,
                "budget": pm.budget,
                "currency": pm.currency,
                "status": pm.status,
                "score": {
                    "overall_score": opp.overall_score if opp else 0.0,
                    "skill_match_score": opp.skill_match_score if opp else 0.0,
                    "budget_score": opp.budget_score if opp else 0.0,
                    "client_score": opp.client_score if opp else 0.0,
                    "win_probability": opp.win_probability if opp else 0.0,
                    "explanation": opp.explanation if opp else "",
                },
                "posted_at": pm.posted_at.isoformat() if pm.posted_at else None,
                "created_at": pm.created_at.isoformat() if pm.created_at else None,
            }
        )

    json_str = json.dumps(items, indent=2)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="opportunities_export.json"'},
    )


@router.get("/proposals/{application_id}/markdown")
def export_proposal_markdown(application_id: int) -> Response:
    """
    Export a tracked proposal as a standalone clean Markdown file.
    """
    with SessionLocal() as session:
        app_record = session.get(ApplicationModel, application_id)
        if not app_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application #{application_id} not found.",
            )

        project = session.get(ProjectModel, app_record.project_id)
        project_title = project.title if project else f"Project #{app_record.project_id}"

        status_val = (
            app_record.status.value
            if hasattr(app_record.status, "value")
            else str(app_record.status)
        )
        rate_val = app_record.proposed_budget or 95.0

    md_content = f"""# Proposal for: {project_title}

**Pitch Strategy**: `{app_record.pitch_angle or 'TECHNICAL_EXPERT'}`
**Current Status**: `{status_val}`
**Proposed Rate**: ${rate_val:.2f}

---

## Proposal Text
{app_record.proposal_text or 'No proposal draft text available.'}

---
*Generated with CLIENT FINDER PRO Engine*
"""
    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="proposal_app_{application_id}.md"'},
    )
