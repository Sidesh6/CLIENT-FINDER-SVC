"""
Production Health Probes, Readiness Checks, and System Telemetry Metrics.
Supports Kubernetes/Docker Liveness (/health/live), Readiness (/health/ready), and Metrics (/health/metrics).
"""

import os
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import func, select

from src.api.schemas import HealthCheckResponse
from src.collectors.registry import DEFAULT_REGISTRY
from src.database.connection import SessionLocal
from src.database.models import OpportunityModel, ProjectModel
from src.database.mongo import check_mongo_health, get_mongo_db, is_mongo_configured
from src.vectors.engine import GLOBAL_VECTOR_STORE

router = APIRouter(tags=["Health & Telemetry"])

# Application start timestamp
APP_START_TIME = time.time()


@router.get("/health", response_model=HealthCheckResponse)
@router.get("/api/health", response_model=HealthCheckResponse)
def get_health() -> HealthCheckResponse:
    """
    General health check verifying database connectivity and record counts.
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


@router.get("/health/live")
def get_liveness_probe() -> dict[str, Any]:
    """
    Kubernetes / Docker Liveness Probe.
    Returns HTTP 200 if the process event loop is active and accepting traffic.
    """
    return {
        "status": "alive",
        "service": "client-finder-svc",
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": round(time.time() - APP_START_TIME, 1),
    }


@router.get("/health/ready")
def get_readiness_probe(response: Response) -> dict[str, Any]:
    """
    Kubernetes / Docker Deep Readiness Probe.
    Evaluates SQL Database, Vector Index Store, MongoDB fallback, and Collector Registry.
    """
    subsystems: dict[str, Any] = {}
    is_ready = True

    # 1. SQL Database Check
    try:
        with SessionLocal() as session:
            session.scalar(select(func.count(ProjectModel.id)))
            subsystems["sql_database"] = {"status": "connected", "type": "relational"}
    except Exception as err:
        subsystems["sql_database"] = {"status": "error", "detail": str(err)}
        is_ready = False

    # 2. Vector Index Engine Check
    try:
        vec_stats = GLOBAL_VECTOR_STORE.get_stats()
        subsystems["vector_engine"] = {
            "status": "ready",
            "indexed_documents": vec_stats.total_indexed_documents,
            "dimension": vec_stats.vector_dimension,
        }
    except Exception as err:
        subsystems["vector_engine"] = {"status": "degraded", "detail": str(err)}

    # 3. Collector Registry Status
    active_collectors = len(DEFAULT_REGISTRY.get_active_collectors())
    subsystems["collector_registry"] = {
        "status": "operational",
        "active_sources": active_collectors,
    }

    # 4. MongoDB Status (if configured)
    if is_mongo_configured():
        m_health = check_mongo_health()
        subsystems["mongo_store"] = m_health

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.now(UTC).isoformat(),
        "subsystems": subsystems,
    }


@router.get("/health/metrics")
def get_telemetry_metrics() -> dict[str, Any]:
    """
    System telemetry and operational metrics.
    """
    uptime = time.time() - APP_START_TIME

    # Ingestion & Database Metrics
    total_projects = 0
    total_opps = 0
    try:
        with SessionLocal() as session:
            total_projects = session.scalar(select(func.count(ProjectModel.id))) or 0
            total_opps = session.scalar(select(func.count(OpportunityModel.id))) or 0
    except Exception:
        pass

    # Vector Engine Metrics
    vec_stats = GLOBAL_VECTOR_STORE.get_stats()

    # Process Memory Telemetry
    mem_info = "N/A"
    try:
        import sys

        if sys.platform != "win32":
            import resource  # type: ignore[import-not-found, import-untyped]

            getrusage = getattr(resource, "getrusage", None)
            rusage_self = getattr(resource, "RUSAGE_SELF", 0)
            if getrusage:
                mem_bytes = getrusage(rusage_self).ru_maxrss * 1024
                mem_info = f"{mem_bytes / (1024 * 1024):.1f} MB"
    except Exception:
        pass

    return {
        "service": "client-finder-svc",
        "environment": os.getenv("APP_ENV", "production"),
        "uptime_seconds": round(uptime, 2),
        "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
        "database": {
            "total_projects": total_projects,
            "total_opportunities": total_opps,
        },
        "vector_store": {
            "indexed_documents": vec_stats.total_indexed_documents,
            "dimension": vec_stats.vector_dimension,
            "memory_kb": round(vec_stats.index_memory_bytes / 1024, 1),
        },
        "collectors": {
            "total_registered": len(DEFAULT_REGISTRY.list_sources()),
            "active_collectors": len(DEFAULT_REGISTRY.get_active_collectors()),
        },
        "system": {
            "max_memory": mem_info,
            "pid": os.getpid(),
        },
    }
