"""
REST API endpoints for conversion analytics, pipeline velocity, and outcome feedback intelligence.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.analytics.calibrator import WinProbabilityCalibrator
from src.analytics.engine import AnalyticsEngine
from src.analytics.schemas import (
    CalibratedWinModifier,
    FunnelMetrics,
    LearningInsights,
    PitchAngleMetric,
    RevenueMetrics,
    SkillPerformanceMetric,
)
from src.database.connection import get_db

logger = logging.getLogger("AnalyticsAPI")

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Outcome Intelligence"])

_ENGINE = AnalyticsEngine()
_CALIBRATOR = WinProbabilityCalibrator()


@router.get("/funnel", response_model=FunnelMetrics)
def get_conversion_funnel(
    db: Annotated[Session, Depends(get_db)],
) -> FunnelMetrics:
    """
    Retrieve application conversion funnel rates and velocity metrics.
    """
    return _ENGINE.compute_funnel_metrics(session=db)


@router.get("/pitch-angles", response_model=list[PitchAngleMetric])
def get_pitch_angle_analytics(
    db: Annotated[Session, Depends(get_db)],
) -> list[PitchAngleMetric]:
    """
    Retrieve response and win rates grouped by strategic pitch angle.
    """
    return _ENGINE.compute_pitch_angle_performance(session=db)


@router.get("/skills", response_model=list[SkillPerformanceMetric])
def get_skill_performance(
    min_applications: int = Query(default=1, ge=1, description="Minimum application sample size"),
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> list[SkillPerformanceMetric]:
    """
    Retrieve skill conversion rates and realized revenue rankings.
    """
    return _ENGINE.compute_skill_performance(session=db, min_applications=min_applications)


@router.get("/revenue", response_model=RevenueMetrics)
def get_revenue_metrics(
    db: Annotated[Session, Depends(get_db)],
) -> RevenueMetrics:
    """
    Retrieve total pipeline value, realized contract revenue, and average deal size.
    """
    return _ENGINE.compute_revenue_metrics(session=db)


@router.get("/insights", response_model=LearningInsights)
def get_learning_insights(
    db: Annotated[Session, Depends(get_db)],
) -> LearningInsights:
    """
    Synthesize high-impact optimization recommendations and top-converting niches.
    """
    return _ENGINE.generate_insights(session=db)


@router.get("/modifiers", response_model=list[CalibratedWinModifier])
def get_calibrated_win_modifiers(
    db: Annotated[Session, Depends(get_db)],
) -> list[CalibratedWinModifier]:
    """
    Retrieve empirical scoring multipliers learned from historical outcomes.
    """
    return _CALIBRATOR.get_learned_modifiers(session=db)
