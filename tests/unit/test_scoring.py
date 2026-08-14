"""
Unit tests for OpportunityScorer and multi-factor mathematical calculators.
"""

from datetime import UTC, datetime, timedelta

from pydantic import HttpUrl

from src.database.database import get_db_session, get_engine, init_db
from src.database.repository import OpportunityRepository, ProjectRepository
from src.models.profile import SkillProficiency, UserProfile, get_default_profile
from src.models.project import Project
from src.scoring.calculators import (
    calculate_budget_score,
    calculate_client_score,
    calculate_competition_score,
    calculate_complexity_score,
    calculate_freshness_score,
    calculate_win_probability,
)
from src.scoring.engine import OpportunityScorer
from src.scoring.schemas import ScoringRecommendation


class TestScoringCalculators:
    """Tests for individual scoring factor calculators."""

    def test_calculate_budget_score(self):
        profile = get_default_profile()  # target: $95/hr, min: $50/hr, min_fixed: $1000

        # Hourly above target
        assert calculate_budget_score(120.0, "USD", "Hourly", profile) >= 90.0
        # Hourly between min and target
        assert 70.0 <= calculate_budget_score(75.0, "USD", "Hourly", profile) <= 90.0
        # Hourly below min
        assert calculate_budget_score(30.0, "USD", "Hourly", profile) < 60.0
        # Unstated budget neutral baseline
        assert calculate_budget_score(None, None, None, profile) == 55.0

    def test_calculate_client_score_credibility_and_risks(self):
        # Good client with company name and structured spec
        good_title = "Senior Python Engineer Needed"
        good_desc = """
        Acme Corp is seeking a senior backend engineer.
        Deliverables:
        - Design REST API
        - Deploy with Docker on AWS
        Please email jobs@acmecorp.com to apply.
        """
        score_good, flags_good = calculate_client_score(good_title, good_desc, "Acme Corp", "HN")
        assert score_good >= 80.0
        assert len(flags_good) == 0

        # Risky client with equity only
        bad_title = "Co-founder Developer Wanted"
        bad_desc = "Build our entire MVP for equity only, no salary or budget available."
        score_bad, flags_bad = calculate_client_score(bad_title, bad_desc, None, "HN")
        assert score_bad <= 40.0
        assert "Equity-only or unpaid compensation structure" in flags_bad

    def test_calculate_competition_score(self):
        # Niche tech stack
        niche_score = calculate_competition_score(
            ["Python", "LangChain", "RAG", "Vector Database"], "High", "AI Development"
        )
        # Generic saturated stack
        generic_score = calculate_competition_score(
            ["WordPress", "HTML/CSS"], "Low", "Web Development"
        )

        assert niche_score > generic_score
        assert niche_score >= 80.0

    def test_calculate_complexity_score(self):
        profile = get_default_profile()
        assert calculate_complexity_score("High", profile) == 95.0
        assert calculate_complexity_score("Medium", profile) == 85.0
        assert calculate_complexity_score("Low", profile) == 55.0

    def test_calculate_freshness_score(self):
        now = datetime.now(UTC)
        recent = now - timedelta(hours=2)
        one_day = now - timedelta(hours=20)
        old = now - timedelta(days=10)

        assert calculate_freshness_score(recent) == 100.0
        assert calculate_freshness_score(one_day) == 90.0
        assert calculate_freshness_score(old) <= 40.0

    def test_calculate_win_probability(self):
        win_prob = calculate_win_probability(
            skill_score=90.0, competition_score=85.0, complexity_score=95.0
        )
        assert 85.0 <= win_prob <= 95.0


class TestOpportunityScorer:
    """Tests for composite OpportunityScorer engine."""

    def test_score_outstanding_opportunity(self):
        scorer = OpportunityScorer()

        project = Project(
            title="Senior AI Engineer (RAG & FastAPI)",
            description="""
            Anthropic Partner firm seeking an expert to build LLM RAG pipelines.
            Budget: $9,000 fixed price.
            Deliverables:
            - LangChain pipeline
            - FastAPI microservice
            Email tech@firm.com with your portfolio.
            """,
            source="Hacker News",
            source_url=HttpUrl("https://news.ycombinator.com/item?id=101"),
            client_name="AI Venture Partners",
            skills=["Python", "FastAPI", "LangChain", "RAG", "PostgreSQL"],
            category="AI Development",
            complexity="High",
            budget=9000.0,
            currency="USD",
            project_type="Fixed Price",
            project_start_date=datetime.now(UTC),
        )

        breakdown = scorer.score(project)

        assert breakdown.overall_score >= 80.0
        assert breakdown.recommendation == ScoringRecommendation.APPLY_IMMEDIATELY
        assert breakdown.skill_match_score >= 85.0
        assert breakdown.budget_score >= 85.0
        assert "Priority Target" in breakdown.explanation or "Outstanding" in breakdown.explanation

    def test_score_low_priority_opportunity(self):
        custom_profile = UserProfile(
            skills=[SkillProficiency(name="Python", proficiency=10)],
        )
        scorer = OpportunityScorer(default_profile=custom_profile)

        low_project = {
            "title": "WordPress Site Tweak",
            "description": "Fix minor CSS bug on WordPress. Budget: $20.",
            "skills": ["PHP", "WordPress"],
            "budget": 20.0,
            "project_type": "Fixed Price",
            "complexity": "Low",
        }

        breakdown = scorer.score(low_project, profile=custom_profile)

        assert breakdown.overall_score < 50.0
        assert breakdown.recommendation == ScoringRecommendation.SKIP

    def test_score_and_persist_to_database(self):
        engine = get_engine("sqlite:///:memory:")
        init_db(engine)

        with get_db_session(engine=engine) as session:
            proj_repo = ProjectRepository(session)
            project_model = proj_repo.add(
                {
                    "title": "FastAPI & Python Microservices",
                    "description": "Build high throughput API. Budget: $4,000.",
                    "source": "Hacker News",
                    "source_url": "https://example.com/fastapi-job",
                    "skills": ["Python", "FastAPI"],
                    "budget": 4000.0,
                }
            )
            assert project_model is not None
            project_id = project_model.id

            pydantic_project = project_model.to_pydantic()

            scorer = OpportunityScorer()
            opp_model = scorer.score_and_persist(
                project_id=project_id,
                project=pydantic_project,
                session=session,
            )

            assert opp_model.project_id == project_id
            assert opp_model.overall_score > 60.0
            assert opp_model.skill_match_score is not None

            # Verify sync to ProjectModel
            updated_proj = proj_repo.get_by_id(project_id)
            assert updated_proj is not None
            assert updated_proj.score == opp_model.overall_score

            # Verify retrieval via OpportunityRepository
            opp_repo = OpportunityRepository(session)
            fetched_opp = opp_repo.get_by_project_id(project_id)
            assert fetched_opp is not None
            assert fetched_opp.overall_score == opp_model.overall_score
