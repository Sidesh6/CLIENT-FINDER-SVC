"""
Empirical Win Probability Calibrator & Feedback Loop.
Dynamically calibrates opportunity win probability formulas using historical wins and losses.
"""

import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.analytics.schemas import CalibratedWinModifier
from src.database.connection import SessionLocal
from src.database.models import ApplicationModel, ApplicationStatus
from src.models.project import Project
from src.proposal.schemas import PitchAngle

logger = logging.getLogger("WinProbabilityCalibrator")


class WinProbabilityCalibrator:
    """
    Learns empirical success patterns from tracked outcomes and dynamically
    calibrates win probability estimates.
    """

    def __init__(
        self,
        min_samples_threshold: int = 3,
        default_baseline_win_rate: float = 0.25,
        session_factory: Any = SessionLocal,
    ):
        self.min_samples_threshold = min_samples_threshold
        self.default_baseline_win_rate = default_baseline_win_rate
        self.session_factory = session_factory

    def get_learned_modifiers(
        self,
        session: Session | None = None,
    ) -> list[CalibratedWinModifier]:
        """Compute empirical skill and pitch angle multipliers based on recorded outcomes."""
        sess = session or self.session_factory()
        own_session = session is None

        try:
            stmt = select(ApplicationModel).options(selectinload(ApplicationModel.project))
            apps = list(sess.scalars(stmt).all())

            # Only evaluate terminal closed applications (WON vs LOST)
            closed_apps = [
                a
                for a in apps
                if a.status in (ApplicationStatus.WON.value, ApplicationStatus.LOST.value)
            ]

            if len(closed_apps) < self.min_samples_threshold:
                return []

            total_closed = len(closed_apps)
            total_wins = sum(1 for a in closed_apps if a.status == ApplicationStatus.WON.value)
            baseline = (
                total_wins / total_closed if total_closed > 0 else self.default_baseline_win_rate
            )
            baseline = max(baseline, 0.05)

            modifiers: list[CalibratedWinModifier] = []

            # 1. Skill Modifiers
            skill_totals: dict[str, int] = defaultdict(int)
            skill_wins: dict[str, int] = defaultdict(int)

            for a in closed_apps:
                proj = a.project
                if proj and proj.skills:
                    is_win = a.status == ApplicationStatus.WON.value
                    for s in proj.skills:
                        s_norm = s.strip().title()
                        skill_totals[s_norm] += 1
                        if is_win:
                            skill_wins[s_norm] += 1

            for s, count in skill_totals.items():
                if count >= self.min_samples_threshold:
                    win_rate = skill_wins[s] / count
                    raw_mult = win_rate / baseline
                    clamped_mult = round(max(0.5, min(2.0, raw_mult)), 2)
                    modifiers.append(
                        CalibratedWinModifier(
                            feature_name=s,
                            feature_type="SKILL",
                            sample_size=count,
                            empirical_win_rate=round(win_rate * 100.0, 1),
                            multiplier=clamped_mult,
                        )
                    )

            # 2. Pitch Angle Modifiers
            pitch_totals: dict[str, int] = defaultdict(int)
            pitch_wins: dict[str, int] = defaultdict(int)

            for a in closed_apps:
                p_angle = a.pitch_angle or PitchAngle.TECHNICAL_EXPERT.value
                pitch_totals[p_angle] += 1
                if a.status == ApplicationStatus.WON.value:
                    pitch_wins[p_angle] += 1

            for p_name, count in pitch_totals.items():
                if count >= self.min_samples_threshold:
                    win_rate = pitch_wins[p_name] / count
                    raw_mult = win_rate / baseline
                    clamped_mult = round(max(0.5, min(2.0, raw_mult)), 2)
                    modifiers.append(
                        CalibratedWinModifier(
                            feature_name=p_name,
                            feature_type="PITCH_ANGLE",
                            sample_size=count,
                            empirical_win_rate=round(win_rate * 100.0, 1),
                            multiplier=clamped_mult,
                        )
                    )

            return modifiers
        finally:
            if own_session:
                sess.close()

    def calibrate_win_probability(
        self,
        project: Project,
        base_probability: float,
        pitch_angle: PitchAngle | None = None,
        session: Session | None = None,
    ) -> float:
        """
        Adjust base win probability using empirical modifiers learned from past performance.
        """
        modifiers = self.get_learned_modifiers(session=session)
        if not modifiers:
            return round(base_probability, 1)

        mod_map = {f"{m.feature_type}:{m.feature_name.lower()}": m.multiplier for m in modifiers}

        skill_multipliers = []
        for s in project.skills:
            key = f"SKILL:{s.strip().lower()}"
            if key in mod_map:
                skill_multipliers.append(mod_map[key])

        angle_mult = 1.0
        if pitch_angle:
            angle_key = f"PITCH_ANGLE:{pitch_angle.value.lower()}"
            angle_mult = mod_map.get(angle_key, 1.0)

        composite_skill_mult = (
            sum(skill_multipliers) / len(skill_multipliers) if skill_multipliers else 1.0
        )

        calibrated = base_probability * composite_skill_mult * angle_mult
        return round(max(5.0, min(95.0, calibrated)), 1)
