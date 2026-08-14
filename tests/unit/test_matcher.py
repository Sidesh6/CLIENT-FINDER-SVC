"""
Unit tests for SkillMatcher matching algorithm and ranking.
"""

from pydantic import HttpUrl

from src.ai.schemas import ProjectCategory
from src.matching.matcher import SkillMatcher
from src.models.profile import SkillProficiency, UserProfile
from src.models.project import Project


class TestSkillMatcher:
    """Tests for SkillMatcher engine."""

    def test_perfect_skill_match(self):
        matcher = SkillMatcher()

        project = Project(
            title="Senior Python & FastAPI AI Engineer",
            description="Build RAG chatbot with FastAPI, LangChain, and PostgreSQL. Budget: $5,000.",
            source="Hacker News",
            source_url=HttpUrl("https://example.com/job1"),
            skills=["Python", "FastAPI", "LangChain", "PostgreSQL"],
            category="AI Development",
            budget=5000.0,
        )

        result = matcher.match(project)

        assert result.match_score >= 90.0
        assert result.is_strong_match is True
        assert len(result.matched_skills) == 4
        assert len(result.missing_skills) == 0
        assert result.category_match is True
        assert result.budget_fit is True
        assert "Outstanding match" in result.explanation or "Strong" in result.explanation

    def test_synonym_and_implied_skill_matching(self):
        custom_profile = UserProfile(
            name="Bob",
            skills=[
                SkillProficiency(name="FastAPI", proficiency=10, is_primary=True),
                SkillProficiency(name="React", proficiency=9, is_primary=True),
            ],
        )
        matcher = SkillMatcher(default_profile=custom_profile)

        # Project requires "Python" (implied by FastAPI) and "ReactJS" (synonym of React)
        raw_dict = {
            "title": "Fullstack Developer",
            "skills": ["python", "reactjs"],
            "category": "Web Development",
            "budget": 3000.0,
        }

        result = matcher.match(raw_dict, profile=custom_profile)

        assert "React" in result.matched_skills
        assert "Python" in result.implied_skills or "Python" in result.matched_skills
        assert result.match_score >= 70.0

    def test_missing_skills_penalty(self):
        custom_profile = UserProfile(
            name="Alice",
            skills=[SkillProficiency(name="Python", proficiency=9)],
            preferred_categories=[ProjectCategory.SYSTEMS_BACKEND],
        )
        matcher = SkillMatcher(default_profile=custom_profile)

        project = Project(
            title="C++ & Rust Systems Engineer",
            description="High performance systems in C++, Rust, and Assembly.",
            source="HN",
            source_url=HttpUrl("https://example.com/job2"),
            skills=["C++", "Rust"],
            category="Systems & Backend",
        )

        result = matcher.match(project, profile=custom_profile)

        assert len(result.missing_skills) == 2
        assert "C++" in result.missing_skills
        assert "Rust" in result.missing_skills
        assert result.match_score < 40.0
        assert result.is_strong_match is False
        assert "Missing required skills" in result.explanation

    def test_category_preference_effect(self):
        custom_profile = UserProfile(
            name="Carol",
            skills=[SkillProficiency(name="Python", proficiency=9)],
            preferred_categories=[ProjectCategory.AI_DEVELOPMENT],
        )
        matcher = SkillMatcher(default_profile=custom_profile)

        proj_ai = {"skills": ["Python"], "category": "AI Development"}
        proj_other = {"skills": ["Python"], "category": "Mobile Development"}

        res_ai = matcher.match(proj_ai, profile=custom_profile)
        res_other = matcher.match(proj_other, profile=custom_profile)

        assert res_ai.match_score > res_other.match_score
        assert res_ai.category_match is True
        assert res_other.category_match is False

    def test_budget_fit_threshold(self):
        profile = UserProfile(
            minimum_hourly_rate=60.0,
            minimum_fixed_budget=2000.0,
            skills=[SkillProficiency(name="Python", proficiency=10)],
        )
        matcher = SkillMatcher(default_profile=profile)

        # Below hourly rate
        low_hourly = {"skills": ["Python"], "budget": 30.0, "project_type": "Hourly"}
        res_low = matcher.match(low_hourly, profile=profile)
        assert res_low.budget_fit is False

        # Above hourly rate
        good_hourly = {"skills": ["Python"], "budget": 80.0, "project_type": "Hourly"}
        res_good = matcher.match(good_hourly, profile=profile)
        assert res_good.budget_fit is True

    def test_filter_and_rank_batch(self):
        matcher = SkillMatcher()

        projects = [
            Project(
                title="PHP WordPress Dev",
                description="WordPress maintenance",
                source="HN",
                source_url=HttpUrl("https://example.com/1"),
                skills=["PHP"],
            ),
            Project(
                title="Lead AI Engineer (RAG & Python)",
                description="Build enterprise RAG pipelines",
                source="HN",
                source_url=HttpUrl("https://example.com/2"),
                skills=["Python", "FastAPI", "RAG", "LangChain", "PostgreSQL"],
                category="AI Development",
                budget=8000.0,
            ),
            Project(
                title="Next.js Frontend",
                description="Build landing pages in Next.js & TailwindCSS",
                source="HN",
                source_url=HttpUrl("https://example.com/3"),
                skills=["Next.js", "TailwindCSS"],
                category="Web Development",
            ),
        ]

        ranked = matcher.filter_and_rank(projects, min_match_score=40.0)

        assert len(ranked) >= 2
        # Top opportunity should be the Lead AI Engineer
        top_project, top_result = ranked[0]
        assert "Lead AI Engineer" in top_project.title
        assert top_result.match_score >= 85.0
        # Second should have higher score than third
        assert ranked[0][1].match_score >= ranked[1][1].match_score
