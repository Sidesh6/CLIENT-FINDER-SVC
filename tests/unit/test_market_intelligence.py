"""
Unit tests for AI Market Intelligence, Skill ROI Heatmaps, and Expected Value Proposal Pricing Optimization.
"""

from fastapi.testclient import TestClient

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
from src.api.main import app

client = TestClient(app)


class TestMarketIntelligenceEngine:
    """Tests for market data aggregation, skill demand metrics, and upskilling roadmaps."""

    def test_market_overview_generation(self):
        engine = MarketIntelligenceEngine()
        overview = engine.get_market_overview()

        assert isinstance(overview, MarketOverview)
        assert overview.total_active_listings >= 1
        assert overview.total_market_pipeline_value > 0
        assert len(overview.top_paying_skills) >= 1
        assert len(overview.most_demanded_skills) >= 1

    def test_skill_roi_ranking(self):
        engine = MarketIntelligenceEngine()
        ranking = engine.get_skill_roi_ranking()

        assert isinstance(ranking, list)
        assert len(ranking) >= 5
        assert all(isinstance(s, SkillMarketMetrics) for s in ranking)
        # Verify Python / FastAPI / RAG / Rust exist
        skills_set = {s.skill for s in ranking}
        assert "Python" in skills_set
        assert "FastAPI" in skills_set

    def test_upskill_recommendations(self):
        engine = MarketIntelligenceEngine()
        upskills = engine.get_upskill_recommendations()

        assert isinstance(upskills, list)
        assert len(upskills) >= 1
        assert all(isinstance(u, UpskillRecommendation) for u in upskills)
        assert all(u.projected_rate_increase_pct > 0 for u in upskills)


class TestRateOptimizer:
    """Tests for price elasticity and Expected Value optimization."""

    def test_rate_optimization_without_client_budget(self):
        optimizer = RateOptimizer()
        req = RateOptimizationRequest(
            project_title="FastAPI Microservices",
            match_score=85.0,
            estimated_hours=50.0,
            target_hourly_rate=100.0,
            client_budget=None,
        )
        res = optimizer.optimize(req)

        assert isinstance(res, RateOptimizationResult)
        assert res.optimal_recommended_rate > 0
        assert len(res.strategies) == 3
        strat_names = {s.strategy_name for s in res.strategies}
        assert "MAX_WIN_RATE" in strat_names
        assert "OPTIMAL_EV" in strat_names
        assert "PREMIUM_ANCHOR" in strat_names
        assert len(res.curve_data_points) >= 6

    def test_rate_optimization_with_strict_budget(self):
        optimizer = RateOptimizer()
        req = RateOptimizationRequest(
            project_title="Fixed Budget AI App",
            match_score=90.0,
            estimated_hours=40.0,
            target_hourly_rate=120.0,
            client_budget=3000.0,
        )
        res = optimizer.optimize(req)

        assert isinstance(res, RateOptimizationResult)
        # Confirm that quotes well beyond 3000 have penalized win rates
        for pt in res.curve_data_points:
            if pt["total_price"] > 5000:
                assert pt["win_probability"] < 25.0


class TestMarketApiRoutes:
    """Tests for market intelligence and rate optimizer REST endpoints."""

    def test_get_market_overview_endpoint(self):
        res = client.get("/api/market/overview")
        assert res.status_code == 200
        data = res.json()
        assert "total_active_listings" in data
        assert "total_market_pipeline_value" in data
        assert "top_paying_skills" in data

    def test_get_skills_roi_endpoint(self):
        res = client.get("/api/market/skills/roi")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 5

    def test_get_upskill_recommendations_endpoint(self):
        res = client.get("/api/market/recommendations/upskill")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_optimize_rate_endpoint(self):
        res = client.post(
            "/api/market/optimize-rate",
            json={
                "project_title": "Enterprise Cloud Architecture",
                "match_score": 88.0,
                "estimated_hours": 60.0,
                "target_hourly_rate": 110.0,
                "client_budget": 8000.0,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "optimal_recommended_rate" in data
        assert "strategies" in data
        assert len(data["strategies"]) == 3
