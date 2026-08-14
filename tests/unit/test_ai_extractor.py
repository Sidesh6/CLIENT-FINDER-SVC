"""
Unit tests for ProjectExtractor with LLM integration and heuristic fallback.
"""

from unittest.mock import MagicMock

from pydantic import HttpUrl

from src.ai.client import BaseLLMClient
from src.ai.extractor import ProjectExtractor
from src.models.project import Project


class TestProjectExtractor:
    """Tests for ProjectExtractor coordination."""

    def test_extractor_with_heuristic_default(self):
        extractor = ProjectExtractor(llm_client=None)

        raw_project = {
            "title": "Python & FastAPI Backend API",
            "description": "Looking for an expert to build REST API with PostgreSQL. Budget: $2,500.",
            "source": "Hacker News",
            "source_url": "https://news.ycombinator.com/item?id=123",
        }

        project = extractor.extract(raw_project)

        assert isinstance(project, Project)
        assert project.title == "Python & FastAPI Backend API"
        assert "Python" in project.skills
        assert "FastAPI" in project.skills
        assert project.budget == 2500.0
        assert project.currency == "USD"
        assert project.category in ("AI Development", "Web Development", "Systems & Backend")
        assert project.confidence_score is not None

    def test_extractor_with_successful_mock_llm(self):
        mock_llm = MagicMock(spec=BaseLLMClient)
        mock_llm.generate.return_value = """
        {
            "category": "AI Development",
            "required_skills": ["Python", "PyTorch", "HuggingFace"],
            "optional_skills": ["Docker"],
            "estimated_complexity": "High",
            "project_type": "Fixed Price",
            "experience_level": "Senior",
            "budget_min": 7500.0,
            "budget_max": 9000.0,
            "currency": "USD",
            "deliverables": ["Fine-tune LLM", "Create evaluation benchmark"],
            "technical_requirements": ["Model quantized to 4-bit"],
            "risk_signals": [],
            "confidence_score": 0.95,
            "summary": "Senior AI engineer for LLM fine-tuning."
        }
        """

        extractor = ProjectExtractor(llm_client=mock_llm)

        raw = {
            "title": "LLM Fine-Tuning Expert",
            "description": "Need an expert to fine-tune Llama 3.",
            "source": "Upwork",
            "source_url": "https://example.com/job/456",
        }

        project = extractor.extract(raw)

        assert mock_llm.generate.called
        assert project.category == "AI Development"
        assert "PyTorch" in project.skills
        assert "HuggingFace" in project.skills
        assert project.budget == 7500.0
        assert project.complexity == "High"
        assert project.deliverables == ["Fine-tune LLM", "Create evaluation benchmark"]
        assert project.confidence_score == 0.95

    def test_extractor_falls_back_when_llm_raises_exception(self):
        mock_llm = MagicMock(spec=BaseLLMClient)
        mock_llm.generate.side_effect = TimeoutError("Connection to LLM timed out")

        extractor = ProjectExtractor(llm_client=mock_llm)

        raw = {
            "title": "Python Web Scraping with Playwright",
            "description": "Scrape product catalog daily. Rate: $50/hr.",
            "source": "HN",
            "source_url": "https://example.com/job/789",
        }

        # Must not raise, should fall back to heuristic
        project = extractor.extract(raw)

        assert "Python" in project.skills
        assert "Playwright" in project.skills
        assert project.budget == 50.0
        assert project.category == "Automation & Scraping"

    def test_extractor_falls_back_when_llm_returns_malformed_json(self):
        mock_llm = MagicMock(spec=BaseLLMClient)
        mock_llm.generate.return_value = "Sorry, I cannot help with that."

        extractor = ProjectExtractor(llm_client=mock_llm)

        raw = {
            "title": "React Frontend Dev",
            "description": "Build Next.js landing pages.",
            "source": "HN",
            "source_url": "https://example.com/job/999",
        }

        project = extractor.extract(raw)

        assert "React" in project.skills or "Next.js" in project.skills
        assert project.category == "Web Development"

    def test_extract_from_pydantic_project_instance(self):
        extractor = ProjectExtractor(llm_client=None)

        existing = Project(
            title="Senior Go Backend Developer",
            description="Build microservices with Go, Docker, and PostgreSQL. Budget: $5,000.",
            source="Freelance",
            source_url=HttpUrl("https://example.com/go-job"),
            skills=["Docker"],  # existing skill
        )

        enriched = extractor.extract(existing)

        assert isinstance(enriched, Project)
        assert "Docker" in enriched.skills
        assert "Go" in enriched.skills or "PostgreSQL" in enriched.skills
        assert enriched.budget == 5000.0

    def test_extract_many_batch(self):
        extractor = ProjectExtractor(llm_client=None)

        batch = [
            {
                "title": "AI Project",
                "description": "Python + LangChain",
                "source": "HN",
                "source_url": "https://example.com/1",
            },
            {
                "title": "Web Project",
                "description": "Next.js + TailwindCSS",
                "source": "HN",
                "source_url": "https://example.com/2",
            },
        ]

        results = extractor.extract_many(batch)
        assert len(results) == 2
        assert isinstance(results[0], Project)
        assert isinstance(results[1], Project)
