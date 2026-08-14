"""
Unit tests for FastAPI REST API endpoints, routing, error handling, and dashboard service.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database.connection import Base, engine, get_db
from src.database.models import ProjectModel
from src.models.project import Project

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database schema is fresh for API unit tests."""
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def seed_test_project():
    """Insert a unique sample test project into the SQLite database."""
    unique_id = uuid.uuid4().hex[:8]
    with next(get_db()) as session:
        proj = Project(
            title=f"FastAPI & LangChain Microservice {unique_id}",
            description="Build scalable RAG microservice with pgvector",
            source="Hacker News",
            source_url=f"https://example.com/api-test-job-{unique_id}",
            skills=["FastAPI", "Python", "LangChain"],
            budget=4500.0,
            currency="USD",
            score=82.5,
        )
        pm = ProjectModel.from_pydantic(proj, status="NEW")
        session.add(pm)
        session.commit()
        session.refresh(pm)
        project_id = pm.id

    yield project_id


class TestHealthEndpoints:
    """Tests for system health and connectivity checks."""

    def test_get_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["version"] == "1.0.0"
        assert "total_projects" in data

    def test_get_api_health(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["database_connected"] is True


class TestProjectsEndpoints:
    """Tests for project listing, detail retrieval, and status updates."""

    def test_list_projects(self, seed_test_project):
        response = client.get("/api/projects?limit=100")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
        assert any(p["id"] == seed_test_project for p in data["items"])

    def test_get_project_by_id(self, seed_test_project):
        response = client.get(f"/api/projects/{seed_test_project}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == seed_test_project
        assert "FastAPI" in data["title"]
        assert data["score"] == 82.5

    def test_get_project_not_found(self):
        response = client.get("/api/projects/999999")
        assert response.status_code == 404

    def test_update_project_status(self, seed_test_project):
        response = client.patch(
            f"/api/projects/{seed_test_project}/status",
            json={"status": "APPLIED"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "APPLIED"

    def test_delete_project(self, seed_test_project):
        response = client.delete(f"/api/projects/{seed_test_project}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify 404 after deletion
        get_res = client.get(f"/api/projects/{seed_test_project}")
        assert get_res.status_code == 404


class TestSearchEndpoints:
    """Tests for keyword and multi-field search endpoint."""

    def test_search_by_keyword(self, seed_test_project):
        response = client.get("/api/search?q=LangChain")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any("LangChain" in p["title"] for p in data["items"])


class TestOpportunitiesEndpoints:
    """Tests for opportunity ranking, KPIs, and batch scoring."""

    def test_get_top_opportunities(self, seed_test_project):
        response = client.get("/api/opportunities/top?min_score=50.0")
        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        assert len(items) >= 1

    def test_get_opportunity_statistics(self, seed_test_project):
        response = client.get("/api/opportunities/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_projects"] >= 1
        assert "top_skills" in data
        assert "category_distribution" in data

    def test_score_all_opportunities(self, seed_test_project):
        response = client.post("/api/opportunities/score-all")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"


class TestProposalsEndpoints:
    """Tests for AI and heuristic proposal synthesis endpoints."""

    def test_generate_proposal_with_angle(self, seed_test_project):
        payload = {
            "project_id": seed_test_project,
            "pitch_angle": "FAST_DELIVERY",
            "tone": "CONFIDENT",
            "include_pricing": True,
        }
        response = client.post("/api/proposals/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "subject_line" in data
        assert "hook" in data
        assert "body" in data
        assert data["pitch_angle"] == "FAST_DELIVERY"
        assert data["quality_score"] >= 80.0

    def test_auto_generate_proposal(self, seed_test_project):
        payload = {
            "project_id": seed_test_project,
            "tone": "CONFIDENT",
            "include_pricing": True,
        }
        response = client.post("/api/proposals/auto", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "subject_line" in data
        assert data["quality_score"] >= 80.0


class TestProfileEndpoints:
    """Tests for developer profile management."""

    def test_get_profile(self):
        response = client.get("/api/profile")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "target_hourly_rate" in data

    def test_update_profile(self):
        update_payload = {
            "name": "Jane Developer",
            "title": "Principal Python Architect",
            "target_hourly_rate": 135.0,
        }
        response = client.put("/api/profile", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Jane Developer"
        assert data["target_hourly_rate"] == 135.0


class TestCollectorsEndpoints:
    """Tests for collector registry and live triggering."""

    def test_list_collectors(self):
        response = client.get("/api/collectors")
        assert response.status_code == 200
        items = response.json()
        assert len(items) >= 1
        assert items[0]["name"] == "Hacker News"

    @patch("src.collectors.hackernews_collector.HackerNewsCollector.collect")
    def test_trigger_collector(self, mock_collect):
        uid = uuid.uuid4().hex[:8]
        mock_collect.return_value = [
            {
                "title": "Frontend React & TypeScript Specialist Needed",
                "description": "Build UI dashboard for data analytics platform",
                "source": "Hacker News",
                "source_url": f"https://news.ycombinator.com/item?id={uid}",
                "skills": ["React", "TypeScript"],
            }
        ]
        response = client.post("/api/collectors/trigger?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["collected_count"] == 1


class TestWebDashboardRoot:
    """Tests for dashboard static index serving."""

    def test_serve_dashboard_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "CLIENT FINDER" in response.text or "status" in response.text
