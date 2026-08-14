"""
Endpoints for managing developer profile, target compensation, and skill proficiencies.
"""

from fastapi import APIRouter

from src.api.schemas import UserProfileUpdateRequest
from src.models.profile import SkillProficiency, UserProfile, get_default_profile

router = APIRouter(prefix="/api/profile", tags=["Profile"])

# Active in-memory profile initialized from default profile
_ACTIVE_PROFILE: UserProfile = get_default_profile()


def get_current_active_profile() -> UserProfile:
    """Return active runtime profile instance."""
    global _ACTIVE_PROFILE
    return _ACTIVE_PROFILE


@router.get("", response_model=UserProfile)
def get_profile() -> UserProfile:
    """
    Retrieve the current developer profile configuration.
    """
    return get_current_active_profile()


@router.put("", response_model=UserProfile)
def update_profile(payload: UserProfileUpdateRequest) -> UserProfile:
    """
    Update developer profile parameters, compensation targets, or skill proficiencies.
    """
    global _ACTIVE_PROFILE
    current = _ACTIVE_PROFILE

    new_skills = current.skills
    if payload.skills is not None:
        new_skills = [
            SkillProficiency(
                name=s.get("name", ""),
                proficiency=int(s.get("proficiency", 8)),
                category=s.get("category"),
                years_experience=float(s.get("years_experience", 2.0)),
            )
            for s in payload.skills
            if s.get("name")
        ]

    _ACTIVE_PROFILE = UserProfile(
        name=payload.name if payload.name is not None else current.name,
        title=payload.title if payload.title is not None else current.title,
        bio=payload.bio if payload.bio is not None else current.bio,
        target_hourly_rate=(
            payload.target_hourly_rate
            if payload.target_hourly_rate is not None
            else current.target_hourly_rate
        ),
        minimum_hourly_rate=(
            payload.minimum_hourly_rate
            if payload.minimum_hourly_rate is not None
            else current.minimum_hourly_rate
        ),
        preferred_categories=(
            payload.preferred_categories
            if payload.preferred_categories is not None
            else current.preferred_categories
        ),
        skills=new_skills,
    )

    return _ACTIVE_PROFILE
