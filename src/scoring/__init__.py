"""
Scoring package for Client Finder service.
Provides multi-factor opportunity scoring, win probability estimation, and recommendations.
"""

from src.scoring.calculators import (
    calculate_budget_score,
    calculate_client_score,
    calculate_competition_score,
    calculate_complexity_score,
    calculate_freshness_score,
    calculate_win_probability,
)
from src.scoring.engine import OpportunityScorer
from src.scoring.schemas import OpportunityScoreBreakdown, ScoringRecommendation

__all__ = [
    "OpportunityScorer",
    "OpportunityScoreBreakdown",
    "ScoringRecommendation",
    "calculate_budget_score",
    "calculate_client_score",
    "calculate_competition_score",
    "calculate_complexity_score",
    "calculate_freshness_score",
    "calculate_win_probability",
]
