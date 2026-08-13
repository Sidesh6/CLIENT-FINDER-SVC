import pytest
from pydantic import ValidationError

from src.models.project import Project


def test_valid_project():
    project = Project(
        title="AI Chatbot",
        description="Build an AI chatbot.",
        source="Example",
        source_url="https://example.com/project/1",
        budget=1000,
        currency="USD",
        skills=["Python", "FastAPI"],
    )

    assert project.title == "AI Chatbot"
    assert project.budget == 1000
    assert "Python" in project.skills


def test_project_requires_title():
    with pytest.raises(ValidationError):
        Project(
            title="",
            description="Build an AI chatbot.",
            source="Example",
            source_url="https://example.com/project/1",
        )


def test_budget_cannot_be_negative():
    with pytest.raises(ValidationError):
        Project(
            title="AI Chatbot",
            description="Build an AI chatbot.",
            source="Example",
            source_url="https://example.com/project/1",
            budget=-500,
        )


def test_score_must_be_between_zero_and_hundred():
    with pytest.raises(ValidationError):
        Project(
            title="AI Chatbot",
            description="Build an AI chatbot.",
            source="Example",
            source_url="https://example.com/project/1",
            score=150,
        )
