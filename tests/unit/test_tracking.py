"""
Unit tests for Application Tracking, Lifecycle State Transitions, and REST API Endpoints.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database.connection import Base, engine, get_db
from src.database.models import ApplicationStatus, ProjectModel
from src.models.project import Project
from src.proposal.schemas import PitchAngle
from src.tracking.schemas import (
    ApplicationCreate,
    ApplicationFilter,
    ApplicationStatusUpdate,
)
from src.tracking.tracker import ApplicationTracker

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield


def create_sample_project(session) -> ProjectModel:
    uid = uuid.uuid4().hex[:8]
    proj = Project(
        title=f"FastAPI Backend Lead {uid}",
        description="Need senior developer for microservice RAG backend",
        source="Hacker News",
        source_url=f"https://example.com/proj-{uid}",
        skills=["Python", "FastAPI", "RAG"],
        budget=4500.0,
    )
    pm = ProjectModel.from_pydantic(proj)
    session.add(pm)
    session.commit()
    session.refresh(pm)
    return pm


class TestApplicationTracker:
    """Tests for Application Lifecycle State Machine and persistence."""

    def test_track_application_and_project_status_sync(self):
        tracker = ApplicationTracker()
        with next(get_db()) as session:
            pm = create_sample_project(session)
            payload = ApplicationCreate(
                project_id=pm.id,
                status=ApplicationStatus.APPLIED,
                proposed_budget=5000.0,
                pitch_angle=PitchAngle.TECHNICAL_EXPERT,
                notes="Initial proposal sent",
            )
            app_obj = tracker.track_application(payload, session=session)

            assert app_obj.id is not None
            assert app_obj.project_id == pm.id
            assert app_obj.status == ApplicationStatus.APPLIED.value
            assert app_obj.proposed_budget == 5000.0
            assert app_obj.applied_at is not None

            # Verify parent project status synchronized
            session.refresh(pm)
            assert pm.status == "APPLIED"

    def test_transition_status_and_timestamp_automation(self):
        tracker = ApplicationTracker()
        with next(get_db()) as session:
            pm = create_sample_project(session)
            payload = ApplicationCreate(
                project_id=pm.id,
                status=ApplicationStatus.APPLIED,
                proposed_budget=6000.0,
            )
            app_obj = tracker.track_application(payload, session=session)

            # 1. Transition to CLIENT_REPLIED
            up_reply = ApplicationStatusUpdate(
                status=ApplicationStatus.CLIENT_REPLIED,
                client_feedback="Looks interesting! Can you hop on a discovery call?",
            )
            app_replied = tracker.transition_status(app_obj.id, up_reply, session=session)
            assert app_replied.status == ApplicationStatus.CLIENT_REPLIED.value
            assert app_replied.response_at is not None
            assert app_replied.client_feedback == up_reply.client_feedback

            # 2. Transition to INTERVIEW
            up_interview = ApplicationStatusUpdate(status=ApplicationStatus.INTERVIEW)
            app_interview = tracker.transition_status(app_obj.id, up_interview, session=session)
            assert app_interview.status == ApplicationStatus.INTERVIEW.value
            assert app_interview.interview_at is not None

            # 3. Transition to WON
            up_won = ApplicationStatusUpdate(
                status=ApplicationStatus.WON,
                final_revenue=6200.0,
                notes="Contract signed and milestone paid",
            )
            app_won = tracker.transition_status(app_obj.id, up_won, session=session)
            assert app_won.status == ApplicationStatus.WON.value
            assert app_won.final_revenue == 6200.0
            assert app_won.closed_at is not None

    def test_list_and_filter_applications(self):
        tracker = ApplicationTracker()
        with next(get_db()) as session:
            pm1 = create_sample_project(session)
            pm2 = create_sample_project(session)

            tracker.track_application(
                ApplicationCreate(
                    project_id=pm1.id,
                    status=ApplicationStatus.APPLIED,
                    pitch_angle=PitchAngle.FAST_DELIVERY,
                ),
                session=session,
            )
            tracker.track_application(
                ApplicationCreate(
                    project_id=pm2.id,
                    status=ApplicationStatus.WON,
                    pitch_angle=PitchAngle.VALUE_ROI,
                ),
                session=session,
            )

            # Filter by status
            won_apps = tracker.list_applications(
                ApplicationFilter(status=ApplicationStatus.WON), session=session
            )
            assert any(a.project_id == pm2.id for a in won_apps)

            # Filter by pitch angle
            fast_apps = tracker.list_applications(
                ApplicationFilter(pitch_angle=PitchAngle.FAST_DELIVERY), session=session
            )
            assert any(a.project_id == pm1.id for a in fast_apps)


class TestApplicationApiRoutes:
    """Tests for Applications REST endpoints."""

    def test_create_and_get_application_routes(self):
        with next(get_db()) as session:
            pm = create_sample_project(session)

        # POST /api/applications
        res = client.post(
            "/api/applications",
            json={
                "project_id": pm.id,
                "status": "APPLIED",
                "proposed_budget": 3500.0,
                "pitch_angle": "TECHNICAL_EXPERT",
                "proposal_text": "Here is my detailed solution proposal...",
            },
        )
        assert res.status_code == 201
        data = res.json()
        app_id = data["id"]
        assert data["project_id"] == pm.id
        assert data["status"] == "APPLIED"
        assert data["proposed_budget"] == 3500.0

        # GET /api/applications/{id}
        res_get = client.get(f"/api/applications/{app_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == app_id

        # GET /api/applications (list)
        res_list = client.get("/api/applications?limit=10")
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 1

    def test_patch_status_route(self):
        with next(get_db()) as session:
            pm = create_sample_project(session)

        res_post = client.post(
            "/api/applications",
            json={"project_id": pm.id, "status": "APPLIED"},
        )
        app_id = res_post.json()["id"]

        # PATCH /api/applications/{id}/status
        res_patch = client.patch(
            f"/api/applications/{app_id}/status",
            json={
                "status": "CLIENT_REPLIED",
                "client_feedback": "Great portfolio!",
            },
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["status"] == "CLIENT_REPLIED"
        assert res_patch.json()["client_feedback"] == "Great portfolio!"

    def test_delete_application_route(self):
        with next(get_db()) as session:
            pm = create_sample_project(session)

        res_post = client.post(
            "/api/applications",
            json={"project_id": pm.id, "status": "APPLIED"},
        )
        app_id = res_post.json()["id"]

        res_del = client.delete(f"/api/applications/{app_id}")
        assert res_del.status_code == 200
        assert res_del.json()["deleted"] is True
