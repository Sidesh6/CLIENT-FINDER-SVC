"""
Tests for base collector mechanics and source metadata.
"""

from typing import Any

from src.collectors.base_collector import BaseCollector


class MockDirectFreelanceCollector(BaseCollector):
    """Test collector simulating direct freelance client acquisition."""

    def __init__(self):
        super().__init__("Direct Client Source")

    def collect(self) -> list[dict[str, Any]]:
        return [
            {
                "title": "FastAPI & AI Automation MVP",
                "description": "Founder seeking contract Python developer to build RAG pipeline.",
                "source": self.source_name,
                "source_url": "https://freelance-platform.org/projects/123",
                "client_name": "Direct Client",
                "budget": 3500,
                "currency": "USD",
                "project_type": "Fixed Milestone",
                "skills": ["Python", "FastAPI", "RAG"],
            }
        ]


def test_base_collector_returns_projects():
    collector = MockDirectFreelanceCollector()
    projects = collector.collect()
    assert len(projects) == 1
    assert projects[0]["title"] == "FastAPI & AI Automation MVP"


def test_base_collector_returns_required_fields():
    collector = MockDirectFreelanceCollector()
    projects = collector.collect()
    project = projects[0]

    assert "title" in project
    assert "description" in project
    assert "source" in project
    assert "source_url" in project
    assert project["budget"] == 3500


def test_base_collector_source_name():
    collector = MockDirectFreelanceCollector()
    assert collector.get_source_name() == "Direct Client Source"
