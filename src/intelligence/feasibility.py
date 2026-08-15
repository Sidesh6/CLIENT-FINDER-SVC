"""
Budget Feasibility & Scope-Creep Predictor Engine.
Evaluates requested technical complexity against offered budgets and recommends counter-anchors.
"""

import logging

from src.intelligence.schemas import (
    BudgetFeasibilityRequest,
    BudgetFeasibilityResult,
    FeasibilityRating,
)
from src.models.profile import UserProfile, get_default_profile

logger = logging.getLogger("BudgetFeasibilityAnalyzer")


class BudgetFeasibilityAnalyzer:
    """
    Evaluates scope complexity against commercial pricing expectations and warns against severe underbudgeting.
    """

    def __init__(self, default_profile: UserProfile | None = None):
        self.default_profile = default_profile or get_default_profile()

    def evaluate_feasibility(
        self,
        req: BudgetFeasibilityRequest,
        profile: UserProfile | None = None,
    ) -> BudgetFeasibilityResult:
        """
        Estimate fair market engineering effort and compare with proposed budget.
        """
        user_prof = profile or self.default_profile
        rate = user_prof.target_hourly_rate or 95.0
        text = f"{req.project_title} {req.project_description}".strip()
        lower_text = text.lower()
        skills = req.target_skills or ["Python", "FastAPI"]

        # 1. Estimate Base Engineering Hours based on Functional Complexity
        hours_min, hours_max = self._estimate_engineering_hours(lower_text, skills)
        avg_hours = (hours_min + hours_max) / 2.0

        fair_market_budget = round(avg_hours * rate, 2)
        proposed = req.proposed_budget

        # 2. Compute Variance Percentage
        variance = ((proposed - fair_market_budget) / fair_market_budget) * 100.0
        variance = round(variance, 1)

        # 3. Classify Feasibility Rating and Score
        if variance >= -20.0:
            rating = FeasibilityRating.REALISTIC
            score = min(100.0, 85.0 + (variance * 0.2))
            creep_risk = "LOW"
            recs = [
                "Budget aligns comfortably with standard market engineering effort.",
                "Proceed with standard 3-phase milestone deliverables.",
            ]
            counter_budget = proposed
        elif -45.0 <= variance < -20.0:
            rating = FeasibilityRating.SLIGHTLY_UNDERBUDGETED
            score = 72.0
            creep_risk = "MODERATE"
            recs = [
                "Recommend slight scope trim in Phase 1 (e.g. deliver core API first, add dashboard in Phase 2).",
                f"Propose counter-budget of ${fair_market_budget:,.2f} or trim 20% non-critical deliverables.",
            ]
            counter_budget = fair_market_budget
        elif -75.0 <= variance < -45.0:
            rating = FeasibilityRating.UNREALISTIC_LOW_BUDGET
            score = 45.0
            creep_risk = "HIGH"
            recs = [
                "Severe budget mismatch. Client budget covers only ~40% of standard senior implementation effort.",
                "Deploy Closing Studio 'Scope Modulation' strategy: Deliver essential MVP spike only.",
                "Strictly require signed Change Order protocol for any extra feature requests.",
            ]
            counter_budget = fair_market_budget
        else:  # variance < -75.0
            rating = FeasibilityRating.HIGH_RISK_SCOPE_CREEP
            score = 25.0
            creep_risk = "CRITICAL"
            recs = [
                "High exploitation risk. Project requirements require full enterprise team but offer micro-budget.",
                "Decline or propose fixed-scope exploratory blueprint milestone ($1,500 - $3,000) before writing code.",
            ]
            counter_budget = max(proposed * 3.0, fair_market_budget)

        return BudgetFeasibilityResult(
            feasibility_rating=rating,
            feasibility_score=round(max(0.0, min(100.0, score)), 1),
            estimated_engineering_hours_min=hours_min,
            estimated_engineering_hours_max=hours_max,
            estimated_market_rate_hourly=rate,
            estimated_fair_market_budget=fair_market_budget,
            budget_variance_percent=variance,
            scope_creep_risk_level=creep_risk,
            scope_reduction_suggestions=recs,
            recommended_counter_budget=counter_budget,
        )

    def _estimate_engineering_hours(self, lower_text: str, skills: list[str]) -> tuple[int, int]:
        """Estimate realistic engineering hours based on architectural components."""
        base_min = 20
        base_max = 40

        # Scope Multipliers:
        # Fullstack / UI
        if any(k in lower_text for k in ["react", "next.js", "frontend", "ui", "vue", "dashboard"]):
            base_min += 20
            base_max += 35

        # AI / LLM / Vector RAG
        if any(
            k in lower_text
            for k in ["ai", "llm", "rag", "embeddings", "vector", "openai", "langchain"]
        ):
            base_min += 25
            base_max += 45

        # Asynchronous / Realtime
        if any(
            k in lower_text
            for k in ["websocket", "streaming", "celery", "worker", "queue", "real-time"]
        ):
            base_min += 15
            base_max += 30

        # Database & Auth
        if any(
            k in lower_text
            for k in [
                "auth",
                "jwt",
                "stripe",
                "billing",
                "payments",
                "database schema",
                "migrations",
            ]
        ):
            base_min += 15
            base_max += 25

        # Complexity boosts from word count
        words = len(lower_text.split())
        if words > 150:
            base_min += 15
            base_max += 30

        return (base_min, base_max)


# Default Singleton Instance
GLOBAL_FEASIBILITY_ANALYZER = BudgetFeasibilityAnalyzer()
