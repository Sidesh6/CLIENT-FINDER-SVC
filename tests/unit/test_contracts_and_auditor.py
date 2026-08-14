"""
Unit tests for AI Proposal Quality Auditor, SOW Milestone Contract Generator, and Protective Scope Guard.
"""

from fastapi.testclient import TestClient

from src.api.main import app
from src.proposal.auditor import (
    ProposalAuditor,
    ProposalAuditRequest,
    ProposalAuditResult,
)
from src.proposal.scope_guard import (
    ContractClause,
    ScopeGuard,
    SOWMilestone,
    SOWRequest,
    SOWResult,
)

client = TestClient(app)


class TestProposalAuditor:
    """Tests for proposal conversion readiness heuristics and scoring."""

    def test_high_quality_proposal_audit(self):
        auditor = ProposalAuditor()
        high_quality_text = (
            "Hi Alex,\n\n"
            "I reviewed your requirements for the FastAPI & LangChain AI microservice platform. "
            "In a recent project, I designed a similar asynchronous RAG pipeline that reduced query latency by 45% "
            "and supported over 10,000 daily active users with 99.9% uptime.\n\n"
            "I propose structuring this in 2 phased milestones with a clear technical blueprint delivery within week 1. "
            "Are you free for a quick 10-minute discovery call this Wednesday to align on the core API schemas?\n\n"
            "Best regards,\nAlex Rivera"
        )
        req = ProposalAuditRequest(
            proposal_text=high_quality_text,
            project_title="FastAPI & LangChain AI Platform",
            target_skills=["FastAPI", "LangChain", "Python", "RAG"],
            target_budget=6000.0,
        )
        res = auditor.audit(req)

        assert isinstance(res, ProposalAuditResult)
        assert res.overall_readiness_score >= 75.0
        assert res.grade in ["EXCELLENT", "STRONG"]
        assert res.word_count > 50
        assert len(res.dimensions) == 5
        assert len(res.detected_strengths) >= 2

    def test_poor_quality_proposal_audit(self):
        auditor = ProposalAuditor()
        poor_text = "I am a developer. I can do this job. Contact me."
        req = ProposalAuditRequest(
            proposal_text=poor_text,
            project_title="Senior Rust & Kubernetes Architect",
            target_skills=["Rust", "Kubernetes"],
        )
        res = auditor.audit(req)

        assert isinstance(res, ProposalAuditResult)
        assert res.overall_readiness_score < 65.0
        assert res.grade in ["NEEDS_IMPROVEMENT", "POOR"]
        assert len(res.actionable_recommendations) >= 2


class TestScopeGuard:
    """Tests for Scope of Work synthesis and protective contract terms."""

    def test_sow_generation(self):
        guard = ScopeGuard()
        req = SOWRequest(
            project_title="Enterprise RAG Pipeline",
            project_description="High-throughput vector search microservice",
            client_name="Starlight AI",
            total_budget=8000.0,
            skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        )
        res = guard.generate_sow(req)

        assert isinstance(res, SOWResult)
        assert res.total_budget == 8000.0
        assert len(res.milestones) == 3
        assert all(isinstance(m, SOWMilestone) for m in res.milestones)

        # Confirm 30 / 40 / 30 cost split
        assert res.milestones[0].payment_amount == 2400.0
        assert res.milestones[1].payment_amount == 3200.0
        assert res.milestones[2].payment_amount == 2400.0

        # Confirm markdown format contains all essential clauses
        assert "STATEMENT OF WORK" in res.formatted_markdown_contract
        assert "Phase 1:" in res.formatted_markdown_contract
        assert "Phase 2:" in res.formatted_markdown_contract
        assert "Scope Boundary" in res.formatted_markdown_contract

    def test_get_standard_protective_clauses(self):
        guard = ScopeGuard()
        clauses = guard.get_standard_protective_clauses()

        assert isinstance(clauses, list)
        assert len(clauses) >= 4
        assert all(isinstance(c, ContractClause) for c in clauses)
        titles = {c.clause_title for c in clauses}
        assert "Scope Boundary & Formal Change Orders" in titles
        assert "Client Review Window & Deemed Acceptance" in titles


class TestContractsApiRoutes:
    """Tests for contracts, audit, and SOW REST endpoints."""

    def test_audit_proposal_endpoint(self):
        res = client.post(
            "/api/contracts/audit-proposal",
            json={
                "proposal_text": (
                    "Hi there! I built high-throughput FastAPI systems scaling to 15k RPS with 99.9% uptime. "
                    "I would love to help build your backend. Are you free for a quick chat Tuesday?"
                ),
                "project_title": "FastAPI Backend Lead",
                "target_skills": ["FastAPI", "Python"],
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "overall_readiness_score" in data
        assert "dimensions" in data
        assert len(data["dimensions"]) == 5

    def test_generate_sow_endpoint(self):
        res = client.post(
            "/api/contracts/generate-sow",
            json={
                "project_title": "Distributed Web Harvester",
                "client_name": "Acme Media",
                "total_budget": 5000.0,
                "skills": ["Python", "FastAPI", "PostgreSQL"],
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_budget"] == 5000.0
        assert len(data["milestones"]) == 3
        assert "formatted_markdown_contract" in data

    def test_get_clauses_endpoint(self):
        res = client.get("/api/contracts/clauses")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 4
