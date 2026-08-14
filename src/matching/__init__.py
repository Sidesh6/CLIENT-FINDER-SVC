"""
Matching package for Client Finder service.
Provides user profile matching, skill taxonomy, and explainable scoring.
"""

from src.matching.matcher import SkillMatcher
from src.matching.schemas import SkillMatchResult
from src.matching.taxonomy import (
    RELATED_SKILLS_GRAPH,
    SYNONYM_MAP,
    get_implied_skills,
    normalize_skill_name,
)

__all__ = [
    "SkillMatcher",
    "SkillMatchResult",
    "normalize_skill_name",
    "get_implied_skills",
    "SYNONYM_MAP",
    "RELATED_SKILLS_GRAPH",
]
