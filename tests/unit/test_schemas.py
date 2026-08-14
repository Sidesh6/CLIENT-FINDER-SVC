"""
Unit tests for AI requirement extraction schemas and enums.
"""

import pytest
from pydantic import ValidationError

from src.ai.schemas import (
    ExperienceLevel,
    ExtractedRequirements,
    PaymentType,
    ProjectCategory,
    ProjectComplexity,
)


class TestExtractionSchemas:
    """Tests for ExtractedRequirements and associated StrEnums."""

    def test_default_extracted_requirements(self):
        reqs = ExtractedRequirements()
        assert reqs.category == ProjectCategory.OTHER
        assert reqs.estimated_complexity == ProjectComplexity.MEDIUM
        assert reqs.project_type == PaymentType.UNKNOWN
        assert reqs.experience_level == ExperienceLevel.NOT_SPECIFIED
        assert reqs.required_skills == []
        assert reqs.budget_min is None
        assert reqs.confidence_score == 0.85

    def test_valid_custom_requirements(self):
        reqs = ExtractedRequirements(
            category=ProjectCategory.AI_DEVELOPMENT,
            required_skills=["Python", "FastAPI", "LangChain"],
            optional_skills=["Docker", "React"],
            estimated_complexity=ProjectComplexity.HIGH,
            project_type=PaymentType.FIXED_PRICE,
            experience_level=ExperienceLevel.SENIOR,
            budget_min=3000.0,
            budget_max=5000.0,
            currency="USD",
            deliverables=["Build RAG pipeline", "Deploy to AWS"],
            technical_requirements=["Must support sub-second latency"],
            risk_signals=["Fast turnaround required"],
            confidence_score=0.95,
            summary="Senior engineer needed for RAG pipeline.",
        )

        assert reqs.category == "AI Development"
        assert reqs.required_skills == ["Python", "FastAPI", "LangChain"]
        assert reqs.budget_min == 3000.0
        assert reqs.budget_max == 5000.0
        assert reqs.currency == "USD"
        assert reqs.confidence_score == 0.95

    def test_invalid_negative_budget_raises(self):
        with pytest.raises(ValidationError):
            ExtractedRequirements(budget_min=-50.0)

    def test_invalid_confidence_score_raises(self):
        with pytest.raises(ValidationError):
            ExtractedRequirements(confidence_score=1.5)

        with pytest.raises(ValidationError):
            ExtractedRequirements(confidence_score=-0.1)

    def test_json_roundtrip_serialization(self):
        reqs = ExtractedRequirements(
            category=ProjectCategory.WEB_DEVELOPMENT,
            required_skills=["Next.js", "TypeScript"],
            budget_min=1500.0,
            currency="EUR",
        )
        json_str = reqs.model_dump_json()
        restored = ExtractedRequirements.model_validate_json(json_str)

        assert restored.category == ProjectCategory.WEB_DEVELOPMENT
        assert restored.required_skills == ["Next.js", "TypeScript"]
        assert restored.budget_min == 1500.0
        assert restored.currency == "EUR"
