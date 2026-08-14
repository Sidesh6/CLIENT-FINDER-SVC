"""
Market Intelligence, Skill ROI, and Proposal Pricing Optimization REST Endpoints.
"""

from fastapi import APIRouter

from src.analytics.intelligence import (
    MarketIntelligenceEngine,
    MarketOverview,
    SkillMarketMetrics,
    UpskillRecommendation,
)
from src.analytics.rate_optimizer import (
    RateOptimizationRequest,
    RateOptimizationResult,
    RateOptimizer,
)
from src.api.routes.profile import get_current_active_profile

router = APIRouter(prefix="/api/market", tags=["Market Intelligence & Pricing Optimization"])


@router.get("/overview", response_model=MarketOverview)
def get_market_overview() -> MarketOverview:
    """
    Retrieve macroeconomic overview of active freelance market volume, top paying skills, and source distribution.
    """
    profile = get_current_active_profile()
    engine = MarketIntelligenceEngine(default_profile=profile)
    return engine.get_market_overview()


@router.get("/skills/roi", response_model=list[SkillMarketMetrics])
def get_skills_roi_ranking() -> list[SkillMarketMetrics]:
    """
    Retrieve ranked list of technologies sorted by market demand, average contract budgets, and rate benchmarks.
    """
    profile = get_current_active_profile()
    engine = MarketIntelligenceEngine(default_profile=profile)
    return engine.get_skill_roi_ranking()


@router.get("/recommendations/upskill", response_model=list[UpskillRecommendation])
def get_upskill_recommendations() -> list[UpskillRecommendation]:
    """
    Generate personalized high-yield upskilling suggestions based on synergy with the developer's verified skills.
    """
    profile = get_current_active_profile()
    engine = MarketIntelligenceEngine(default_profile=profile)
    return engine.get_upskill_recommendations(profile=profile)


@router.post("/optimize-rate", response_model=RateOptimizationResult)
def optimize_proposal_rate(req: RateOptimizationRequest) -> RateOptimizationResult:
    """
    Compute price elasticity curves and recommend Expected Value maximizing proposal quote for an opportunity.
    """
    profile = get_current_active_profile()
    optimizer = RateOptimizer(default_profile=profile)
    return optimizer.optimize(req, profile=profile)
