"""
Predictive Proposal Rate & Expected Value Optimization Engine.
Calculates price elasticity, win probability decay curves, and expected revenue yield.
"""

import math

from pydantic import BaseModel, Field

from src.models.profile import UserProfile, get_default_profile


class RateOptimizationRequest(BaseModel):
    """Inbound request payload for pricing optimization analysis."""

    project_title: str
    match_score: float = Field(
        default=80.0, ge=0.0, le=100.0, description="Overall opportunity match score"
    )
    estimated_hours: float = Field(
        default=40.0, ge=1.0, description="Estimated total project hours"
    )
    client_budget: float | None = Field(default=None, description="Stated client budget limit")
    target_hourly_rate: float = Field(
        default=95.0, ge=10.0, description="Developer base hourly rate"
    )


class RateStrategyPoint(BaseModel):
    """Specific commercial pricing tier with projected win rate and expected yield."""

    strategy_name: str
    hourly_rate: float
    total_project_estimate: float
    win_probability_pct: float
    expected_yield_value: float
    recommendation_summary: str


class RateOptimizationResult(BaseModel):
    """Complete price elasticity and Expected Value optimization result."""

    project_title: str
    estimated_hours: float
    client_budget: float | None
    optimal_recommended_rate: float
    strategies: list[RateStrategyPoint]
    curve_data_points: list[dict[str, float]]


class RateOptimizer:
    """
    Computes win probability decay curves across rate tiers and identifies the expected-value maximizing quote.
    """

    def __init__(self, default_profile: UserProfile | None = None):
        self.default_profile = default_profile or get_default_profile()

    def optimize(
        self,
        req: RateOptimizationRequest,
        profile: UserProfile | None = None,
    ) -> RateOptimizationResult:
        """
        Produce pricing tiers and EV curves for a specific opportunity.
        """
        user_prof = profile or self.default_profile
        base_rate = req.target_hourly_rate or user_prof.target_hourly_rate or 95.0
        hours = req.estimated_hours
        score = req.match_score
        client_bud = req.client_budget

        # Base win probability scaled from match score (e.g. score 80 -> 40% base win prob)
        base_win_prob = max(0.15, min(0.85, (score / 100.0) * 0.55))

        # Generate curve data points across rate multiplier 0.6x to 1.8x
        curve_points: list[dict[str, float]] = []
        max_ev = 0.0
        optimal_rate = base_rate

        for mult in [0.6, 0.75, 0.85, 1.0, 1.15, 1.3, 1.5, 1.75]:
            r = round(base_rate * mult, 0)
            total_price = r * hours

            # Win probability decays as rate rises
            decay_factor = 1.0 / (1.0 + math.exp(2.5 * (mult - 1.0)))

            # If client has explicit budget limit, penalize heavily when total_price exceeds budget
            if client_bud and client_bud > 0 and total_price > client_bud:
                budget_penalty = math.exp(-2.0 * ((total_price - client_bud) / client_bud))
                decay_factor *= max(0.1, budget_penalty)

            win_prob = round(base_win_prob * decay_factor * 100.0, 1)
            ev = round((win_prob / 100.0) * total_price, 2)

            curve_points.append(
                {
                    "rate": r,
                    "total_price": total_price,
                    "win_probability": win_prob,
                    "expected_yield": ev,
                }
            )

            if ev > max_ev:
                max_ev = ev
                optimal_rate = r

        # Extract 3 canonical strategy points
        # 1. MAX WIN RATE (0.75x base rate)
        max_win_pt = curve_points[1]
        p1 = RateStrategyPoint(
            strategy_name="MAX_WIN_RATE",
            hourly_rate=max_win_pt["rate"],
            total_project_estimate=max_win_pt["total_price"],
            win_probability_pct=max_win_pt["win_probability"],
            expected_yield_value=max_win_pt["expected_yield"],
            recommendation_summary="Lowest friction price point. Ideal when building pipeline volume or acquiring new client references.",
        )

        # 2. OPTIMAL EXPECTED VALUE (EV maximizing point)
        opt_pt = next((pt for pt in curve_points if pt["rate"] == optimal_rate), curve_points[3])
        p2 = RateStrategyPoint(
            strategy_name="OPTIMAL_EV",
            hourly_rate=opt_pt["rate"],
            total_project_estimate=opt_pt["total_price"],
            win_probability_pct=opt_pt["win_probability"],
            expected_yield_value=opt_pt["expected_yield"],
            recommendation_summary="Statistically maximizes expected total dollar return factoring in win probability.",
        )

        # 3. PREMIUM ANCHOR (1.3x base rate)
        prem_pt = curve_points[5]
        p3 = RateStrategyPoint(
            strategy_name="PREMIUM_ANCHOR",
            hourly_rate=prem_pt["rate"],
            total_project_estimate=prem_pt["total_price"],
            win_probability_pct=prem_pt["win_probability"],
            expected_yield_value=prem_pt["expected_yield"],
            recommendation_summary="High-margin quote positioning developer as premier architectural authority with turnkey delivery.",
        )

        return RateOptimizationResult(
            project_title=req.project_title,
            estimated_hours=hours,
            client_budget=client_bud,
            optimal_recommended_rate=optimal_rate,
            strategies=[p1, p2, p3],
            curve_data_points=curve_points,
        )
