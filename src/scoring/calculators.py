"""
Mathematical factor calculators for multi-dimensional opportunity scoring.
"""

import re
from datetime import UTC, datetime

from src.models.profile import UserProfile


def calculate_budget_score(
    budget: float | None,
    currency: str | None,
    payment_type: str | None,
    profile: UserProfile,
) -> float:
    """
    Calculate budget attractiveness score (0-100) based on rate alignment vs. user profile.
    """
    if budget is None:
        return 55.0  # Neutral baseline when budget is unstated in listing

    is_hourly = payment_type and "hourly" in payment_type.lower()
    target_rate = profile.target_hourly_rate or 90.0
    min_rate = profile.minimum_hourly_rate or 50.0

    if is_hourly:
        if budget >= target_rate:
            bonus = min(10.0, ((budget - target_rate) / target_rate) * 20.0)
            return min(100.0, 90.0 + bonus)
        elif budget >= min_rate:
            progress = (budget - min_rate) / max(1.0, (target_rate - min_rate))
            return 70.0 + (progress * 19.0)
        else:
            ratio = budget / max(1.0, min_rate)
            return max(15.0, ratio * 60.0)
    else:
        min_fixed = profile.minimum_fixed_budget or 1000.0
        if budget >= 10000.0:
            return 98.0
        elif budget >= 5000.0:
            return 90.0
        elif budget >= 2500.0:
            return 80.0
        elif budget >= min_fixed:
            progress = (budget - min_fixed) / max(1.0, (2500.0 - min_fixed))
            return 65.0 + (progress * 14.0)
        else:
            ratio = budget / max(1.0, min_fixed)
            return max(15.0, ratio * 55.0)


def calculate_client_score(
    title: str,
    description: str,
    client_name: str | None,
    source: str,
) -> tuple[float, list[str]]:
    """
    Analyze client clarity, track record signals, and specification depth.
    Returns (client_score, risk_flags).
    """
    score = 60.0  # Baseline
    risk_flags: list[str] = []
    text_lower = f"{title}\n{description}".lower()

    # Positive credibility signals
    if client_name and client_name.strip() and client_name.lower() not in {"unknown", "anonymous"}:
        score += 15.0

    if len(description.strip()) >= 400:
        score += 10.0

    # Structured requirements (bullet points or numbered deliverables)
    if re.search(r"[-*•\d\.)]\s+[A-Z]", description):
        score += 10.0

    # Clear application call to action (email, github, calendly, or form)
    if re.search(r"\b(email|github|apply|reach out|contact|calendly|form)\b", text_lower):
        score += 5.0

    # Negative / Risk Signals
    if re.search(r"\b(equity[\s-]only|revenue[\s-]share|unpaid|for equity)\b", text_lower):
        score -= 40.0
        risk_flags.append("Equity-only or unpaid compensation structure")

    if len(description.strip()) < 120:
        score -= 20.0
        risk_flags.append("Extremely brief or vague project description")

    if re.search(r"\b(asap|urgent|immediately|yesterday)\b", text_lower):
        score -= 10.0
        risk_flags.append("Aggressive or unrealistic timeline indicators")

    if re.search(r"\b(rockstar|ninja|guru|wizard|unlimited revisions)\b", text_lower):
        score -= 10.0
        risk_flags.append("Potentially high-friction client expectations")

    final_score = max(10.0, min(100.0, score))
    return round(final_score, 1), risk_flags


def calculate_competition_score(
    skills: list[str],
    complexity: str | None,
    category: str | None,
) -> float:
    """
    Estimate competition friction (barrier to entry).
    Higher score = Less competition / Niche advantage.
    """
    score = 65.0
    skills_lower = {s.lower() for s in skills}

    niche_high_barrier = {
        "langchain",
        "llamaindex",
        "rag",
        "pytorch",
        "fine-tuning",
        "vector database",
        "kubernetes",
        "rust",
        "golang",
        "go",
        "snowflake",
        "kafka",
    }
    low_barrier_generic = {"wordpress", "html/css", "php", "wix", "squarespace"}

    # Niche skill barrier
    if skills_lower & niche_high_barrier:
        score += 18.0

    # Complexity barrier
    if complexity:
        comp_clean = complexity.lower()
        if "high" in comp_clean or "expert" in comp_clean:
            score += 12.0
        elif "low" in comp_clean:
            score -= 15.0

    # Low-barrier saturation penalty
    if skills_lower & low_barrier_generic and not (skills_lower & niche_high_barrier):
        score -= 20.0

    return max(20.0, min(100.0, round(score, 1)))


def calculate_complexity_score(
    complexity: str | None,
    profile: UserProfile,
) -> float:
    """
    Evaluate complexity alignment vs. developer target experience seniority.
    """
    if not complexity:
        return 75.0

    comp = complexity.lower()
    # Senior / Lead target
    if "high" in comp:
        return 95.0
    elif "medium" in comp:
        return 85.0
    elif "expert" in comp:
        return 80.0
    elif "low" in comp:
        return 55.0
    return 75.0


def calculate_freshness_score(posted_at: datetime | None) -> float:
    """
    Calculate time-decay curve based on opportunity age.
    """
    if posted_at is None:
        return 65.0

    now = datetime.now(UTC)
    if posted_at.tzinfo is None:
        # Assume UTC if naive
        posted_at = posted_at.replace(tzinfo=UTC)

    age_hours = (now - posted_at).total_seconds() / 3600.0

    if age_hours <= 6.0:
        return 100.0
    elif age_hours <= 24.0:
        return 90.0
    elif age_hours <= 72.0:  # 3 days
        return 75.0
    elif age_hours <= 168.0:  # 7 days
        return 55.0
    elif age_hours <= 336.0:  # 14 days
        return 35.0
    else:
        return 20.0


def calculate_win_probability(
    skill_score: float,
    competition_score: float,
    complexity_score: float,
) -> float:
    """
    Composite estimate of probability of securing the contract.
    """
    win_prob = (skill_score * 0.50) + (competition_score * 0.30) + (complexity_score * 0.20)
    return max(0.0, min(100.0, round(win_prob, 1)))
