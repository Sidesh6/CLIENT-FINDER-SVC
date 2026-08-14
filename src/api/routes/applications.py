"""
REST API endpoints for application lifecycle and outcome tracking.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import ApplicationStatus
from src.proposal.schemas import PitchAngle
from src.tracking.schemas import (
    ApplicationCreate,
    ApplicationFilter,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from src.tracking.tracker import ApplicationTracker

logger = logging.getLogger("ApplicationsAPI")

router = APIRouter(prefix="/api/applications", tags=["Applications & Tracking"])

_TRACKER = ApplicationTracker()


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def track_application(
    payload: ApplicationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationResponse:
    """
    Record a new application submission or link a proposal to a project opportunity.
    """
    try:
        app = _TRACKER.track_application(payload, session=db)
        resp = _TRACKER.get_application(app.id, session=db)
        if not resp:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created application.",
            )
        return resp
    except Exception as exc:
        logger.error("Failed to track application: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    status: Annotated[ApplicationStatus | None, Query(description="Filter by status")] = None,
    pitch_angle: Annotated[PitchAngle | None, Query(description="Filter by pitch angle")] = None,
    min_revenue: Annotated[
        float | None, Query(ge=0.0, description="Filter by minimum revenue")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> list[ApplicationResponse]:
    """
    List tracked applications with optional lifecycle filtering and pagination.
    """
    filters = ApplicationFilter(
        status=status,
        pitch_angle=pitch_angle,
        min_revenue=min_revenue,
        limit=limit,
        offset=offset,
    )
    return _TRACKER.list_applications(filters, session=db)


@router.get("/{app_id}", response_model=ApplicationResponse)
def get_application(
    app_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationResponse:
    """
    Retrieve full details for a specific tracked application.
    """
    app = _TRACKER.get_application(app_id, session=db)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application #{app_id} not found.",
        )
    return app


@router.patch("/{app_id}/status", response_model=ApplicationResponse)
def update_application_status(
    app_id: int,
    status_update: ApplicationStatusUpdate,
    force: Annotated[bool, Query(description="Bypass transition validation checks")] = False,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> ApplicationResponse:
    """
    Progress application status through lifecycle stages (e.g. APPLIED -> CLIENT_REPLIED -> WON).
    """
    try:
        _TRACKER.transition_status(app_id, status_update, force=force, session=db)
        app = _TRACKER.get_application(app_id, session=db)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application #{app_id} not found after update.",
            )
        return app
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Error updating application status: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/{app_id}", status_code=status.HTTP_200_OK)
def delete_application(
    app_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """
    Remove an application record from tracking.
    """
    success = _TRACKER.delete_application(app_id, session=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application #{app_id} not found.",
        )
    return {"message": f"Application #{app_id} deleted successfully.", "deleted": True}
