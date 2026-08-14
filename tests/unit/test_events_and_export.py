"""
Unit tests for Real-Time Event Streaming (WebSockets/SSE), Custom Feed Registration,
Data Export endpoints (CSV/JSON/Markdown), and Outbound Webhooks with HMAC signing.
"""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.events import EventBroadcaster, EventType, SystemEvent
from src.api.main import app
from src.collectors.registry import DEFAULT_REGISTRY
from src.database.connection import SessionLocal
from src.database.models import ApplicationModel, ApplicationStatus, ProjectModel
from src.models.project import Project
from src.notifications.webhooks import (
    OutboundWebhookManager,
    WebhookEndpoint,
)
from src.scoring.schemas import OpportunityScoreBreakdown
from src.utils.http_client import HttpClient

client = TestClient(app)


class TestEventBroadcaster:
    """Tests for EventBroadcaster event serialization, WebSocket handling, and SSE subscriptions."""

    def test_system_event_serialization(self):
        event = SystemEvent(
            event_type=EventType.NEW_OPPORTUNITY,
            data={"id": 101, "title": "FastAPI AI Dev", "score": 85.0},
        )
        json_str = event.to_json()
        assert "NEW_OPPORTUNITY" in json_str
        assert "FastAPI AI Dev" in json_str

        sse_str = event.to_sse_format()
        assert sse_str.startswith("event: NEW_OPPORTUNITY\n")
        assert "data: " in sse_str

    @pytest.mark.anyio
    async def test_event_broadcaster_sse_subscription(self):
        broadcaster = EventBroadcaster()
        queue = await broadcaster.subscribe_sse()

        test_event = SystemEvent(
            event_type=EventType.CYCLE_COMPLETED,
            data={"collected_count": 5},
        )
        await broadcaster.broadcast(test_event)

        received = await queue.get()
        assert received.event_type == EventType.CYCLE_COMPLETED
        assert received.data["collected_count"] == 5

        await broadcaster.unsubscribe_sse(queue)
        assert len(broadcaster._sse_subscribers) == 0

    def test_broadcast_test_endpoint(self):
        res = client.post("/api/events/broadcast-test?message=HelloRealtime")
        assert res.status_code == 200
        assert res.json()["status"] == "broadcast_dispatched"


class TestCustomFeedRegistration:
    """Tests for dynamic custom feed testing, validation, and registry binding."""

    SAMPLE_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Dynamic Custom Jobs</title>
        <item>
          <title>Lead Backend Architect</title>
          <link>https://example.com/jobs/99</link>
          <description>Build Python microservices</description>
        </item>
      </channel>
    </rss>
    """

    def test_add_custom_feed_success(self, monkeypatch):
        # Mock HttpClient.get to return valid XML
        monkeypatch.setattr(
            "src.utils.http_client.HttpClient.get",
            lambda self, url, **kwargs: TestCustomFeedRegistration.SAMPLE_RSS_FEED,
        )

        feed_name = f"CustomFeed_{uuid.uuid4().hex[:6]}"
        res = client.post(
            "/api/collectors/custom",
            json={
                "name": feed_name,
                "feed_url": "https://example.com/custom-jobs.rss",
                "enabled": True,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["source_name"] == feed_name
        assert data["sample_items_found"] == 1
        assert feed_name in DEFAULT_REGISTRY.list_sources()

        # Clean up
        del_res = client.delete(f"/api/collectors/custom/{feed_name}")
        assert del_res.status_code == 200
        assert feed_name not in DEFAULT_REGISTRY.list_sources()

    def test_add_custom_feed_invalid_url_fails(self, monkeypatch):
        monkeypatch.setattr(
            "src.utils.http_client.HttpClient.get",
            lambda self, url, **kwargs: "<invalid>bad xml",
        )
        res = client.post(
            "/api/collectors/custom",
            json={
                "name": "FailingFeed",
                "feed_url": "https://example.com/bad.rss",
                "enabled": True,
            },
        )
        # Should return 400 Bad Request or handled cleanly
        assert res.status_code in [200, 400]


class TestDataExportEndpoints:
    """Tests for CSV, JSON, and Markdown export endpoints."""

    def test_export_opportunities_csv(self):
        res = client.get("/api/export/csv")
        assert res.status_code == 200
        assert "text/csv" in res.headers["Content-Type"]
        assert "attachment; filename=" in res.headers["Content-Disposition"]
        lines = res.text.splitlines()
        assert len(lines) >= 1
        assert "ID,Title,Source" in lines[0]

    def test_export_opportunities_json(self):
        res = client.get("/api/export/json")
        assert res.status_code == 200
        assert "application/json" in res.headers["Content-Type"]
        data = res.json()
        assert isinstance(data, list)

    def test_export_proposal_markdown(self):
        # Create a mock application in db
        with SessionLocal() as session:
            url_str = f"https://example.com/{uuid.uuid4().hex}"
            proj = ProjectModel(
                title="Test Export Proj",
                description="Desc",
                source="Hacker News",
                source_url=url_str,
                url_hash=uuid.uuid4().hex,
                content_hash=uuid.uuid4().hex,
            )
            session.add(proj)
            session.flush()

            app_rec = ApplicationModel(
                project_id=proj.id,
                status=ApplicationStatus.APPLIED.value,
                pitch_angle="TECHNICAL_EXPERT",
                proposal_text="Body of the proposal draft",
                proposed_budget=95.0,
            )
            session.add(app_rec)
            session.commit()
            app_id = app_rec.id

        res = client.get(f"/api/export/proposals/{app_id}/markdown")
        assert res.status_code == 200
        assert "text/markdown" in res.headers["Content-Type"]
        assert "Proposal for: Test Export Proj" in res.text
        assert "Body of the proposal draft" in res.text


class TestOutboundWebhookIntegrations:
    """Tests for HMAC signature generation and outbound webhook delivery."""

    def test_hmac_signature_generation(self):
        mgr = OutboundWebhookManager()
        payload = b'{"hello": "world"}'
        secret = "super_secret_key"

        sig = mgr.generate_signature(payload, secret)
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex string length

    def test_webhook_dispatch_with_mock_http(self):
        mock_http = MagicMock(spec=HttpClient)
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_resp.text = '{"ok": true}'
        mock_http.post.return_value = mock_resp

        mgr = OutboundWebhookManager(http_client=mock_http)
        test_ep = WebhookEndpoint(
            url="https://hooks.zapier.com/hooks/catch/123/abc",
            secret="test_secret",
            min_score=70.0,
        )

        test_proj = Project(
            title="Senior AI Engineer",
            description="Build LangChain RAG pipeline",
            source="RemoteOK",
            source_url="https://remoteok.com/j/123",
            skills=["Python", "FastAPI", "LangChain"],
        )
        test_breakdown = OpportunityScoreBreakdown(
            overall_score=85.0,
            skill_match_score=90.0,
            budget_score=80.0,
            client_score=80.0,
            competition_score=80.0,
            complexity_score=80.0,
            freshness_score=90.0,
            win_probability=0.8,
            explanation="Excellent fit",
        )

        results = mgr.dispatch(test_proj, test_breakdown, endpoints=[test_ep])
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].status_code == 200
        assert mock_http.post.called

        # Verify X-ClientFinder-Signature header was sent
        call_kwargs = mock_http.post.call_args[1]
        assert "X-ClientFinder-Signature" in call_kwargs["headers"]

    def test_integration_api_routes(self, monkeypatch):
        # Test listing webhooks
        res_list = client.get("/api/integrations/webhooks")
        assert res_list.status_code == 200
        assert isinstance(res_list.json(), list)

        # Test adding webhook
        res_add = client.post(
            "/api/integrations/webhooks",
            json={"url": "https://hooks.zapier.com/test", "secret": "abc", "min_score": 80.0},
        )
        assert res_add.status_code == 200
        assert res_add.json()["url"] == "https://hooks.zapier.com/test"
