"""
Unit Tests for Phase 16 Autonomous Outreach Sequences, Inbound Intent Classifier, and A/B Pitch Experimentation.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database.connection import SessionLocal, init_db
from src.database.models import ApplicationModel, ApplicationStatus, ProjectModel
from src.models.profile import get_default_profile
from src.outreach.experiments import ProposalExperimenter
from src.outreach.inbound import InboundReplyClassifier
from src.outreach.schemas import (
    InboundReplyRequest,
    IntentType,
    OutreachSequenceCreate,
    SequenceStatus,
    SequenceStepType,
    StepStatus,
)
from src.outreach.sequences import OutreachSequenceEngine
from src.proposal.schemas import PitchAngle


import uuid

@pytest.fixture(autouse=True)
def setup_test_database():
    """Initialize fresh database before each test run."""
    init_db()
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        source_url = f"https://example.com/proj/{uid}"
        title = f"FastAPI AI Agent Orchestrator {uid}"
        desc = "Build scalable background agent workflow engine in Python."
        from src.database.models import compute_content_hash, compute_url_hash
        proj = ProjectModel(
            external_id=f"test_outreach_proj_{uid}",
            title=title,
            description=desc,
            source_url=source_url,
            url_hash=compute_url_hash(source_url),
            content_hash=compute_content_hash(title, desc),
            source="RemoteOK",
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)

        app_rec = ApplicationModel(
            project_id=proj.id,
            status=ApplicationStatus.APPLIED,
            notes="Initial proposal dispatched.",
        )
        db.add(app_rec)
        db.commit()
        db.refresh(app_rec)
    finally:
        db.close()


class TestOutreachSequenceEngine:
    """Test suite for multi-touch outreach cadence generation and step management."""

    def test_create_outreach_sequence_default_cadence(self):
        engine = OutreachSequenceEngine()
        req = OutreachSequenceCreate(
            application_id=1,
            project_title="FastAPI AI Agent Orchestrator",
            client_name="Acme Corp",
            pitch_angle=PitchAngle.TECHNICAL_EXPERT,
            target_skills=["Python", "FastAPI", "PostgreSQL"],
            auto_start=True,
        )

        seq = engine.create_sequence(req)
        assert seq.sequence_id.startswith("seq_")
        assert seq.application_id == 1
        assert seq.status == SequenceStatus.ACTIVE
        assert seq.total_steps == 5
        assert seq.current_step_index == 2  # Step 1 was auto-started

        # Verify Step 1 executed, Step 2-5 pending
        assert seq.steps[0].step_type == SequenceStepType.INITIAL_PROPOSAL
        assert seq.steps[0].status == StepStatus.EXECUTED
        assert seq.steps[1].step_type == SequenceStepType.DAY_3_DIAGNOSIS
        assert seq.steps[1].delay_days == 3
        assert seq.steps[1].status == StepStatus.PENDING
        assert seq.steps[2].step_type == SequenceStepType.DAY_7_CASE_STUDY
        assert seq.steps[3].step_type == SequenceStepType.DAY_14_BREAKUP
        assert seq.steps[4].step_type == SequenceStepType.DAY_30_REVIVE

    def test_advance_sequence_steps_to_completion(self):
        engine = OutreachSequenceEngine()
        req = OutreachSequenceCreate(
            application_id=2,
            project_title="Cloud Migration",
            auto_start=False,
        )
        seq = engine.create_sequence(req)
        assert seq.status == SequenceStatus.PENDING
        assert seq.current_step_index == 1

        # Advance step 1 -> 2
        s1 = engine.advance_step(seq.sequence_id)
        assert s1.current_step_index == 2
        assert s1.steps[0].status == StepStatus.EXECUTED

        # Advance 2 -> 3 -> 4 -> 5 -> Complete
        engine.advance_step(seq.sequence_id)
        engine.advance_step(seq.sequence_id)
        engine.advance_step(seq.sequence_id)
        final_seq = engine.advance_step(seq.sequence_id)

        assert final_seq.status == SequenceStatus.COMPLETED
        assert all(step.status == StepStatus.EXECUTED for step in final_seq.steps)

    def test_pause_resume_and_cancel_sequence(self):
        engine = OutreachSequenceEngine()
        req = OutreachSequenceCreate(
            application_id=3,
            project_title="Data Pipeline",
        )
        seq = engine.create_sequence(req)

        paused = engine.pause_sequence(seq.sequence_id)
        assert paused.status == SequenceStatus.PAUSED

        resumed = engine.resume_sequence(seq.sequence_id)
        assert resumed.status == SequenceStatus.ACTIVE

        cancelled = engine.cancel_sequence(seq.sequence_id, reason="Client Replied")
        assert cancelled.status == SequenceStatus.CANCELLED

    def test_auto_cancel_on_application_status_change(self):
        engine = OutreachSequenceEngine()
        req = OutreachSequenceCreate(
            application_id=10,
            project_title="E-Commerce API",
            auto_start=True,
        )
        engine.create_sequence(req)

        # Status transition to INTERVIEW should auto-cancel active sequences
        updated_count = engine.handle_application_status_change(
            application_id=10, new_status="INTERVIEW"
        )
        assert updated_count == 1

        seq = engine.list_sequences(application_id=10)[0]
        assert seq.status == SequenceStatus.CANCELLED


class TestInboundReplyClassifier:
    """Test suite for inbound client message intent classification and response synthesis."""

    def test_classify_schedule_call_intent(self):
        classifier = InboundReplyClassifier()
        req = InboundReplyRequest(
            message_text="Hi! We loved your proposal. Are you available for a quick Zoom call this Thursday at 2pm EST to discuss the architecture?",
            project_title="FastAPI AI Workflow",
            client_name="David",
        )
        res = classifier.analyze_reply(req=req, update_db=False)

        assert res.classified_intent == IntentType.SCHEDULE_CALL
        assert res.confidence >= 0.85
        assert res.sentiment_score > 0.5
        assert res.recommended_funnel_status == "INTERVIEW"
        assert "Thursday" in res.suggested_response_draft or "calendar" in res.suggested_response_draft.lower()

    def test_classify_rate_pushback_intent(self):
        classifier = InboundReplyClassifier()
        req = InboundReplyRequest(
            message_text="Thanks for reaching out. Your background looks strong, but your proposed rate is too high and out of our budget. Can you offer a lower rate or a fixed price instead?",
            project_title="Backend API",
            client_name="Sarah",
        )
        res = classifier.analyze_reply(req=req, update_db=False)

        assert res.classified_intent == IntentType.RATE_PUSHBACK
        assert "BUDGET_TOO_HIGH" in res.detected_objections
        assert res.recommended_funnel_status == "NEGOTIATION"
        assert "Phase 1" in res.suggested_response_draft or "milestone" in res.suggested_response_draft.lower()

    def test_classify_scope_question_intent(self):
        classifier = InboundReplyClassifier()
        req = InboundReplyRequest(
            message_text="How do you handle rate limiting and database connection pooling under high concurrent traffic?",
            project_title="High Throughput Engine",
        )
        res = classifier.analyze_reply(req=req, update_db=False)

        assert res.classified_intent == IntentType.SCOPE_QUESTION
        assert res.recommended_funnel_status == "CLIENT_REPLIED"
        assert "latency" in res.suggested_response_draft or "queues" in res.suggested_response_draft

    def test_classify_rejection_intent(self):
        classifier = InboundReplyClassifier()
        req = InboundReplyRequest(
            message_text="Thank you for your application, but we have already filled the position with another candidate.",
            project_title="Frontend Developer",
        )
        res = classifier.analyze_reply(req=req, update_db=False)

        assert res.classified_intent == IntentType.REJECTION
        assert res.sentiment_score < 0.0
        assert res.recommended_funnel_status == "LOST"

    def test_classify_out_of_office_intent(self):
        classifier = InboundReplyClassifier()
        req = InboundReplyRequest(
            message_text="I am currently out of the office on vacation with limited email access. Returning on August 20th.",
        )
        res = classifier.analyze_reply(req=req, update_db=False)

        assert res.classified_intent == IntentType.OUT_OF_OFFICE
        assert res.recommended_funnel_status == "APPLIED"


class TestProposalExperimenter:
    """Test suite for multi-armed bandit A/B pitch testing and conversion metrics."""

    def test_record_events_and_calculate_metrics(self):
        exp = ProposalExperimenter()
        # Record 10 impressions, 4 replies, 1 win for VALUE_ROI
        for _ in range(10):
            exp.record_event(
                pitch_angle=PitchAngle.VALUE_ROI, event_type="IMPRESSION", category="AI"
            )
        for _ in range(4):
            exp.record_event(
                pitch_angle=PitchAngle.VALUE_ROI, event_type="REPLY", category="AI"
            )
        exp.record_event(
            pitch_angle=PitchAngle.VALUE_ROI, event_type="WIN", category="AI"
        )

        metrics = exp.get_pitch_metrics()
        roi_metric = next(m for m in metrics if m.pitch_angle == PitchAngle.VALUE_ROI)

        assert roi_metric.impressions_sent >= 10
        assert roi_metric.replies_received >= 4
        assert roi_metric.reply_rate_percent > 0.0
        assert roi_metric.conversion_score > 0.0
        assert roi_metric.confidence_interval_low <= roi_metric.confidence_interval_high

    def test_summary_and_category_optimal_pitch(self):
        exp = ProposalExperimenter()
        summary = exp.get_summary()

        assert summary.total_outreach_events > 0
        assert summary.total_replies > 0
        assert summary.overall_reply_rate > 0.0
        assert isinstance(summary.best_performing_pitch, PitchAngle)
        assert "AI / Machine Learning" in summary.category_recommendations

        # Test greedy category selection
        pitch = exp.select_optimal_pitch_angle(category="AI / Machine Learning", epsilon=0.0)
        assert pitch == PitchAngle.TECHNICAL_EXPERT


class TestOutreachApiEndpoints:
    """Integration test suite for FastAPI outreach REST routes."""

    def test_outreach_rest_api_lifecycle(self):
        client = TestClient(app)

        # 1. Create Sequence
        payload = {
            "application_id": 1,
            "project_title": "AI Cloud Gateway",
            "client_name": "Stripe Labs",
            "pitch_angle": "TECHNICAL_EXPERT",
            "target_skills": ["Python", "FastAPI"],
            "auto_start": True,
        }
        res_create = client.post("/api/outreach/sequences", json=payload)
        assert res_create.status_code == 200
        seq = res_create.json()
        seq_id = seq["sequence_id"]
        assert seq["status"] == "ACTIVE"
        assert len(seq["steps"]) == 5

        # 2. Get Sequence
        res_get = client.get(f"/api/outreach/sequences/{seq_id}")
        assert res_get.status_code == 200
        assert res_get.json()["sequence_id"] == seq_id

        # 3. Advance Sequence
        res_adv = client.post(f"/api/outreach/sequences/{seq_id}/advance")
        assert res_adv.status_code == 200
        assert res_adv.json()["current_step_index"] == 3

        # 4. Pause and Resume
        res_pause = client.post(f"/api/outreach/sequences/{seq_id}/pause")
        assert res_pause.status_code == 200
        assert res_pause.json()["status"] == "PAUSED"

        res_res = client.post(f"/api/outreach/sequences/{seq_id}/resume")
        assert res_res.status_code == 200
        assert res_res.json()["status"] == "ACTIVE"

        # 5. Inbound Message Analysis
        reply_payload = {
            "message_text": "Hi, let's schedule a Zoom call for tomorrow!",
            "project_title": "AI Cloud Gateway",
            "client_name": "Stripe Labs",
        }
        res_reply = client.post("/api/outreach/inbound/analyze?update_db=false", json=reply_payload)
        assert res_reply.status_code == 200
        reply_data = res_reply.json()
        assert reply_data["classified_intent"] == "SCHEDULE_CALL"
        assert reply_data["recommended_funnel_status"] == "INTERVIEW"

        # 6. A/B Pitch Stats & Recommend Pitch
        res_stats = client.get("/api/outreach/experiments/pitch-stats")
        assert res_stats.status_code == 200
        assert "pitch_metrics" in res_stats.json()

        res_rec = client.get("/api/outreach/experiments/recommend-pitch?category=AI")
        assert res_rec.status_code == 200
        assert "recommended_pitch_angle" in res_rec.json()
