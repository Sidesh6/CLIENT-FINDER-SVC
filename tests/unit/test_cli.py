"""
Unit tests for CLI commands, argument parsing, and execution handlers.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.cli import build_parser, main
from src.database.connection import Base, engine, get_db
from src.database.models import ProjectModel
from src.models.project import Project


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield


class TestCliParser:
    """Tests for CLI argument parsing across all subcommands."""

    def test_harvest_parser_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["harvest"])
        assert args.command == "harvest"
        assert args.limit == 10
        assert args.min_score == 75.0
        assert args.dry_run is False

    def test_daemon_parser_args(self):
        parser = build_parser()
        args = parser.parse_args(["daemon", "--interval", "10", "--digest-hours", "12"])
        assert args.command == "daemon"
        assert args.interval == 10.0
        assert args.digest_hours == 12.0

    def test_pitch_parser_args(self):
        parser = build_parser()
        args = parser.parse_args(
            ["pitch", "--project-id", "42", "--angle", "FAST_DELIVERY", "--no-pricing"]
        )
        assert args.command == "pitch"
        assert args.project_id == 42
        assert args.angle == "FAST_DELIVERY"
        assert args.no_pricing is True

    def test_apply_and_apps_parser(self):
        parser = build_parser()
        args_apply = parser.parse_args(
            ["apply", "--project-id", "12", "--status", "APPLIED", "--budget", "5000"]
        )
        assert args_apply.command == "apply"
        assert args_apply.project_id == 12
        assert args_apply.budget == 5000.0

        args_apps = parser.parse_args(["apps", "--status", "WON"])
        assert args_apps.command == "apps"
        assert args_apps.status == "WON"

    def test_funnel_and_stats_parser(self):
        parser = build_parser()
        assert parser.parse_args(["stats"]).command == "stats"
        assert parser.parse_args(["funnel"]).command == "funnel"


class TestCliExecution:
    """Tests for CLI command execution handlers."""

    @patch("src.scheduler.coordinator.PipelineCoordinator.run_cycle")
    def test_cmd_harvest_execution(self, mock_run):
        mock_result = MagicMock()
        mock_result.duration_seconds = 1.5
        mock_result.collected_count = 5
        mock_result.new_projects_saved = 3
        mock_result.duplicates_skipped = 2
        mock_result.opportunities_scored = 3
        mock_result.high_priority_count = 1
        mock_result.notifications_sent = 1
        mock_result.errors = []
        mock_run.return_value = mock_result

        exit_code = main(["harvest", "--limit", "5", "--dry-run"])
        assert exit_code == 0
        mock_run.assert_called_once()

    def test_cmd_stats_execution(self):
        exit_code = main(["stats"])
        assert exit_code == 0

    def test_cmd_funnel_execution(self):
        exit_code = main(["funnel"])
        assert exit_code == 0

    def test_cmd_pitch_execution(self):
        uid = uuid.uuid4().hex[:8]
        with next(get_db()) as session:
            proj = Project(
                title=f"CLI Pitch Test Project {uid}",
                description="FastAPI backend engineer for AI system",
                source="HN",
                source_url=f"https://example.com/pitch-{uid}",
                skills=["FastAPI", "Python"],
                budget=5000.0,
            )
            pm = ProjectModel.from_pydantic(proj)
            session.add(pm)
            session.commit()
            project_id = pm.id

        exit_code = main(["pitch", "--project-id", str(project_id), "--angle", "TECHNICAL_EXPERT"])
        assert exit_code == 0

    def test_cmd_apply_and_apps_execution(self):
        uid = uuid.uuid4().hex[:8]
        with next(get_db()) as session:
            proj = Project(
                title=f"CLI Apply Test {uid}",
                description="Python developer needed",
                source="HN",
                source_url=f"https://example.com/apply-{uid}",
                skills=["Python"],
            )
            pm = ProjectModel.from_pydantic(proj)
            session.add(pm)
            session.commit()
            project_id = pm.id

        exit_code = main(["apply", "--project-id", str(project_id), "--budget", "4000"])
        assert exit_code == 0

        exit_code_apps = main(["apps"])
        assert exit_code_apps == 0

    def test_main_without_args_prints_help(self):
        exit_code = main([])
        assert exit_code == 0
