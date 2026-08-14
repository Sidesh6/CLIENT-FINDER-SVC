"""
Outbound Webhook Dispatcher with HMAC-SHA256 Cryptographic Payload Signing.
Enables real-time lead push to Zapier, Make, custom CRM endpoints, and webhooks.
"""

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.models.project import Project
from src.scoring.schemas import OpportunityScoreBreakdown
from src.utils.http_client import HttpClient

logger = logging.getLogger("OutboundWebhooks")


@dataclass
class WebhookEndpoint:
    """Configured outbound webhook target."""

    url: str
    secret: str | None = None
    min_score: float = 75.0
    enabled: bool = True


@dataclass
class WebhookDeliveryResult:
    """Telemetry report for a webhook dispatch attempt."""

    url: str
    success: bool
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class OutboundWebhookManager:
    """
    Manages and securely dispatches outbound webhook notifications to third-party integrations.
    """

    def __init__(self, http_client: HttpClient | None = None):
        self.http_client = http_client or HttpClient(timeout=10.0, max_retries=2)
        self._endpoints: list[WebhookEndpoint] = []

    def add_endpoint(self, url: str, secret: str | None = None, min_score: float = 75.0) -> None:
        """Register an outbound webhook endpoint."""
        self._endpoints.append(WebhookEndpoint(url=url, secret=secret, min_score=min_score))

    def list_endpoints(self) -> list[dict[str, Any]]:
        """Return list of configured webhook endpoints."""
        return [
            {
                "url": ep.url,
                "has_secret": bool(ep.secret),
                "min_score": ep.min_score,
                "enabled": ep.enabled,
            }
            for ep in self._endpoints
        ]

    def generate_signature(self, payload_bytes: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 hexadecimal digest for webhook verification."""
        return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    def dispatch(
        self,
        project: Project,
        score_breakdown: OpportunityScoreBreakdown,
        endpoints: list[WebhookEndpoint] | None = None,
    ) -> list[WebhookDeliveryResult]:
        """
        Deliver signed JSON payload to all eligible webhook destinations.
        """
        targets = endpoints if endpoints is not None else self._endpoints
        results: list[WebhookDeliveryResult] = []

        payload_dict = {
            "event": "OPPORTUNITY_DISCOVERED",
            "timestamp": datetime.now(UTC).isoformat(),
            "project": {
                "title": project.title,
                "description": project.description,
                "source": project.source,
                "source_url": str(project.source_url),
                "skills": project.skills,
                "budget": project.budget,
                "currency": project.currency,
                "project_type": project.project_type,
                "client_name": project.client_name,
                "posted_at": (
                    project.project_start_date.isoformat() if project.project_start_date else None
                ),
            },
            "score": {
                "overall_score": score_breakdown.overall_score,
                "skill_match_score": score_breakdown.skill_match_score,
                "budget_score": score_breakdown.budget_score,
                "client_score": score_breakdown.client_score,
                "competition_score": score_breakdown.competition_score,
                "complexity_score": score_breakdown.complexity_score,
                "freshness_score": score_breakdown.freshness_score,
                "win_probability": score_breakdown.win_probability,
                "explanation": score_breakdown.explanation,
            },
        }

        payload_bytes = json.dumps(payload_dict, default=str).encode("utf-8")

        for ep in targets:
            if not ep.enabled or score_breakdown.overall_score < ep.min_score:
                continue

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "ClientFinder-Webhook/1.0",
            }

            if ep.secret:
                sig = self.generate_signature(payload_bytes, ep.secret)
                headers["X-ClientFinder-Signature"] = f"sha256={sig}"

            try:
                resp = self.http_client.post(
                    url=ep.url,
                    data=payload_bytes,
                    headers=headers,
                )
                results.append(
                    WebhookDeliveryResult(
                        url=ep.url,
                        success=resp.is_success,
                        status_code=resp.status_code,
                        response_body=resp.text[:200],
                    )
                )
                logger.info(
                    "Outbound webhook delivered to %s (status %d)", ep.url, resp.status_code
                )
            except Exception as exc:
                logger.warning("Outbound webhook delivery failed for %s: %s", ep.url, exc)
                results.append(
                    WebhookDeliveryResult(
                        url=ep.url,
                        success=False,
                        error=str(exc),
                    )
                )

        return results


# Global singleton instance
GLOBAL_WEBHOOK_MANAGER = OutboundWebhookManager()
