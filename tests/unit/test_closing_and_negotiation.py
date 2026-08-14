"""
Unit tests for AI Negotiation, Objection Handling, Follow-Up Cadence, and Technical Interview Prep.
"""

import uuid

from fastapi.testclient import TestClient

from src.api.main import app
from src.database.connection import SessionLocal
from src.database.models import ApplicationModel, ApplicationStatus, ProjectModel
from src.proposal.followup import (
    FollowUpManager,
    FollowUpRequest,
    FollowUpResponse,
    FollowUpStage,
)
from src.proposal.interview_prep import (
    InterviewPrepAdvisor,
    InterviewPrepSheet,
    InterviewQuestion,
)
from src.proposal.negotiation import (
    NegotiationAdvisor,
    NegotiationRequest,
    NegotiationResponse,
    NegotiationStrategy,
    ObjectionType,
)

client = TestClient(app)


class TestNegotiationAdvisor:
    """Tests for objection handling strategies and counter-offer logic."""

    def test_value_anchoring_strategy(self):
        advisor = NegotiationAdvisor()
        req = NegotiationRequest(
            project_title="FastAPI AI Platform",
            project_description="High performance backend",
            objection_type=ObjectionType.RATE_TOO_HIGH,
            strategy=NegotiationStrategy.VALUE_ANCHORING,
            target_hourly_rate=120.0,
            client_budget=5000.0,
        )
        res = advisor.advise(req)

        assert isinstance(res, NegotiationResponse)
        assert res.strategy_used == NegotiationStrategy.VALUE_ANCHORING
        assert "$120/hr" in res.recommended_response
        assert "10-hour exploratory milestone" in res.alternative_counter_offer
        assert len(res.concession_rules) >= 1

    def test_scope_modulation_strategy(self):
        advisor = NegotiationAdvisor()
        req = NegotiationRequest(
            project_title="NextJS & Python App",
            project_description="Full stack app",
            objection_type=ObjectionType.RATE_TOO_HIGH,
            strategy=NegotiationStrategy.SCOPE_MODULATION,
            target_hourly_rate=100.0,
            client_budget=3000.0,
        )
        res = advisor.advise(req)

        assert res.strategy_used == NegotiationStrategy.SCOPE_MODULATION
        assert "Phase 1" in res.recommended_response
        assert "Phase 2" in res.recommended_response

    def test_fixed_price_and_deadline_objections(self):
        advisor = NegotiationAdvisor()
        res_fixed = advisor.advise(
            NegotiationRequest(
                project_title="Fixed Job",
                project_description="Desc",
                objection_type=ObjectionType.FIXED_PRICE_REQUEST,
            )
        )
        assert "acceptance criteria" in res_fixed.recommended_response.lower()

        res_rush = advisor.advise(
            NegotiationRequest(
                project_title="Rush Job",
                project_description="Desc",
                objection_type=ObjectionType.TIGHT_DEADLINE,
                target_hourly_rate=100.0,
            )
        )
        assert res_rush.commercial_terms.get("priority_turnaround") is True


class TestFollowUpManager:
    """Tests for multi-stage follow-up message generation."""

    def test_day_3_checkin_generation(self):
        mgr = FollowUpManager()
        req = FollowUpRequest(
            project_title="Senior RAG Architect",
            project_description="Build RAG search",
            client_name="Sarah",
            stage=FollowUpStage.DAY_3_CHECKIN,
        )
        res = mgr.generate(req)

        assert isinstance(res, FollowUpResponse)
        assert res.stage == FollowUpStage.DAY_3_CHECKIN
        assert "Sarah" in res.body_text
        assert "Senior RAG Architect" in res.subject_line
        assert "3 business days" in res.recommended_send_timing

    def test_day_7_and_day_14_cadences(self):
        mgr = FollowUpManager()
        res_7 = mgr.generate(
            FollowUpRequest(
                project_title="FastAPI Lead",
                project_description="Desc",
                stage=FollowUpStage.DAY_7_VALUE_ADD,
            )
        )
        assert "Loom" in res_7.body_text

        res_14 = mgr.generate(
            FollowUpRequest(
                project_title="FastAPI Lead",
                project_description="Desc",
                stage=FollowUpStage.DAY_14_BREAKUP,
            )
        )
        assert "close out my file" in res_14.body_text


class TestInterviewPrepAdvisor:
    """Tests for technical interview preparation cheatsheet synthesis."""

    def test_interview_prep_generation(self):
        advisor = InterviewPrepAdvisor()
        sheet = advisor.generate(
            project_title="Autonomous Agent Architect",
            project_description="Build LLM tool-calling autonomous agents with FastAPI",
            skills=["Python", "FastAPI", "PostgreSQL", "LangChain"],
        )

        assert isinstance(sheet, InterviewPrepSheet)
        assert sheet.project_title == "Autonomous Agent Architect"
        assert len(sheet.likely_questions) >= 3
        assert len(sheet.reverse_questions_to_ask_client) >= 2
        assert len(sheet.red_flags_to_watch_for) >= 2
        assert all(isinstance(q, InterviewQuestion) for q in sheet.likely_questions)


class TestClosingApiRoutes:
    """Tests for closing, negotiation, and follow-up REST endpoints."""

    def test_negotiate_api_route(self):
        res = client.post(
            "/api/closing/negotiate",
            json={
                "project_title": "AI Backend Engineer",
                "project_description": "Build high throughput microservices",
                "objection_type": "RATE_TOO_HIGH",
                "strategy": "VALUE_ANCHORING",
                "target_hourly_rate": 95.0,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "recommended_response" in data
        assert "alternative_counter_offer" in data

    def test_followup_api_route(self):
        res = client.post(
            "/api/closing/followup",
            json={
                "project_title": "Full-Stack Dev",
                "project_description": "React and Python",
                "client_name": "Marcus",
                "stage": "DAY_3_CHECKIN",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["stage"] == "DAY_3_CHECKIN"
        assert "Marcus" in data["body_text"]

    def test_interview_prep_api_route(self):
        res = client.post(
            "/api/closing/interview-prep",
            json={
                "project_title": "Senior Python Architect",
                "project_description": "Scalable REST APIs",
                "skills": ["Python", "FastAPI"],
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "likely_questions" in data
        assert len(data["likely_questions"]) >= 3

    def test_followup_from_tracked_application_route(self):
        with SessionLocal() as session:
            url_str = f"https://example.com/{uuid.uuid4().hex}"
            proj = ProjectModel(
                title="Followup Test Proj",
                description="Followup Desc",
                source="WeWorkRemotely",
                source_url=url_str,
                url_hash=uuid.uuid4().hex,
                content_hash=uuid.uuid4().hex,
                client_name="Elena",
            )
            session.add(proj)
            session.flush()

            app_rec = ApplicationModel(
                project_id=proj.id,
                status=ApplicationStatus.APPLIED.value,
                pitch_angle="TECHNICAL_EXPERT",
                proposal_text="Sample pitch",
            )
            session.add(app_rec)
            session.commit()
            app_id = app_rec.id

        res = client.post(f"/api/closing/from-application/{app_id}/followup?stage=DAY_3_CHECKIN")
        assert res.status_code == 200
        data = res.json()
        assert "Elena" in data["body_text"]
        assert "Followup Test Proj" in data["subject_line"]
