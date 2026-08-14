"""
Unit tests for AnalyticsEngine, WinProbabilityCalibrator, and Analytics REST endpoints.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from src.analytics.calibrator import WinProbabilityCalibrator
from src.analytics.engine import AnalyticsEngine
from src.api.main import app
from src.database.connection import Base, engine, get_db
from src.database.models import ApplicationStatus, ProjectModel
from src.models.project import Project
from src.proposal.schemas import PitchAngle
from src.tracking.schemas import ApplicationCreate, ApplicationStatusUpdate
from src.tracking.tracker import ApplicationTracker

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield


def create_project_with_skills(session, skills: list[str], budget: float = 4000.0) -> ProjectModel:
    uid = uuid.uuid4().hex[:8]
    proj = Project(
        title=f"Analytics Test Project {uid}",
        description="Software development requirement",
        source="Hacker News",
        source_url=f"https://example.com/analytics-{uid}",
        skills=skills,
        budget=budget,
    )
    pm = ProjectModel.from_pydantic(proj)
    session.add(pm)
    session.commit()
    session.refresh(pm)
    return pm


class TestAnalyticsEngine:
    """Tests for Funnel calculations, velocity, pitch angle, and skill metrics."""

    def test_funnel_metrics_calculation(self):
        engine_svc = AnalyticsEngine()
        tracker = ApplicationTracker()

        with next(get_db()) as session:
            # Create 4 applications: 1 APPLIED, 1 REPLIED, 1 INTERVIEW, 1 WON
            pm1 = create_project_with_skills(session, ["FastAPI", "Python"], budget=3000.0)
            pm2 = create_project_with_skills(session, ["Python", "RAG"], budget=4000.0)
            pm3 = create_project_with_skills(session, ["React", "FastAPI"], budget=5000.0)
            pm4 = create_project_with_skills(session, ["Python", "FastAPI"], budget=6000.0)

            tracker.track_application(
                ApplicationCreate(
                    project_id=pm1.id, status=ApplicationStatus.APPLIED, proposed_budget=3000.0
                ),
                session=session,
            )
            tracker.track_application(
                ApplicationCreate(
                    project_id=pm2.id,
                    status=ApplicationStatus.CLIENT_REPLIED,
                    proposed_budget=4000.0,
                ),
                session=session,
            )
            tracker.track_application(
                ApplicationCreate(
                    project_id=pm3.id, status=ApplicationStatus.INTERVIEW, proposed_budget=5000.0
                ),
                session=session,
            )
            app4 = tracker.track_application(
                ApplicationCreate(
                    project_id=pm4.id, status=ApplicationStatus.WON, proposed_budget=6000.0
                ),
                session=session,
            )
            tracker.transition_status(
                app4.id,
                ApplicationStatusUpdate(status=ApplicationStatus.WON, final_revenue=6500.0),
                session=session,
            )

            funnel = engine_svc.compute_funnel_metrics(session=session)

            assert funnel.total_applications >= 4
            assert funnel.won_count >= 1
            assert funnel.win_rate > 0.0

    def test_pitch_angle_performance(self):
        engine_svc = AnalyticsEngine()
        tracker = ApplicationTracker()

        with next(get_db()) as session:
            pm = create_project_with_skills(session, ["Python"])
            tracker.track_application(
                ApplicationCreate(
                    project_id=pm.id,
                    status=ApplicationStatus.WON,
                    pitch_angle=PitchAngle.TECHNICAL_EXPERT,
                    proposed_budget=5000.0,
                ),
                session=session,
            )
            tracker.transition_status(
                pm.application.id,
                ApplicationStatusUpdate(status=ApplicationStatus.WON, final_revenue=5500.0),
                session=session,
            )

            metrics = engine_svc.compute_pitch_angle_performance(session=session)
            assert len(metrics) == len(PitchAngle)
            tech_expert = next(m for m in metrics if m.pitch_angle == PitchAngle.TECHNICAL_EXPERT)
            assert tech_expert.total_sent >= 1
            assert tech_expert.won >= 1
            assert tech_expert.total_revenue >= 5500.0

    def test_skill_performance_and_revenue(self):
        engine_svc = AnalyticsEngine()
        tracker = ApplicationTracker()

        with next(get_db()) as session:
            pm = create_project_with_skills(session, ["FastAPI", "Python"], budget=5000.0)
            app_obj = tracker.track_application(
                ApplicationCreate(
                    project_id=pm.id, status=ApplicationStatus.WON, proposed_budget=5000.0
                ),
                session=session,
            )
            tracker.transition_status(
                app_obj.id,
                ApplicationStatusUpdate(status=ApplicationStatus.WON, final_revenue=5000.0),
                session=session,
            )

            skill_metrics = engine_svc.compute_skill_performance(
                session=session, min_applications=1
            )
            assert len(skill_metrics) >= 1
            fastapi_skill = next((s for s in skill_metrics if s.skill.lower() == "fastapi"), None)
            assert fastapi_skill is not None
            assert fastapi_skill.wins_count >= 1

    def test_revenue_metrics(self):
        engine_svc = AnalyticsEngine()
        with next(get_db()) as session:
            rev = engine_svc.compute_revenue_metrics(session=session)
            assert rev.currency == "USD"
            assert rev.realized_revenue >= 0.0

    def test_generate_insights(self):
        engine_svc = AnalyticsEngine()
        with next(get_db()) as session:
            insights = engine_svc.generate_insights(session=session)
            assert isinstance(insights.recommendations, list)


class TestWinProbabilityCalibrator:
    """Tests for empirical win probability modifier learning."""

    def test_calibrator_with_outcomes(self):
        calibrator = WinProbabilityCalibrator(min_samples_threshold=2)
        tracker = ApplicationTracker()

        with next(get_db()) as session:
            # Create 2 WON and 1 LOST applications for Python
            for _ in range(2):
                pm_w = create_project_with_skills(session, ["PyTorch"])
                app_w = tracker.track_application(
                    ApplicationCreate(
                        project_id=pm_w.id,
                        status=ApplicationStatus.WON,
                        pitch_angle=PitchAngle.TECHNICAL_EXPERT,
                    ),
                    session=session,
                )
                tracker.transition_status(
                    app_w.id,
                    ApplicationStatusUpdate(status=ApplicationStatus.WON, final_revenue=3000.0),
                    session=session,
                )

            modifiers = calibrator.get_learned_modifiers(session=session)
            assert isinstance(modifiers, list)

            # Calibrate win probability on a new PyTorch project
            test_proj = Project(
                title="PyTorch Model Tuning",
                description="Need PyTorch engineer",
                source="HN",
                source_url="https://example.com/pytorch",
                skills=["PyTorch"],
            )
            calibrated_prob = calibrator.calibrate_win_probability(
                project=test_proj,
                base_probability=50.0,
                pitch_angle=PitchAngle.TECHNICAL_EXPERT,
                session=session,
            )
            assert 5.0 <= calibrated_prob <= 95.0


class TestAnalyticsApiRoutes:
    """Tests for Analytics REST endpoints."""

    def test_all_analytics_routes(self):
        res_funnel = client.get("/api/analytics/funnel")
        assert res_funnel.status_code == 200
        assert "total_applications" in res_funnel.json()

        res_pitch = client.get("/api/analytics/pitch-angles")
        assert res_pitch.status_code == 200
        assert len(res_pitch.json()) == len(PitchAngle)

        res_skills = client.get("/api/analytics/skills?min_applications=1")
        assert res_skills.status_code == 200
        assert isinstance(res_skills.json(), list)

        res_rev = client.get("/api/analytics/revenue")
        assert res_rev.status_code == 200
        assert "realized_revenue" in res_rev.json()

        res_insights = client.get("/api/analytics/insights")
        assert res_insights.status_code == 200
        assert "recommendations" in res_insights.json()

        res_mod = client.get("/api/analytics/modifiers")
        assert res_mod.status_code == 200
        assert isinstance(res_mod.json(), list)
