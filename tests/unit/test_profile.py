"""
Unit tests for UserProfile and SkillProficiency models.
"""

import pytest
from pydantic import ValidationError

from src.ai.schemas import ProjectCategory
from src.models.profile import SkillProficiency, UserProfile, get_default_profile


class TestUserProfile:
    """Tests for developer profile creation and querying."""

    def test_skill_proficiency_model(self):
        skill = SkillProficiency(
            name="Python", proficiency=10, years_of_experience=6.5, is_primary=True
        )
        assert skill.name == "Python"
        assert skill.proficiency == 10
        assert skill.years_of_experience == 6.5
        assert skill.is_primary is True

    def test_skill_proficiency_validation(self):
        with pytest.raises(ValidationError):
            SkillProficiency(name="Python", proficiency=11)  # > 10

        with pytest.raises(ValidationError):
            SkillProficiency(name="Python", proficiency=0)  # < 1

    def test_user_profile_methods(self):
        profile = UserProfile(
            name="Alice",
            skills=[
                SkillProficiency(name="Python", proficiency=9),
                SkillProficiency(name="FastAPI", proficiency=10),
            ],
        )

        assert "python" in profile.get_skill_names()
        assert "fastapi" in profile.get_skill_names()
        assert profile.get_skill_proficiency("Python") == 9
        assert profile.get_skill_proficiency("FastAPI") == 10
        assert profile.get_skill_proficiency("Rust") is None

    def test_default_profile(self):
        profile = get_default_profile()
        assert profile.name == "Alex Mercer"
        assert len(profile.skills) >= 15
        assert profile.get_skill_proficiency("Python") == 10
        assert profile.get_skill_proficiency("FastAPI") == 10
        assert ProjectCategory.AI_DEVELOPMENT in profile.preferred_categories
        assert profile.minimum_hourly_rate == 50.0
