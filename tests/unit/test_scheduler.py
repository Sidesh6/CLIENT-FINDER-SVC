"""
Unit tests for PipelineCoordinator, PipelineScheduler background daemon, and API scheduler routes.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.collectors.base_collector import BaseCollector
from src.database.connection import Base, engine, get_db
from src.database.models import ProjectModel
from src.models.project import Project
from src.scheduler.coordinator import PipelineCoordinator, PipelineRunResult
from src.scheduler.service import PipelineScheduler

client = TestClient(app)


class MockCollector(BaseCollector):
    """Mock collector returning deterministic project dictionaries."""

    def __init__(self, items: list[dict]):
        super().__init__("MockCollector")
        self.items = items

    def collect(self) -> list[dict]:
        return list(self.items)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield


class TestPipelineCoordinator:
    """Tests for unified 8-step pipeline execution and error handling."""

    def test_run_cycle_dry_run(self):
        uid = uuid.uuid4().hex[:8]
        items = [
            {
                "title": f"FastAPI Microservice Lead {uid}",
                "description": "Build high performance FastAPI RAG backend with Python",
                "source": "MockSource",
                "source_url": f"https://example.com/dry-run-{uid}",
                "skills": ["FastAPI", "Python"],
            }
        ]
        collector = MockCollector(items)
        coordinator = PipelineCoordinator(collectors=[collector])

        result = coordinator.run_cycle(dry_run=True)

        assert isinstance(result, PipelineRunResult)
        assert result.collected_count == 1
        assert result.cleaned_count == 1
        assert result.new_projects_saved == 0  # Dry-run skips persistence
        assert result.duration_seconds >= 0.0
        assert result.success is True

    def test_run_cycle_full_persistence_and_scoring(self):
        uid = uuid.uuid4().hex[:8]
        items = [
            {
                "title": f"Full-Stack Python & RAG Architect {uid}",
                "description": "Urgent requirement for Senior Python and FastAPI engineer",
                "source": "Hacker News",
                "source_url": f"https://example.com/full-cycle-{uid}",
                "skills": ["Python", "FastAPI", "RAG"],
                "budget": 6000.0,
            }
        ]
        collector = MockCollector(items)
        coordinator = PipelineCoordinator(collectors=[collector])

        result = coordinator.run_cycle(min_notification_score=60.0)

        assert result.collected_count == 1
        assert result.new_projects_saved == 1
        assert result.opportunities_scored == 1
        assert result.duration_seconds >= 0.0

    def test_run_cycle_handles_collector_exception(self):
        failing_col = MagicMock()
        failing_col.name = "FailingCollector"
        failing_col.collect.side_effect = RuntimeError("Network timeout connecting to feed")

        coordinator = PipelineCoordinator(collectors=[failing_col])
        result = coordinator.run_cycle()

        assert result.collected_count == 0
        assert len(result.errors) >= 1
        assert "Network timeout" in result.errors[0]


class TestPipelineScheduler:
    """Tests for background scheduler daemon thread and digest."""

    def test_scheduler_start_pause_stop_lifecycle(self):
        scheduler = PipelineScheduler(harvest_interval_minutes=60.0)
        assert not scheduler.is_running()

        scheduler.start()
        assert scheduler.is_running()
        assert not scheduler.is_paused()

        scheduler.pause()
        assert scheduler.is_paused()

        scheduler.resume()
        assert not scheduler.is_paused()

        scheduler.stop()
        assert not scheduler.is_running()

    def test_scheduler_status_telemetry(self):
        scheduler = PipelineScheduler(harvest_interval_minutes=30.0)
        status = scheduler.get_status()

        assert "running" in status
        assert "paused" in status
        assert "harvest_interval_minutes" in status
        assert status["harvest_interval_minutes"] == 30.0
        assert "total_cycles_executed" in status

    def test_send_daily_digest(self):
        uid = uuid.uuid4().hex[:8]
        with next(get_db()) as session:
            proj = Project(
                title=f"Digest Test Lead {uid}",
                description="Python engineer for automated system",
                source="HN",
                source_url=f"https://example.com/digest-{uid}",
                skills=["Python"],
                score=88.0,
            )
            pm = ProjectModel.from_pydantic(proj)
            session.add(pm)
            session.commit()

        scheduler = PipelineScheduler()
        results = scheduler.send_daily_digest(lookback_hours=48)

        assert isinstance(results, list)
        assert len(results) >= 1


class TestSchedulerApiRoutes:
    """Tests for scheduler REST endpoints."""

    def test_get_scheduler_status(self):
        res = client.get("/api/scheduler/status")
        assert res.status_code == 200
        data = res.json()
        assert "running" in data

    def test_scheduler_pause_and_resume_routes(self):
        res = client.post("/api/scheduler/pause")
        assert res.status_code == 200
        assert res.json()["status"] == "paused"

        res = client.post("/api/scheduler/resume")
        assert res.status_code == 200
        assert res.json()["status"] == "resumed"

    def test_scheduler_run_now_route(self):
        with patch(
            "src.collectors.hackernews_collector.HackerNewsCollector.collect", return_value=[]
        ):
            res = client.post("/api/scheduler/run-now")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "completed"
            assert "result" in data
