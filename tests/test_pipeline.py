"""Tests for the project discovery pipeline."""

from unittest.mock import MagicMock

import pytest

from src.ai.extractor import ProjectExtractor
from src.collectors.example_collector import ExampleCollector
from src.collectors.hackernews_collector import HackerNewsCollector
from src.models.project import Project
from src.processors.cleaner import ProjectCleaner


class TestProjectCleaner:
    """Tests for ProjectCleaner."""

    def test_clean_strips_whitespace(self):
        """Test that cleaner strips whitespace from string fields."""
        cleaner = ProjectCleaner()
        raw_project = {
            "title": "  Test Project  ",
            "description": "  Description with spaces  ",
            "source": "  Source  ",
            "source_url": "https://example.com",
            "client_name": "  Client  ",
            "budget": 1000,
            "currency": "USD",
            "project_type": "Development",
            "skills": ["Python", "FastAPI"],
        }

        cleaned = cleaner.clean(raw_project)

        assert cleaned["title"] == "Test Project"
        assert cleaned["description"] == "Description with spaces"
        assert cleaned["source"] == "Source"
        assert cleaned["client_name"] == "Client"

    def test_clean_non_string_fields_unchanged(self):
        """Test that non-string fields are not modified."""
        cleaner = ProjectCleaner()
        raw_project = {
            "title": "Test",
            "description": "Desc",
            "source": "Source",
            "source_url": "https://example.com",
            "budget": 1000,
            "skills": ["Python", "FastAPI"],
        }

        cleaned = cleaner.clean(raw_project)

        assert cleaned["budget"] == 1000
        assert cleaned["skills"] == ["Python", "FastAPI"]

    def test_clean_many(self):
        """Test cleaning multiple projects."""
        cleaner = ProjectCleaner()
        raw_projects = [
            {
                "title": "  Project 1  ",
                "description": "Desc",
                "source": "S",
                "source_url": "https://ex.com",
            },
            {
                "title": "  Project 2  ",
                "description": "Desc",
                "source": "S",
                "source_url": "https://ex.com",
            },
        ]

        cleaned = cleaner.clean_many(raw_projects)

        assert len(cleaned) == 2
        assert cleaned[0]["title"] == "Project 1"
        assert cleaned[1]["title"] == "Project 2"


class TestProjectExtractor:
    """Tests for ProjectExtractor."""

    def test_extract_creates_valid_project(self):
        """Test that extractor creates a valid Project model."""
        extractor = ProjectExtractor()
        cleaned_project = {
            "title": "AI Chatbot Development",
            "description": "Build an AI chatbot using Python, FastAPI and RAG.",
            "source": "Example Source",
            "source_url": "https://example.com/project/123",
            "client_name": "Example Client",
            "budget": 2000,
            "currency": "USD",
            "project_type": "AI Development",
            "skills": ["Python", "FastAPI", "RAG"],
        }

        project = extractor.extract(cleaned_project)

        assert isinstance(project, Project)
        assert project.title == "AI Chatbot Development"
        assert project.description == "Build an AI chatbot using Python, FastAPI and RAG."
        assert project.source == "Example Source"
        assert str(project.source_url) == "https://example.com/project/123"
        assert project.client_name == "Example Client"
        assert project.budget == 2000
        assert project.currency == "USD"
        assert project.project_type == "AI Development"
        assert project.skills == ["Python", "FastAPI", "RAG"]
        assert project.score is None

    def test_extract_with_optional_fields_none(self):
        """Test extraction with optional fields as None."""
        extractor = ProjectExtractor()
        cleaned_project = {
            "title": "Minimal Project",
            "description": "A minimal project",
            "source": "Test",
            "source_url": "https://test.com",
        }

        project = extractor.extract(cleaned_project)

        assert project.title == "Minimal Project"
        assert project.client_name is None
        assert project.budget is None
        assert project.currency is None
        assert project.project_type is None
        assert project.skills == []
        assert project.project_start_date is None
        assert project.project_end_date is None
        assert project.score is None


class TestProjectModel:
    """Tests for Project Pydantic model validation."""

    def test_valid_project(self):
        """Test creating a valid project."""
        project = Project(
            title="Test",
            description="Description",
            source="Source",
            source_url="https://example.com",
        )
        assert project.title == "Test"

    def test_invalid_empty_title(self):
        """Test that empty title raises validation error."""
        with pytest.raises(ValueError):
            Project(
                title="",
                description="Description",
                source="Source",
                source_url="https://example.com",
            )

    def test_invalid_url(self):
        """Test that invalid URL raises validation error."""
        with pytest.raises(ValueError):
            Project(
                title="Test",
                description="Description",
                source="Source",
                source_url="not-a-url",
            )

    def test_score_validation(self):
        """Test score validation bounds."""
        # Valid scores
        project = Project(
            title="Test",
            description="Desc",
            source="S",
            source_url="https://ex.com",
            score=50,
        )
        assert project.score == 50

        # Invalid: negative score
        with pytest.raises(ValueError):
            Project(
                title="Test",
                description="Desc",
                source="S",
                source_url="https://ex.com",
                score=-1,
            )

        # Invalid: score > 100
        with pytest.raises(ValueError):
            Project(
                title="Test",
                description="Desc",
                source="S",
                source_url="https://ex.com",
                score=101,
            )


class TestEndToEndPipeline:
    """Tests for the complete discovery pipeline: Collector -> Cleaner -> Extractor -> Project."""

    def test_example_collector_pipeline(self):
        collector = ExampleCollector()
        cleaner = ProjectCleaner()
        extractor = ProjectExtractor()

        raw_projects = collector.collect()
        assert len(raw_projects) > 0

        cleaned_projects = cleaner.clean_many(raw_projects)
        assert len(cleaned_projects) == len(raw_projects)

        validated_projects = [extractor.extract(p) for p in cleaned_projects]
        assert len(validated_projects) == len(raw_projects)
        for proj in validated_projects:
            assert isinstance(proj, Project)
            assert proj.title
            assert proj.source == "Example Source"
            assert str(proj.source_url).startswith("https://")

    def test_hackernews_collector_pipeline(self):
        mock_http = MagicMock()
        mock_http.get_json.return_value = {
            "hits": [
                {
                    "objectID": "55555",
                    "author": "hire_founder",
                    "comment_text": "<p>SEEKING FREELANCER: Need a Python + LangChain engineer to build a project scoring engine.</p>",
                }
            ]
        }

        collector = HackerNewsCollector(http_client=mock_http, search_query="SEEKING FREELANCER")
        cleaner = ProjectCleaner()
        extractor = ProjectExtractor()

        raw_projects = collector.collect()
        assert len(raw_projects) == 1

        cleaned_projects = cleaner.clean_many(raw_projects)
        validated_projects = [extractor.extract(p) for p in cleaned_projects]

        assert len(validated_projects) == 1
        proj = validated_projects[0]
        assert isinstance(proj, Project)
        assert proj.source == "Hacker News"
        assert proj.client_name == "hire_founder"
        assert "LangChain" in proj.description
        assert str(proj.source_url) == "https://news.ycombinator.com/item?id=55555"
