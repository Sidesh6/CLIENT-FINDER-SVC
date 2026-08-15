"""
FastAPI Main Application for CLIENT FINDER SVC.
Coordinates REST endpoints, CORS policies, WebSockets, static web dashboard serving, and database initialization.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.events import GLOBAL_EVENT_BROADCASTER
from src.api.routes import (
    analytics,
    applications,
    client_intel,
    closing,
    collectors,
    contracts,
    events,
    export,
    health,
    integrations,
    market,
    notifications,
    opportunities,
    outreach,
    profile,
    projects,
    proposals,
    scheduler,
    search,
    vectors,
)
from src.database.connection import init_db
from src.database.mongo import init_mongo_indexes, is_mongo_configured

logger = logging.getLogger("ClientFinderAPI")

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle management."""
    if is_mongo_configured():
        logger.info("Initializing MongoDB collections and indexes...")
        try:
            init_mongo_indexes()
        except Exception as e:
            logger.warning("MongoDB index initialization deferred: %s", e)
    else:
        logger.info("Initializing SQL database schema for Client Finder Service...")
        init_db()

    GLOBAL_EVENT_BROADCASTER.set_event_loop(asyncio.get_running_loop())
    logger.info("Client Finder Service REST API initialized successfully.")
    yield
    logger.info("Client Finder Service REST API shutting down...")


app = FastAPI(
    title="CLIENT FINDER SVC",
    version="1.0.0",
    description="Automated Freelance Opportunity Discovery, Scoring, and Context-Aware AI Proposal Generator",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local dashboards and cross-origin frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health.router)
app.include_router(projects.router)
app.include_router(search.router)
app.include_router(opportunities.router)
app.include_router(proposals.router)
app.include_router(profile.router)
app.include_router(collectors.router)
app.include_router(notifications.router)
app.include_router(scheduler.router)
app.include_router(applications.router)
app.include_router(analytics.router)
app.include_router(events.router)
app.include_router(export.router)
app.include_router(integrations.router)
app.include_router(closing.router)
app.include_router(market.router)
app.include_router(contracts.router)
app.include_router(outreach.router)
app.include_router(client_intel.router)
app.include_router(vectors.router)

# Mount Static Files for Modern Glassmorphic Web Dashboard
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard_root() -> Any:
    """Serve web dashboard single-page interface."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "service": "CLIENT FINDER SVC",
        "status": "operational",
        "docs": "/docs",
        "health": "/api/health",
    }
