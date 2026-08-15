"""
Unit & Integration Tests for Phase 19: AI Client Dossier, Scam Risk Sentinel, and Scope Feasibility.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database.connection import SessionLocal, init_db
from src.database.models import ProjectModel, compute_content_hash, compute_url_hash
from src.intelligence.dossier import ClientDossierEngine
from src.intelligence.feasibility import BudgetFeasibilityAnalyzer
from src.intelligence.scam_sentinel import ScamSentinel
from src.intelligence.schemas import (
    BudgetFeasibilityRequest,
    ClientDossierRequest,
    FeasibilityRating,
    RiskTier,
    ScamAuditRequest,
    ScamPatternType,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Initialize fresh test database."""
    init_db()


class TestClientDossierEngine:
    """Test suite for client background intelligence profile synthesis and trust evaluation."""

    def test_generate_client_dossier_high_trust(self):
        engine = ClientDossierEngine()
        req = ClientDossierRequest(
            client_name="Stripe Infrastructure",
            project_title="FastAPI Microservice with Async Celery Workers",
            project_description="We are a Series B funded engineering team looking for a senior Python engineer to build a high-throughput API with PostgreSQL, Redis, Docker, and FastAPI for our active users.",
            source="RemoteOK",
            source_url="https://stripe.com/careers/lead-engineer",
            claimed_budget=6500.0,
        )
        res = engine.generate_dossier(req)

        assert res.client_name == "Stripe Infrastructure"
        assert res.inferred_company_domain == "stripe.com"
        assert "FastAPI" in res.detected_tech_stack
        assert "PostgreSQL" in res.detected_tech_stack
        assert res.overall_trust_score >= 80.0
        assert res.trust_grade in ("EXCELLENT", "VERIFIED")
        assert len(res.positive_signals) >= 3
        assert len(res.caution_warnings) == 0

    def test_generate_client_dossier_unverified_sparse(self):
        engine = ClientDossierEngine()
        req = ClientDossierRequest(
            client_name="Anonymous",
            project_title="Need coder",
            project_description="quick script fix",
            source="Custom Form",
            source_url=None,
            claimed_budget=None,
        )
        res = engine.generate_dossier(req)

        assert res.inferred_company_domain is None
        assert res.overall_trust_score <= 65.0
        assert res.trust_grade in ("MODERATE", "UNVERIFIED", "SUSPICIOUS")
        assert len(res.caution_warnings) >= 2


class TestScamSentinel:
    """Test suite for fraud pattern detection, payment redirection, and free work traps."""

    def test_detect_off_platform_telegram_payment_scam(self):
        sentinel = ScamSentinel()
        req = ScamAuditRequest(
            project_title="Urgent Web Developer Needed",
            project_description="We need urgent help. Do not apply here, telegram me @crypto_admin for wire transfer payment directly.",
            claimed_budget=5000.0,
        )
        res = sentinel.audit_opportunity(req)

        assert res.is_safe_to_apply is False
        assert res.risk_tier in (RiskTier.HIGH, RiskTier.CRITICAL)
        assert any(
            f.pattern_type == ScamPatternType.OFF_PLATFORM_PAYMENT for f in res.detected_red_flags
        )
        assert any(
            "telegram" in r.lower() or "not apply" in r.lower()
            for r in res.defensive_recommendations
        )

    def test_detect_fake_check_cashing_equipment_scam(self):
        sentinel = ScamSentinel()
        req = ScamAuditRequest(
            project_title="Data Entry / Backend Developer",
            project_description="Congratulations! We will send you a check to buy equipment and a MacBook from our approved vendor before starting.",
            claimed_budget=4000.0,
        )
        res = sentinel.audit_opportunity(req)

        assert res.is_safe_to_apply is False
        assert res.risk_tier == RiskTier.CRITICAL
        assert any(
            f.pattern_type == ScamPatternType.CHECK_CASHING_EQUIPMENT_SCAM
            for f in res.detected_red_flags
        )

    def test_detect_unpaid_test_assignment_trap(self):
        sentinel = ScamSentinel()
        req = ScamAuditRequest(
            project_title="Fullstack Developer",
            project_description="Candidates must prove yourself by building this full app as a test for free before we interview.",
            claimed_budget=1000.0,
        )
        res = sentinel.audit_opportunity(req)

        assert res.is_safe_to_apply is False
        assert any(
            f.pattern_type == ScamPatternType.FREE_WORK_TEST_TASK for f in res.detected_red_flags
        )

    def test_detect_crypto_registration_fee_scam(self):
        sentinel = ScamSentinel()
        req = ScamAuditRequest(
            project_title="Crypto Contract Audit",
            project_description="Deposit into our smart contract first to activate your vendor account and start.",
            claimed_budget=3000.0,
        )
        res = sentinel.audit_opportunity(req)

        assert res.is_safe_to_apply is False
        assert res.risk_tier == RiskTier.CRITICAL
        assert any(
            f.pattern_type == ScamPatternType.CRYPTO_UNVERIFIED_ESCROW
            for f in res.detected_red_flags
        )

    def test_audit_clean_legitimate_project(self):
        sentinel = ScamSentinel()
        req = ScamAuditRequest(
            project_title="Senior Python / FastAPI Developer",
            project_description="Looking for an experienced engineer to build microservices with PostgreSQL and Docker. Standard milestone contract through platform.",
            claimed_budget=5000.0,
        )
        res = sentinel.audit_opportunity(req)

        assert res.is_safe_to_apply is True
        assert res.risk_tier == RiskTier.LOW
        assert len(res.detected_red_flags) == 0
        assert res.scam_risk_score == 0.0


class TestBudgetFeasibilityAnalyzer:
    """Test suite for scope vs. budget calibration and scope-creep detection."""

    def test_calculate_realistic_budget_feasibility(self):
        analyzer = BudgetFeasibilityAnalyzer()
        req = BudgetFeasibilityRequest(
            project_title="Python API with Database Migrations",
            project_description="Build small REST backend with PostgreSQL and FastAPI.",
            proposed_budget=5000.0,
            target_skills=["Python", "FastAPI", "PostgreSQL"],
        )
        res = analyzer.evaluate_feasibility(req)

        assert res.feasibility_rating in (
            FeasibilityRating.REALISTIC,
            FeasibilityRating.SLIGHTLY_UNDERBUDGETED,
        )
        assert res.feasibility_score >= 70.0
        assert res.estimated_engineering_hours_min >= 20
        assert res.estimated_fair_market_budget > 0

    def test_detect_severe_underbudgeting_scope_creep(self):
        analyzer = BudgetFeasibilityAnalyzer()
        req = BudgetFeasibilityRequest(
            project_title="Build Full AI Knowledge Platform with React UI, WebSockets, Celery, and Auth",
            project_description="Complete enterprise system with React frontend, real-time WebSocket streaming, OpenAI vector RAG, Docker setup, and Stripe billing.",
            proposed_budget=200.0,  # Ridiculously low budget for full enterprise scope
            target_skills=["Python", "React", "Docker", "FastAPI", "OpenAI"],
        )
        res = analyzer.evaluate_feasibility(req)

        assert res.feasibility_rating in (
            FeasibilityRating.UNREALISTIC_LOW_BUDGET,
            FeasibilityRating.HIGH_RISK_SCOPE_CREEP,
        )
        assert res.feasibility_score <= 50.0
        assert res.scope_creep_risk_level in ("HIGH", "CRITICAL")
        assert res.recommended_counter_budget > 1000.0
        assert len(res.scope_reduction_suggestions) >= 2


class TestClientIntelligenceApiEndpoints:
    """Test suite for FastAPI REST API endpoints under /api/intelligence."""

    def test_client_dossier_route(self):
        payload = {
            "client_name": "Datadog Labs",
            "project_title": "Distributed Tracing Agent",
            "project_description": "Build an open-telemetry collector in Python with Docker.",
            "source": "RemoteOK",
            "source_url": "https://datadoghq.com/careers/001",
            "claimed_budget": 7500.0,
        }
        res = client.post("/api/intelligence/client-dossier", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["client_name"] == "Datadog Labs"
        assert data["inferred_company_domain"] == "datadoghq.com"
        assert data["overall_trust_score"] >= 80.0

    def test_scam_audit_route(self):
        payload = {
            "project_title": "Telegram Bot Developer",
            "project_description": "Contact me on telegram @fraud for direct paypal before contract.",
            "claimed_budget": 5000.0,
        }
        res = client.post("/api/intelligence/scam-audit", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["is_safe_to_apply"] is False
        assert data["risk_tier"] in ("HIGH", "CRITICAL")

    def test_budget_feasibility_route(self):
        payload = {
            "project_title": "FastAPI Web Service",
            "project_description": "Build modern CRUD backend with PostgreSQL.",
            "proposed_budget": 4500.0,
        }
        res = client.post("/api/intelligence/budget-feasibility", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["feasibility_rating"] in ("REALISTIC", "SLIGHTLY_UNDERBUDGETED")
        assert data["estimated_engineering_hours_min"] > 0

    def test_from_project_route(self):
        uid = uuid.uuid4().hex[:8]
        url = f"https://example.com/project/{uid}"
        title = f"Agent Backend Service {uid}"
        desc = "Series A startup seeking FastAPI engineer for PostgreSQL backend."

        with SessionLocal() as session:
            proj = ProjectModel(
                external_id=f"test_intel_{uid}",
                title=title,
                description=desc,
                source_url=url,
                url_hash=compute_url_hash(url),
                content_hash=compute_content_hash(title, desc),
                client_name="Scale AI",
                budget=5500.0,
                source="Hacker News",
            )
            session.add(proj)
            session.commit()
            session.refresh(proj)
            proj_id = proj.id

        res = client.get(f"/api/intelligence/from-project/{proj_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["project_id"] == proj_id
        assert data["client_dossier"]["client_name"] == "Scale AI"
        assert data["scam_audit"]["is_safe_to_apply"] is True
        assert data["budget_feasibility"]["feasibility_score"] >= 60.0
