"""
Multi-factor Opportunity Scoring Engine.
Calculates composite ratings, recommendations, and synchronizes scores with the database.
"""

from typing import Any

from sqlalchemy.orm import Session

from src.database.models import OpportunityModel
from src.database.repository import OpportunityRepository, ProjectRepository
from src.matching.matcher import SkillMatcher
from src.models.profile import UserProfile, get_default_profile
from src.models.project import Project
from src.scoring.calculators import (
    calculate_budget_score,
    calculate_client_score,
    calculate_competition_score,
    calculate_complexity_score,
    calculate_freshness_score,
    calculate_win_probability,
)
from src.scoring.schemas import OpportunityScoreBreakdown, ScoringRecommendation


class OpportunityScorer:
    """
    Evaluates project opportunities across 7 weighted criteria to produce
    a holistic score (0-100), decision recommendation, and explainable audit breakdown.
    """

    # Weights defined per system specification
    WEIGHT_SKILL = 0.30
    WEIGHT_BUDGET = 0.20
    WEIGHT_CLIENT = 0.15
    WEIGHT_COMPETITION = 0.10
    WEIGHT_COMPLEXITY = 0.10
    WEIGHT_FRESHNESS = 0.10
    WEIGHT_WIN_PROB = 0.05

    def __init__(
        self,
        skill_matcher: SkillMatcher | None = None,
        default_profile: UserProfile | None = None,
    ):
        self.default_profile = default_profile or get_default_profile()
        self.skill_matcher = skill_matcher or SkillMatcher(default_profile=self.default_profile)

    def score(
        self,
        project: Project | dict[str, Any],
        profile: UserProfile | None = None,
    ) -> OpportunityScoreBreakdown:
        """
        Evaluate and score a project opportunity across all 7 dimensions.
        """
        user_profile = profile or self.default_profile

        # Extract attributes
        if isinstance(project, Project):
            title = project.title
            description = project.description
            skills = project.skills
            budget = project.budget
            currency = project.currency
            project_type = project.project_type
            category = project.category
            complexity = project.complexity
            client_name = project.client_name
            source = project.source
            posted_at = project.project_start_date
        elif isinstance(project, dict):
            title = str(project.get("title", ""))
            description = str(project.get("description", ""))
            skills = list(project.get("skills", []))
            budget = project.get("budget")
            currency = project.get("currency")
            project_type = project.get("project_type")
            category = project.get("category")
            complexity = project.get("complexity")
            client_name = project.get("client_name")
            source = str(project.get("source", "Unknown"))
            posted_at = project.get("posted_at", project.get("project_start_date"))
        else:
            raise TypeError(f"Unsupported project payload: {type(project)}")

        # 1. Skill Match Score (30%)
        skill_match_res = self.skill_matcher.match(project, profile=user_profile)
        skill_score = skill_match_res.match_score

        # 2. Budget Attractiveness Score (20%)
        budget_score = calculate_budget_score(
            budget=budget,
            currency=currency,
            payment_type=project_type,
            profile=user_profile,
        )

        # 3. Client Quality Score (15%)
        client_score, risk_flags = calculate_client_score(
            title=title,
            description=description,
            client_name=client_name,
            source=source,
        )

        # 4. Competition Friction Score (10%)
        competition_score = calculate_competition_score(
            skills=skills,
            complexity=complexity,
            category=category,
        )

        # 5. Complexity Fit Score (10%)
        complexity_score = calculate_complexity_score(
            complexity=complexity,
            profile=user_profile,
        )

        # 6. Freshness & Urgency Score (10%)
        freshness_score = calculate_freshness_score(posted_at=posted_at)

        # 7. Win Probability Score (5%)
        win_prob = calculate_win_probability(
            skill_score=skill_score,
            competition_score=competition_score,
            complexity_score=complexity_score,
        )

        # Composite weighted sum
        overall = (
            (skill_score * self.WEIGHT_SKILL)
            + (budget_score * self.WEIGHT_BUDGET)
            + (client_score * self.WEIGHT_CLIENT)
            + (competition_score * self.WEIGHT_COMPETITION)
            + (complexity_score * self.WEIGHT_COMPLEXITY)
            + (freshness_score * self.WEIGHT_FRESHNESS)
            + (win_prob * self.WEIGHT_WIN_PROB)
        )

        overall_score = round(max(0.0, min(100.0, overall)), 1)

        # Decision Recommendation
        if overall_score >= 80.0:
            recommendation = ScoringRecommendation.APPLY_IMMEDIATELY
        elif overall_score >= 68.0:
            recommendation = ScoringRecommendation.STRONG_PROSPECT
        elif overall_score >= 50.0:
            recommendation = ScoringRecommendation.CONSIDER
        else:
            recommendation = ScoringRecommendation.SKIP

        # Build Explanation
        explanation = self._format_explanation(
            overall_score=overall_score,
            recommendation=recommendation,
            skill_score=skill_score,
            skill_explanation=skill_match_res.explanation,
            budget_score=budget_score,
            budget=budget,
            currency=currency,
            client_score=client_score,
            competition_score=competition_score,
            freshness_score=freshness_score,
            win_prob=win_prob,
            risk_flags=risk_flags,
        )

        return OpportunityScoreBreakdown(
            overall_score=overall_score,
            skill_match_score=skill_score,
            budget_score=budget_score,
            client_score=client_score,
            competition_score=competition_score,
            complexity_score=complexity_score,
            freshness_score=freshness_score,
            win_probability=win_prob,
            recommendation=recommendation,
            risk_flags=risk_flags,
            explanation=explanation,
        )

    def score_batch(
        self,
        projects: list[Project | dict[str, Any]],
        profile: UserProfile | None = None,
    ) -> list[tuple[Any, OpportunityScoreBreakdown]]:
        """
        Score a list of opportunities.
        """
        return [(p, self.score(p, profile=profile)) for p in projects]

    def rank_opportunities(
        self,
        projects: list[Project | dict[str, Any]],
        profile: UserProfile | None = None,
        min_score: float = 0.0,
    ) -> list[tuple[Any, OpportunityScoreBreakdown]]:
        """
        Score and rank opportunities in descending order of overall score.
        """
        scored = self.score_batch(projects, profile=profile)
        filtered = [item for item in scored if item[1].overall_score >= min_score]
        filtered.sort(key=lambda item: item[1].overall_score, reverse=True)
        return filtered

    def score_and_persist(
        self,
        project_id: int,
        project: Project,
        session: Session,
        profile: UserProfile | None = None,
    ) -> OpportunityModel:
        """
        Score an opportunity and persist the score breakdown and overall rating
        to the database (OpportunityModel & ProjectModel.score).
        """
        breakdown = self.score(project, profile=profile)

        # Update Project record overall score
        proj_repo = ProjectRepository(session)
        proj_repo.update_score(project_id, breakdown.overall_score)

        # Create/Update Opportunity record
        opp_repo = OpportunityRepository(session)
        opp_model = opp_repo.create_or_update(
            project_id=project_id,
            skill_match_score=breakdown.skill_match_score,
            budget_score=breakdown.budget_score,
            client_score=breakdown.client_score,
            overall_score=breakdown.overall_score,
            explanation=breakdown.explanation,
        )

        # Populate optional multi-criteria columns
        opp_model.competition_score = breakdown.competition_score
        opp_model.complexity_score = breakdown.complexity_score
        opp_model.freshness_score = breakdown.freshness_score
        opp_model.win_probability = breakdown.win_probability

        session.flush()
        return opp_model

    def _format_explanation(
        self,
        overall_score: float,
        recommendation: ScoringRecommendation,
        skill_score: float,
        skill_explanation: str,
        budget_score: float,
        budget: float | None,
        currency: str | None,
        client_score: float,
        competition_score: float,
        freshness_score: float,
        win_prob: float,
        risk_flags: list[str],
    ) -> str:
        """Construct multi-factor audit narrative."""
        tier_names = {
            ScoringRecommendation.APPLY_IMMEDIATELY: "Priority Target (Apply Immediately)",
            ScoringRecommendation.STRONG_PROSPECT: "Strong Opportunity Prospect",
            ScoringRecommendation.CONSIDER: "Viable Opportunity (Consider)",
            ScoringRecommendation.SKIP: "Low Priority (Skip)",
        }

        budget_display = f"{budget} {currency or 'USD'}" if budget else "Unstated"
        parts: list[str] = [
            f"Overall rating: {overall_score}/100 [{tier_names[recommendation]}].",
            f"Skill Fit: {skill_score}/100 ({skill_explanation}).",
            f"Budget: {budget_score}/100 ({budget_display}).",
            f"Client Quality: {client_score}/100.",
            f"Competition Friction: {competition_score}/100 (Est. Win Probability: {win_prob}%).",
        ]

        if risk_flags:
            parts.append(f"Risk Signals: {'; '.join(risk_flags)}.")

        return " ".join(parts)
