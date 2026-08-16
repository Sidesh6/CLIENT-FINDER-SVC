"""
Unit tests for Phase 26: AI Executive Agent & Autonomous Lead Acquisition Orchestrator.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.executive.coordinator import GLOBAL_EXECUTIVE_COORDINATOR
from src.executive.schemas import ActionCategory, AutonomousPolicyConfig, AutonomyMode
from src.executive.telemetry import GLOBAL_EXECUTIVE_TELEMETRY

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_executive_state():
    """Reset executive telemetry and policies between tests."""
    GLOBAL_EXECUTIVE_TELEMETRY._policies.clear()
    GLOBAL_EXECUTIVE_TELEMETRY._logs.clear()
    GLOBAL_EXECUTIVE_TELEMETRY._cycles_count.clear()


def test_executive_policy_defaults_and_updates():
    tracker = GLOBAL_EXECUTIVE_TELEMETRY
    tenant_id = "test_tenant"

    policy = tracker.get_policy(tenant_id)
    assert policy.autonomy_mode == AutonomyMode.SEMI_AUTONOMOUS
    assert policy.min_score_threshold == 75.0

    updated = tracker.update_policy(
        tenant_id,
        AutonomousPolicyConfig(
            autonomy_mode=AutonomyMode.FULLY_AUTONOMOUS,
            min_score_threshold=85.0,
            scam_risk_floor=40.0,
        ),
    )
    assert updated.autonomy_mode == AutonomyMode.FULLY_AUTONOMOUS
    assert updated.min_score_threshold == 85.0


def test_executive_action_recording_and_kpis():
    tracker = GLOBAL_EXECUTIVE_TELEMETRY
    tenant_id = "tenant_kpi"

    tracker.record_action(
        tenant_id=tenant_id,
        category=ActionCategory.HARVEST_AND_SCORE,
        opportunity_title="Swept Feeds",
        description="Scanned 10 items",
        mode=AutonomyMode.SEMI_AUTONOMOUS,
        auto_executed=True,
        time_saved_mins=10.0,
    )

    tracker.record_action(
        tenant_id=tenant_id,
        category=ActionCategory.PROPOSAL_SYNTHESIS,
        opportunity_title="FastAPI API",
        description="Drafted proposal",
        mode=AutonomyMode.SEMI_AUTONOMOUS,
        auto_executed=True,
        time_saved_mins=20.0,
    )

    kpis = tracker.get_kpis(tenant_id)
    assert kpis.total_actions_taken == 2
    assert kpis.total_proposals_auto_drafted == 1
    assert kpis.total_time_saved_hours == 0.5


def test_executive_coordinator_run_cycle():
    coordinator = GLOBAL_EXECUTIVE_COORDINATOR
    tenant_id = "tenant_exec_run"

    res = coordinator.run_autonomous_cycle(tenant_id)
    assert res.cycle_id.startswith("exec_cycle_")
    assert res.opportunities_scanned >= 0
    assert len(res.actions) > 0

    kpis = GLOBAL_EXECUTIVE_TELEMETRY.get_kpis(tenant_id)
    assert kpis.total_cycles_run == 1


def test_executive_disabled_mode():
    coordinator = GLOBAL_EXECUTIVE_COORDINATOR
    tenant_id = "tenant_disabled"

    GLOBAL_EXECUTIVE_TELEMETRY.update_policy(
        tenant_id,
        AutonomousPolicyConfig(autonomy_mode=AutonomyMode.DISABLED),
    )

    res = coordinator.run_autonomous_cycle(tenant_id)
    assert res.opportunities_scanned == 0
    assert len(res.actions) == 0


def test_executive_api_routes():
    # Test GET /api/executive/status
    resp_stat = client.get("/api/executive/status")
    assert resp_stat.status_code == 200
    data_stat = resp_stat.json()
    assert "current_mode" in data_stat
    assert "active_policies" in data_stat

    # Test POST /api/executive/config
    resp_cfg = client.post(
        "/api/executive/config",
        json={
            "autonomy_mode": "FULLY_AUTONOMOUS",
            "min_score_threshold": 80.0,
            "scam_risk_floor": 30.0,
        },
    )
    assert resp_cfg.status_code == 200
    assert resp_cfg.json()["autonomy_mode"] == "FULLY_AUTONOMOUS"

    # Test POST /api/executive/cycle
    resp_cycle = client.post("/api/executive/cycle")
    assert resp_cycle.status_code == 200
    cycle_data = resp_cycle.json()
    assert "cycle_id" in cycle_data

    # Test GET /api/executive/activity-log
    resp_logs = client.get("/api/executive/activity-log")
    assert resp_logs.status_code == 200
    assert isinstance(resp_logs.json(), list)
