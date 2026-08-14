"""
Health check route verifying database connectivity and service status.
"""

from fastapi import APIRouter
from sqlalchemy import func, select

from src.api.schemas import HealthCheckResponse
from src.database.connection import SessionLocal
from src.database.models import OpportunityModel, ProjectModel
from src.database.mongo import check_mongo_health, get_mongo_db, is_mongo_configured

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse)
@router.get("/api/health", response_model=HealthCheckResponse)
def get_health() -> HealthCheckResponse:
    """
    Check API and database health status across SQL and MongoDB backends.
    """
    db_connected = False
    total_projects = 0
    total_opps = 0

    if is_mongo_configured():
        mongo_status = check_mongo_health()
        if mongo_status.get("status") == "connected":
            db_connected = True
            try:
                db = get_mongo_db()
                total_projects = int(db["projects"].count_documents({}))
                total_opps = int(db["opportunities"].count_documents({}))
            except Exception:
                pass
    else:
        try:
            with SessionLocal() as session:
                total_projects = session.scalar(select(func.count(ProjectModel.id))) or 0
                total_opps = session.scalar(select(func.count(OpportunityModel.id))) or 0
                db_connected = True
        except Exception:
            db_connected = False

    return HealthCheckResponse(
        status="healthy" if db_connected else "degraded",
        version="1.0.0",
        database_connected=db_connected,
        total_projects=total_projects,
        total_opportunities=total_opps,
    )
