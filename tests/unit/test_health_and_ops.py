"""
Unit & Integration Tests for Production Health Probes, Metrics, Docker, and Alembic Configurations.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthProbesAndTelemetry:
    """Tests for Kubernetes/Docker Liveness, Readiness, and Prometheus-compatible metrics."""

    def test_health_liveness_probe(self, client: TestClient):
        res = client.get("/health/live")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "alive"
        assert data["service"] == "client-finder-svc"
        assert "uptime_seconds" in data
        assert "timestamp" in data

    def test_health_readiness_probe(self, client: TestClient):
        res = client.get("/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert "subsystems" in data
        assert "sql_database" in data["subsystems"]
        assert "vector_engine" in data["subsystems"]
        assert "collector_registry" in data["subsystems"]
        assert data["subsystems"]["sql_database"]["status"] == "connected"
        assert data["subsystems"]["vector_engine"]["status"] == "ready"

    def test_health_metrics_probe(self, client: TestClient):
        res = client.get("/health/metrics")
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "client-finder-svc"
        assert "uptime_seconds" in data
        assert "database" in data
        assert "vector_store" in data
        assert "collectors" in data
        assert data["vector_store"]["dimension"] == 384

    def test_general_health_route(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "database_connected" in data


class TestContainerAndComposeConfigurations:
    """Tests validating containerization specs, Docker Compose orchestration, and Alembic migrations."""

    def test_dockerfile_specification(self):
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        assert dockerfile_path.exists(), "Dockerfile must exist at repository root."

        content = dockerfile_path.read_text(encoding="utf-8")
        assert "AS builder" in content, "Dockerfile should use multi-stage build."
        assert "AS runner" in content, "Dockerfile should define production runner stage."
        assert "appuser" in content, "Dockerfile must run as unprivileged non-root user."
        assert "EXPOSE 8000" in content, "Dockerfile must expose port 8000."
        assert "HEALTHCHECK" in content, "Dockerfile must declare native healthcheck probe."

    def test_dockerignore_specification(self):
        dockerignore_path = PROJECT_ROOT / ".dockerignore"
        assert dockerignore_path.exists(), ".dockerignore must exist at repository root."

        content = dockerignore_path.read_text(encoding="utf-8")
        assert ".git" in content
        assert "__pycache__" in content
        assert ".venv" in content
        assert ".env" in content

    def test_docker_compose_development_stack(self):
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        assert compose_path.exists(), "docker-compose.yml must exist at repository root."

        content = compose_path.read_text(encoding="utf-8")
        assert "api:" in content
        assert "worker:" in content
        assert "postgres:" in content
        assert "redis:" in content
        assert "mongo:" in content
        assert "postgres_data:" in content

    def test_docker_compose_production_stack(self):
        prod_compose_path = PROJECT_ROOT / "docker-compose.prod.yml"
        assert prod_compose_path.exists(), "docker-compose.prod.yml must exist at repository root."

        content = prod_compose_path.read_text(encoding="utf-8")
        assert "restart: always" in content
        assert "resources:" in content
        assert "limits:" in content
        assert "logging:" in content

    def test_env_example_template(self):
        env_example_path = PROJECT_ROOT / ".env.example"
        assert env_example_path.exists(), ".env.example template must exist."

        content = env_example_path.read_text(encoding="utf-8")
        assert "DATABASE_URL=" in content
        assert "JWT_SECRET_KEY=" in content
        assert "POSTGRES_USER=" in content

    def test_alembic_migrations_structure(self):
        alembic_ini = PROJECT_ROOT / "alembic.ini"
        env_py = PROJECT_ROOT / "alembic" / "env.py"
        migration_001 = PROJECT_ROOT / "alembic" / "versions" / "001_initial_schema.py"

        assert alembic_ini.exists(), "alembic.ini must exist."
        assert env_py.exists(), "alembic/env.py must exist."
        assert migration_001.exists(), "Initial migration script must exist."

        mig_content = migration_001.read_text(encoding="utf-8")
        assert "001_initial_schema" in mig_content
        assert "def upgrade()" in mig_content
        assert "def downgrade()" in mig_content

    def test_github_actions_workflows(self):
        ci_workflow = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
        docker_workflow = PROJECT_ROOT / ".github" / "workflows" / "docker-publish.yml"

        assert ci_workflow.exists(), "CI workflow must exist."
        assert docker_workflow.exists(), "Docker publish workflow must exist."

        ci_content = ci_workflow.read_text(encoding="utf-8")
        assert "pytest" in ci_content
        assert "ruff check" in ci_content
        assert "mypy" in ci_content
