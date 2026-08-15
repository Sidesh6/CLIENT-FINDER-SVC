"""
Unit & Integration Tests for Enterprise CRM Two-Way Sync Engine & Deal Pipeline Orchestrator.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.crm.connectors.airtable import AirtableConnector
from src.crm.connectors.hubspot import HubSpotConnector
from src.crm.connectors.linear import LinearConnector
from src.crm.connectors.notion import NotionConnector
from src.crm.schemas import (
    CRMConnectionConfig,
    CRMProvider,
    CRMSyncRequest,
    SyncDirection,
)
from src.crm.syncer import CRMSyncCoordinator


@pytest.fixture
def client():
    return TestClient(app)


class TestCRMConnectors:
    """Tests for individual CRM platform connectors (HubSpot, Notion, Airtable, Linear)."""

    def test_hubspot_connector_test_and_push(self):
        connector = HubSpotConnector()
        assert connector.provider == CRMProvider.HUBSPOT

        config = CRMConnectionConfig(provider=CRMProvider.HUBSPOT, api_key="pat-na1-12345")
        ok, msg = connector.test_connection(config)
        assert ok is True

        project = {
            "id": "proj_hs_01",
            "title": "Enterprise Vector Search Engine",
            "budget_max": 15000.0,
            "status": "INTERVIEWING",
        }
        deal_id, action = connector.push_deal(config, project, dry_run=False)
        assert deal_id.startswith("hs_deal_")
        assert action == "CREATED"

    def test_notion_connector_test_and_push(self):
        connector = NotionConnector()
        assert connector.provider == CRMProvider.NOTION

        config = CRMConnectionConfig(provider=CRMProvider.NOTION, base_or_db_id="db_notion_01")
        ok, msg = connector.test_connection(config)
        assert ok is True

        project = {
            "id": "proj_notion_01",
            "title": "AI SaaS MVP",
            "skills": ["Python", "FastAPI"],
            "budget_min": 7500.0,
            "status": "APPLIED",
        }
        page_id, action = connector.push_deal(config, project, dry_run=False)
        assert page_id.startswith("notion_page_")
        assert action == "CREATED"

    def test_airtable_connector_test_and_push(self):
        connector = AirtableConnector()
        assert connector.provider == CRMProvider.AIRTABLE

        config = CRMConnectionConfig(provider=CRMProvider.AIRTABLE, base_or_db_id="appBase123")
        ok, msg = connector.test_connection(config)
        assert ok is True

        project = {
            "id": "proj_at_01",
            "title": "Autonomous Outreach Agent",
            "score": 96.0,
            "status": "NEGOTIATING",
        }
        rec_id, action = connector.push_deal(config, project, dry_run=False)
        assert rec_id.startswith("rec_")
        assert action == "CREATED"

    def test_linear_connector_test_and_push(self):
        connector = LinearConnector()
        assert connector.provider == CRMProvider.LINEAR

        config = CRMConnectionConfig(provider=CRMProvider.LINEAR, base_or_db_id="team_eng_01")
        ok, msg = connector.test_connection(config)
        assert ok is True

        project = {
            "id": "proj_lin_01",
            "title": "Production CI/CD Automation",
            "skills": ["Docker", "Kubernetes"],
            "status": "ACCEPTED",
        }
        issue_id, action = connector.push_deal(config, project, dry_run=False)
        assert issue_id.startswith("LIN-")
        assert action == "CREATED"


class TestCRMSyncCoordinator:
    """Tests for CRMSyncCoordinator lifecycle, two-way sync execution, and audit logs."""

    def test_list_and_update_configs(self):
        coordinator = CRMSyncCoordinator()
        configs = coordinator.list_configs("test_tenant")
        assert len(configs) >= 4

        # Update config
        new_config = CRMConnectionConfig(
            provider=CRMProvider.HUBSPOT,
            is_enabled=True,
            api_key="pat-custom-token",
            table_or_pipeline_id="custom_pipeline",
        )
        updated = coordinator.update_config("test_tenant", new_config)
        assert updated.api_key == "pat-custom-token"

        fetched = coordinator.get_config("test_tenant", CRMProvider.HUBSPOT)
        assert fetched.table_or_pipeline_id == "custom_pipeline"

    def test_sync_opportunities_dry_run_and_execution(self):
        coordinator = CRMSyncCoordinator()

        # Dry run sync
        req_dry = CRMSyncRequest(
            provider=CRMProvider.NOTION,
            direction=SyncDirection.PUSH_TO_CRM,
            dry_run=True,
        )
        res_dry = coordinator.sync_opportunities("default_tenant", req_dry)
        assert res_dry.is_dry_run is True
        assert res_dry.records_processed >= 1

        # Real sync
        req_live = CRMSyncRequest(
            provider=CRMProvider.AIRTABLE,
            direction=SyncDirection.PUSH_TO_CRM,
            dry_run=False,
        )
        res_live = coordinator.sync_opportunities("default_tenant", req_live)
        assert res_live.is_dry_run is False
        assert res_live.records_created >= 1

        # Check audit logs
        logs = coordinator.get_sync_logs("default_tenant")
        assert len(logs) >= 2
        assert logs[0].provider in [CRMProvider.NOTION, CRMProvider.AIRTABLE]


class TestCRMApiEndpoints:
    """Integration tests for /api/crm/... REST endpoints."""

    def test_list_and_test_crm_connectors_route(self, client: TestClient):
        # 1. List connectors
        res_list = client.get("/api/crm/connectors")
        assert res_list.status_code == 200
        configs = res_list.json()
        assert len(configs) >= 4

        # 2. Test HubSpot connection
        res_test_hs = client.post("/api/crm/connectors/HUBSPOT/test")
        assert res_test_hs.status_code == 200
        assert res_test_hs.json()["success"] is True

        # 3. Test Linear connection
        res_test_lin = client.post("/api/crm/connectors/LINEAR/test")
        assert res_test_lin.status_code == 200
        assert res_test_lin.json()["success"] is True

    def test_crm_sync_and_logs_route(self, client: TestClient):
        # 1. Trigger sync
        sync_payload = {
            "provider": "HUBSPOT",
            "direction": "PUSH_TO_CRM",
            "dry_run": False,
        }
        res_sync = client.post("/api/crm/sync", json=sync_payload)
        assert res_sync.status_code == 200
        data_sync = res_sync.json()
        assert data_sync["provider"] == "HUBSPOT"
        assert data_sync["records_processed"] >= 1

        # 2. Query sync logs
        res_logs = client.get("/api/crm/logs")
        assert res_logs.status_code == 200
        logs = res_logs.json()
        assert len(logs) >= 1
        assert logs[0]["status"] in ["SUCCESS", "PARTIAL_SUCCESS"]
