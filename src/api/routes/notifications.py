"""
Endpoints for testing notification channels and broadcasting opportunity alerts.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from src.database.connection import SessionLocal
from src.database.models import ProjectModel
from src.notifications.channels.console import ConsoleNotifier
from src.notifications.dispatcher import NotificationDispatcher
from src.scoring.engine import OpportunityScorer

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.post("/test")
def send_test_notification() -> dict[str, Any]:
    """
    Dispatch a test alert across active notification channels.
    """
    console = ConsoleNotifier()
    dispatcher = NotificationDispatcher(channels=[console])

    mock_project = {
        "title": "FastAPI & RAG System Architect",
        "description": "High-priority test opportunity alert",
        "skills": ["FastAPI", "Python", "RAG"],
        "budget": 7500.0,
        "currency": "USD",
        "source": "System Test",
        "source_url": "https://example.com/test",
    }
    scorer = OpportunityScorer()
    breakdown = scorer.score(mock_project)

    results = dispatcher.dispatch(mock_project, breakdown)

    return {
        "status": "sent",
        "channels_contacted": len(results),
        "results": [r.model_dump() for r in results],
    }


@router.post("/broadcast/{project_id}")
def broadcast_opportunity_alert(project_id: int) -> dict[str, Any]:
    """
    Broadcast a high-priority alert for a specific project opportunity.
    """
    with SessionLocal() as session:
        pm = session.get(ProjectModel, project_id)
        if not pm:
            raise HTTPException(status_code=404, detail=f"Project ID {project_id} not found")

        p_obj = pm.to_pydantic()
        scorer = OpportunityScorer()
        breakdown = scorer.score(p_obj)

        console = ConsoleNotifier()
        dispatcher = NotificationDispatcher(channels=[console])
        results = dispatcher.dispatch(p_obj, breakdown)

        return {
            "status": "broadcasted",
            "project_id": project_id,
            "channels_contacted": len(results),
            "results": [r.model_dump() for r in results],
        }
