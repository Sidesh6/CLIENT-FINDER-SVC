"""
Skill Matching Engine.
Compares extracted project requirements against user profile proficiencies,
computing multi-tier match scores, coverage metrics, and transparent explanations.
"""

from typing import Any

from src.ai.schemas import ExtractedRequirements
from src.matching.schemas import SkillMatchResult
from src.matching.taxonomy import (
    get_implied_skills,
    normalize_skill_name,
)
from src.models.profile import SkillProficiency, UserProfile, get_default_profile
from src.models.project import Project


class SkillMatcher:
    """
    Evaluates project opportunities against developer profiles with exact,
    synonym, and ontological skill matching.
    """

    def __init__(self, default_profile: UserProfile | None = None):
        self.default_profile = default_profile or get_default_profile()

    def match(
        self,
        project: Project | ExtractedRequirements | dict[str, Any],
        profile: UserProfile | None = None,
    ) -> SkillMatchResult:
        """
        Evaluate a project against a user profile and generate an explainable match result.
        """
        user_profile = profile or self.default_profile

        # Extract normalized attributes from input
        project_skills, category_str, budget, currency, payment_type_str = (
            self._extract_project_attrs(project)
        )

        user_skill_map = user_profile.get_skill_map()

        matched_skills: list[str] = []
        missing_skills: list[str] = []
        implied_skills: list[str] = []
        proficiencies: list[float] = []
        primary_match_count = 0

        # Multi-tier skill matching loop
        for raw_skill in project_skills:
            canon_skill = normalize_skill_name(raw_skill)
            skill_key = canon_skill.lower()

            # Tier 1: Direct / Synonym Match in Profile
            if skill_key in user_skill_map:
                user_prof = user_skill_map[skill_key]
                matched_skills.append(canon_skill)
                proficiencies.append(float(user_prof.proficiency))
                if user_prof.is_primary:
                    primary_match_count += 1
                continue

            # Tier 2: Ontological Implication Matching
            # Case A: Does any user skill imply this required skill? (e.g. user has FastAPI -> implies Python)
            implied_found = False
            for u_prof in user_profile.skills:
                u_canon = normalize_skill_name(u_prof.name)
                implied_from_user = [
                    normalize_skill_name(s).lower() for s in get_implied_skills(u_canon)
                ]
                if skill_key in implied_from_user:
                    implied_skills.append(canon_skill)
                    proficiencies.append(float(u_prof.proficiency) * 0.85)
                    implied_found = True
                    break

            # Case B: Does the required skill imply skills the user has with high proficiency?
            if not implied_found:
                implied_from_req = [
                    normalize_skill_name(s).lower() for s in get_implied_skills(canon_skill)
                ]
                user_matches_for_req = [
                    user_skill_map[imp] for imp in implied_from_req if imp in user_skill_map
                ]
                if user_matches_for_req:
                    best_u_prof = max(user_matches_for_req, key=lambda s: s.proficiency)
                    implied_skills.append(canon_skill)
                    proficiencies.append(float(best_u_prof.proficiency) * 0.75)
                    implied_found = True

            # Tier 3: Missing Skill
            if not implied_found:
                missing_skills.append(canon_skill)

        # Calculate Coverage and Proficiencies
        total_reqs = len(project_skills)
        if total_reqs == 0:
            coverage_ratio = 1.0
            avg_proficiency = 8.0
            raw_score = 65.0
        else:
            effective_matches = len(matched_skills) + (len(implied_skills) * 0.80)
            coverage_ratio = min(1.0, effective_matches / total_reqs)
            avg_proficiency = sum(proficiencies) / len(proficiencies) if proficiencies else 0.0
            prof_factor = avg_proficiency / 10.0
            raw_score = (coverage_ratio * 70.0) + (prof_factor * 30.0)

        # Primary Skill Bonus (+5% if all matched skills are primary)
        if matched_skills and primary_match_count == len(matched_skills):
            raw_score += 5.0

        # Category Compatibility Check & Adjustments
        category_match = True
        if category_str:
            matched_pref = any(
                pref.value.lower() == category_str.lower()
                or pref.name.lower() == category_str.lower()
                for pref in user_profile.preferred_categories
            )
            if matched_pref:
                category_match = True
                raw_score += 5.0
            else:
                category_match = False
                raw_score -= 8.0

        # Budget & Compensation Fit
        budget_fit = self._check_budget_fit(budget, currency, payment_type_str, user_profile)
        if not budget_fit:
            raw_score -= 5.0

        # Bound score to 0.0 - 100.0
        final_score = round(max(0.0, min(100.0, raw_score)), 1)
        is_strong = final_score >= 70.0 and len(missing_skills) == 0

        # Build Explanation
        explanation = self._build_explanation(
            final_score=final_score,
            total_reqs=total_reqs,
            matched_skills=matched_skills,
            implied_skills=implied_skills,
            missing_skills=missing_skills,
            avg_proficiency=avg_proficiency,
            category_str=category_str,
            category_match=category_match,
            budget=budget,
            currency=currency,
            budget_fit=budget_fit,
            user_profile=user_profile,
        )

        return SkillMatchResult(
            match_score=final_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            implied_skills=implied_skills,
            coverage_ratio=round(coverage_ratio, 2),
            average_proficiency=round(avg_proficiency, 1),
            category_match=category_match,
            budget_fit=budget_fit,
            is_strong_match=is_strong,
            explanation=explanation,
        )

    def match_many(
        self,
        projects: list[Project | ExtractedRequirements | dict[str, Any]],
        profile: UserProfile | None = None,
    ) -> list[tuple[Any, SkillMatchResult]]:
        """
        Evaluate a batch of projects and return pairs of (project, SkillMatchResult).
        """
        return [(p, self.match(p, profile=profile)) for p in projects]

    def filter_and_rank(
        self,
        projects: list[Project | ExtractedRequirements | dict[str, Any]],
        profile: UserProfile | None = None,
        min_match_score: float = 50.0,
    ) -> list[tuple[Any, SkillMatchResult]]:
        """
        Match, filter by minimum threshold, and sort descending by match_score.
        """
        results = self.match_many(projects, profile=profile)
        filtered = [item for item in results if item[1].match_score >= min_match_score]
        filtered.sort(key=lambda item: item[1].match_score, reverse=True)
        return filtered

    def _extract_project_attrs(
        self, project: Project | ExtractedRequirements | dict[str, Any]
    ) -> tuple[list[str], str | None, float | None, str | None, str | None]:
        """Extract skills, category, budget, currency, and payment type from varying input types."""
        if isinstance(project, Project):
            return (
                project.skills,
                project.category,
                project.budget,
                project.currency,
                project.project_type,
            )
        elif isinstance(project, ExtractedRequirements):
            return (
                project.required_skills,
                project.category.value,
                project.budget_min,
                project.currency,
                project.project_type.value,
            )
        elif isinstance(project, dict):
            skills = project.get("skills", project.get("required_skills", []))
            cat = project.get("category")
            budget = project.get("budget", project.get("budget_min"))
            curr = project.get("currency")
            ptype = project.get("project_type")
            return list(skills), cat, budget, curr, ptype
        return [], None, None, None, None

    def _check_budget_fit(
        self,
        budget: float | None,
        currency: str | None,
        payment_type: str | None,
        profile: UserProfile,
    ) -> bool:
        """Verify if compensation satisfies user's minimum rate/budget criteria."""
        if budget is None:
            return True  # Unknown budget assumed neutral

        # For USD equivalent budgets
        if payment_type and "hourly" in payment_type.lower():
            if profile.minimum_hourly_rate and budget < profile.minimum_hourly_rate:
                return False
        else:
            if profile.minimum_fixed_budget and budget < profile.minimum_fixed_budget:
                return False

        return True

    def _build_explanation(
        self,
        final_score: float,
        total_reqs: int,
        matched_skills: list[str],
        implied_skills: list[str],
        missing_skills: list[str],
        avg_proficiency: float,
        category_str: str | None,
        category_match: bool,
        budget: float | None,
        currency: str | None,
        budget_fit: bool,
        user_profile: UserProfile,
    ) -> str:
        """Generate clear, human-readable justification for the score."""
        parts: list[str] = []

        if final_score >= 85.0:
            parts.append(f"Outstanding match ({final_score}%).")
        elif final_score >= 70.0:
            parts.append(f"Strong opportunity match ({final_score}%).")
        elif final_score >= 50.0:
            parts.append(f"Moderate match ({final_score}%).")
        else:
            parts.append(f"Low match ({final_score}%).")

        # Skills breakdown
        if matched_skills:
            user_map = user_profile.get_skill_map()
            skills_annotated = [
                f"{s} ({user_map.get(s.lower(), SkillProficiency(name=s, proficiency=8)).proficiency}/10)"
                for s in matched_skills
            ]
            parts.append(f"Satisfies core skills: {', '.join(skills_annotated)}.")

        if implied_skills:
            parts.append(f"Covered via related experience: {', '.join(implied_skills)}.")

        if missing_skills:
            parts.append(f"Missing required skills: {', '.join(missing_skills)}.")

        # Category and budget
        if category_str:
            if category_match:
                parts.append(f"Category '{category_str}' matches your preferred focus.")
            else:
                parts.append(f"Category '{category_str}' is outside your top preferences.")

        if budget is not None:
            if budget_fit:
                parts.append(f"Compensation ({budget} {currency or 'USD'}) meets minimum criteria.")
            else:
                parts.append(
                    f"Compensation ({budget} {currency or 'USD'}) is below your minimum threshold."
                )

        return " ".join(parts)
