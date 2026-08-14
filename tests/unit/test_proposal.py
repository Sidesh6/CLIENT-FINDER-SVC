"""
Unit tests for AI proposal generation, prompt builders, heuristics, and pitch angles.
"""

import json
from unittest.mock import MagicMock

from pydantic import HttpUrl

from src.models.profile import SkillProficiency, UserProfile, get_default_profile
from src.models.project import Project
from src.proposal.generator import ProposalGenerator
from src.proposal.heuristic import HeuristicProposalGenerator
from src.proposal.prompts import build_proposal_prompt
from src.proposal.schemas import PitchAngle, ProposalTone


class TestProposalSchemas:
    """Tests for proposal models and pitch angle enums."""

    def test_pitch_angles_enum(self):
        assert PitchAngle.TECHNICAL_EXPERT == "TECHNICAL_EXPERT"
        assert PitchAngle.FAST_DELIVERY == "FAST_DELIVERY"
        assert PitchAngle.VALUE_ROI == "VALUE_ROI"
        assert PitchAngle.PORTFOLIO_PROOF == "PORTFOLIO_PROOF"
        assert PitchAngle.CONSULTATIVE_ADVISOR == "CONSULTATIVE_ADVISOR"


class TestHeuristicProposalGenerator:
    """Tests for rule-based proposal synthesis across all 5 pitch angles."""

    def test_generate_technical_expert(self):
        gen = HeuristicProposalGenerator()
        profile = get_default_profile()

        project = Project(
            title="FastAPI & LangChain Microservice",
            description="Build RAG backend on AWS",
            source="Hacker News",
            source_url=HttpUrl("https://example.com/job"),
            skills=["Python", "FastAPI", "LangChain", "PostgreSQL"],
            budget=5000.0,
        )

        res = gen.generate(project, profile, pitch_angle=PitchAngle.TECHNICAL_EXPERT)

        assert "Senior" in res.subject_line or "FastAPI" in res.subject_line
        assert "production-grade" in res.hook or "FastAPI" in res.hook
        assert "latency" in res.body or "architecture" in res.body
        assert len(res.relevant_projects) >= 2
        assert "USD 5,000" in (res.pricing_quote or "")
        assert res.quality_score >= 80.0

    def test_generate_fast_delivery(self):
        gen = HeuristicProposalGenerator()
        profile = get_default_profile()

        project = {
            "title": "Need urgent MVP in React & Python",
            "description": "Urgent timeline needed in 7 days",
            "skills": ["Python", "React"],
            "budget": 3000.0,
        }

        res = gen.generate(project, profile, pitch_angle=PitchAngle.FAST_DELIVERY)

        assert "Immediate Availability" in res.subject_line or "Quick" in res.subject_line
        assert "immediate availability" in res.hook or "MVP" in res.hook
        assert "Day 1-2" in res.body
        assert "start immediately" in res.call_to_action.lower()

    def test_generate_value_roi(self):
        gen = HeuristicProposalGenerator()
        profile = get_default_profile()

        project = {
            "title": "Automate Manual Data Processing",
            "description": "Cut operational costs and streamline data flow",
            "skills": ["Python", "SQL"],
            "budget": 8000.0,
        }

        res = gen.generate(project, profile, pitch_angle=PitchAngle.VALUE_ROI)

        assert "ROI" in res.subject_line or "High-ROI" in res.subject_line
        assert "operational overhead" in res.hook or "performance" in res.hook
        assert "cloud costs" in res.body or "velocity" in res.body

    def test_generate_consultative_advisor(self):
        gen = HeuristicProposalGenerator()
        profile = get_default_profile()

        project = {
            "title": "Architecture Redesign for SaaS",
            "description": "Evaluate migration options",
            "skills": ["Python", "PostgreSQL"],
        }

        res = gen.generate(project, profile, pitch_angle=PitchAngle.CONSULTATIVE_ADVISOR)

        assert "Architectural" in res.subject_line or "Discovery" in res.subject_line
        assert (
            "discovery" in res.call_to_action.lower() or "brainstorm" in res.call_to_action.lower()
        )


class TestPromptBuilder:
    """Tests for dynamic prompt compilation."""

    def test_build_proposal_prompt(self):
        profile = UserProfile(
            name="Jane Doe",
            title="Senior AI Engineer",
            skills=[SkillProficiency(name="Python", proficiency=10)],
            target_hourly_rate=120.0,
        )

        project = Project(
            title="LLM Vector Indexing",
            description="Build scalable RAG",
            source="HN",
            source_url=HttpUrl("https://example.com/rag"),
            skills=["Python", "Vector Database"],
            budget=6000.0,
        )

        prompt = build_proposal_prompt(
            project=project,
            profile=profile,
            pitch_angle=PitchAngle.TECHNICAL_EXPERT,
            tone=ProposalTone.CONFIDENT,
        )

        assert "Target Project Opportunity:" in prompt
        assert "Jane Doe" in prompt
        assert "Senior AI Engineer" in prompt
        assert "$120/hr" in prompt
        assert "TECHNICAL_EXPERT" in prompt


class TestProposalGenerator:
    """Tests for ProposalGenerator orchestration and LLM mock handling."""

    def test_auto_select_pitch_angle(self):
        gen = ProposalGenerator(llm_client=None)

        # Urgent project
        urgent_proj = {"title": "Urgent fix needed ASAP", "description": "Need fast turnaround"}
        assert gen.auto_select_pitch_angle(urgent_proj) == PitchAngle.FAST_DELIVERY

        # AI high tech project
        ai_proj = {
            "title": "Build LangChain RAG pipeline",
            "category": "AI Development",
            "skills": ["LangChain", "RAG"],
        }
        assert gen.auto_select_pitch_angle(ai_proj) == PitchAngle.TECHNICAL_EXPERT

        # High budget project
        roi_proj = {
            "title": "Enterprise Data Automation",
            "budget": 12000.0,
            "description": "Maximize ROI",
        }
        assert gen.auto_select_pitch_angle(roi_proj) == PitchAngle.VALUE_ROI

    def test_generator_with_mock_llm_success(self):
        mock_llm = MagicMock()
        mock_payload = {
            "subject_line": "AI Engineer for FastAPI RAG Microservice",
            "hook": "I reviewed your project and have built production RAG systems with LangChain and FastAPI.",
            "body": "My approach leverages async FastAPI endpoints with pgvector indexing to achieve sub-50ms latency.",
            "relevant_projects": [
                "Built enterprise RAG pipeline handling 100k queries/day",
                "Deployed FastAPI microservice with 99.9% uptime",
            ],
            "call_to_action": "Let's connect for a 15-minute architecture call tomorrow.",
            "pricing_quote": "$95/hr",
            "full_proposal_text": "Custom LLM proposal content here.",
        }
        mock_llm.generate.return_value = f"```json\n{json.dumps(mock_payload)}\n```"

        gen = ProposalGenerator(llm_client=mock_llm)
        project = Project(
            title="FastAPI AI Engineer",
            description="Build RAG system",
            source="HN",
            source_url=HttpUrl("https://example.com"),
            skills=["FastAPI", "Python"],
        )

        res = gen.generate_for_project(project)
        assert res.subject_line == "AI Engineer for FastAPI RAG Microservice"
        assert "sub-50ms latency" in res.body
        assert res.quality_score >= 85.0
        mock_llm.generate.assert_called_once()

    def test_generator_falls_back_when_llm_errors(self):
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = RuntimeError("LLM API Rate Limit")

        gen = ProposalGenerator(llm_client=mock_llm)
        project = Project(
            title="FastAPI AI Engineer",
            description="Build RAG system",
            source="HN",
            source_url=HttpUrl("https://example.com"),
            skills=["FastAPI", "Python"],
        )

        # Should not raise; falls back gracefully to Heuristic generator
        res = gen.generate_for_project(project)
        assert res is not None
        assert "FastAPI" in res.hook or "Python" in res.hook
        assert len(res.relevant_projects) >= 2
