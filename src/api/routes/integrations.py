"""
Outbound Webhook and Third-Party Integration Endpoints.
Allows configuring endpoints and testing HMAC-SHA256 authenticated webhook dispatches.
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field, HttpUrl

from src.models.project import Project
from src.notifications.webhooks import (
    GLOBAL_WEBHOOK_MANAGER,
    WebhookEndpoint,
)
from src.scoring.schemas import OpportunityScoreBreakdown

router = APIRouter(prefix="/api/integrations", tags=["Integrations & Outbound Webhooks"])


class WebhookCreateRequest(BaseModel):
    """Payload for configuring an outbound webhook."""

    url: str = Field(description="Target webhook URL (e.g. Zapier / Make webhook)")
    secret: str | None = Field(
        default=None, description="Optional secret key for HMAC-SHA256 signature verification"
    )
    min_score: float = Field(
        default=75.0, ge=0, le=100, description="Minimum score to trigger outbound dispatch"
    )


class WebhookTestRequest(BaseModel):
    """Payload for dispatching a test webhook."""

    url: str
    secret: str | None = None


@router.get("/webhooks")
def list_webhook_endpoints() -> list[dict[str, Any]]:
    """
    List all configured outbound webhook destinations.
    """
    return GLOBAL_WEBHOOK_MANAGER.list_endpoints()


@router.post("/webhooks")
def add_webhook_endpoint(req: WebhookCreateRequest) -> dict[str, Any]:
    """
    Add a new outbound webhook target.
    """
    GLOBAL_WEBHOOK_MANAGER.add_endpoint(url=req.url, secret=req.secret, min_score=req.min_score)
    return {
        "url": req.url,
        "has_secret": bool(req.secret),
        "min_score": req.min_score,
        "message": "Webhook endpoint registered successfully.",
    }


@router.post("/webhooks/test", response_model=list[dict[str, Any]])
def test_webhook_dispatch(req: WebhookTestRequest) -> list[dict[str, Any]]:
    """
    Dispatch a test lead payload with HMAC signature to verify target reception.
    """
    sample_proj = Project(
        title="Senior Python & FastAPI AI Architect",
        description="Build high-throughput RAG microservices and autonomous agents.",
        source="ClientFinderTest",
        source_url=HttpUrl("https://example.com/test-opportunity"),
        skills=["Python", "FastAPI", "LangChain", "RAG"],
        budget=8500.0,
    )
    sample_breakdown = OpportunityScoreBreakdown(
        overall_score=88.5,
        skill_match_score=92.0,
        budget_score=85.0,
        client_score=80.0,
        competition_score=75.0,
        complexity_score=90.0,
        freshness_score=95.0,
        win_probability=0.82,
        explanation="Test opportunity generated for webhook payload verification.",
    )

    test_ep = WebhookEndpoint(url=req.url, secret=req.secret, min_score=0.0)
    results = GLOBAL_WEBHOOK_MANAGER.dispatch(
        project=sample_proj,
        score_breakdown=sample_breakdown,
        endpoints=[test_ep],
    )

    return [
        {
            "url": r.url,
            "success": r.success,
            "status_code": r.status_code,
            "response_body": r.response_body,
            "error": r.error,
        }
        for r in results
    ]
