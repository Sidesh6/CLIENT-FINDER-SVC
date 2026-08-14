"""
Outcome Analytics & Intelligence Engine.
Aggregates conversion funnels, pitch angle win rates, skill profitability, and pipeline velocity.
"""

import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.analytics.schemas import (
    FunnelMetrics,
    LearningInsights,
    PitchAngleMetric,
    RevenueMetrics,
    SkillPerformanceMetric,
)
from src.database.connection import SessionLocal
from src.database.models import ApplicationModel, ApplicationStatus
from src.proposal.schemas import PitchAngle

logger = logging.getLogger("AnalyticsEngine")


class AnalyticsEngine:
    """
    Computes conversion metrics, sales velocity, and historical ROI breakdowns.
    """

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def compute_funnel_metrics(
        self,
        since: datetime | None = None,
        session: Session | None = None,
    ) -> FunnelMetrics:
        """Calculate complete application conversion funnel and response velocity."""
        sess = session or self.session_factory()
        own_session = session is None

        try:
            stmt = select(ApplicationModel)
            if since:
                stmt = stmt.where(ApplicationModel.applied_at >= since)

            apps = list(sess.scalars(stmt).all())
            total = len(apps)

            if total == 0:
                return FunnelMetrics()

            replied = [
                a
                for a in apps
                if a.response_at is not None
                or a.status
                in (
                    ApplicationStatus.CLIENT_REPLIED.value,
                    ApplicationStatus.INTERVIEW.value,
                    ApplicationStatus.NEGOTIATION.value,
                    ApplicationStatus.WON.value,
                )
            ]
            interviewed = [
                a
                for a in apps
                if a.interview_at is not None
                or a.status
                in (
                    ApplicationStatus.INTERVIEW.value,
                    ApplicationStatus.NEGOTIATION.value,
                    ApplicationStatus.WON.value,
                )
            ]
            negotiation = [a for a in apps if a.status == ApplicationStatus.NEGOTIATION.value]
            won = [a for a in apps if a.status == ApplicationStatus.WON.value]
            lost = [a for a in apps if a.status == ApplicationStatus.LOST.value]
            active = [
                a
                for a in apps
                if a.status
                not in (
                    ApplicationStatus.WON.value,
                    ApplicationStatus.LOST.value,
                    ApplicationStatus.CANCELLED.value,
                    ApplicationStatus.COMPLETED.value,
                )
            ]

            # Calculate Velocity
            reply_times_hours = []
            for a in apps:
                if a.response_at and a.applied_at:
                    diff = (a.response_at - a.applied_at).total_seconds() / 3600.0
                    if diff >= 0:
                        reply_times_hours.append(diff)

            close_times_days = []
            for a in won:
                if a.closed_at and a.applied_at:
                    diff = (a.closed_at - a.applied_at).total_seconds() / 86400.0
                    if diff >= 0:
                        close_times_days.append(diff)

            avg_reply = (
                sum(reply_times_hours) / len(reply_times_hours) if reply_times_hours else 0.0
            )
            avg_close = sum(close_times_days) / len(close_times_days) if close_times_days else 0.0

            return FunnelMetrics(
                total_applications=total,
                replied_count=len(replied),
                interview_count=len(interviewed),
                negotiation_count=len(negotiation),
                won_count=len(won),
                lost_count=len(lost),
                active_count=len(active),
                response_rate=round((len(replied) / total) * 100.0, 1),
                interview_rate=round((len(interviewed) / total) * 100.0, 1),
                win_rate=round((len(won) / total) * 100.0, 1),
                close_rate=round((len(won) / len(interviewed)) * 100.0, 1) if interviewed else 0.0,
                avg_time_to_reply_hours=round(avg_reply, 1),
                avg_time_to_close_days=round(avg_close, 1),
            )
        finally:
            if own_session:
                sess.close()

    def compute_pitch_angle_performance(
        self,
        session: Session | None = None,
    ) -> list[PitchAngleMetric]:
        """Evaluate conversion success across strategic pitch angles."""
        sess = session or self.session_factory()
        own_session = session is None

        try:
            apps = list(sess.scalars(select(ApplicationModel)).all())
            grouped: dict[str, list[ApplicationModel]] = defaultdict(list)

            for a in apps:
                angle_key = a.pitch_angle or PitchAngle.TECHNICAL_EXPERT.value
                grouped[angle_key].append(a)

            results = []
            for angle_enum in PitchAngle:
                angle_apps = grouped.get(angle_enum.value, [])
                total = len(angle_apps)
                if total == 0:
                    results.append(PitchAngleMetric(pitch_angle=angle_enum))
                    continue

                replied = sum(
                    1
                    for a in angle_apps
                    if a.response_at
                    or a.status
                    in (
                        ApplicationStatus.CLIENT_REPLIED.value,
                        ApplicationStatus.INTERVIEW.value,
                        ApplicationStatus.NEGOTIATION.value,
                        ApplicationStatus.WON.value,
                    )
                )
                won = sum(1 for a in angle_apps if a.status == ApplicationStatus.WON.value)
                budgets = [a.proposed_budget for a in angle_apps if a.proposed_budget is not None]
                revenue = sum(a.final_revenue for a in angle_apps if a.final_revenue is not None)

                results.append(
                    PitchAngleMetric(
                        pitch_angle=angle_enum,
                        total_sent=total,
                        replied=replied,
                        won=won,
                        win_rate=round((won / total) * 100.0, 1),
                        avg_proposed_budget=round(sum(budgets) / len(budgets), 2)
                        if budgets
                        else 0.0,
                        total_revenue=round(revenue, 2),
                    )
                )

            return results
        finally:
            if own_session:
                sess.close()

    def compute_skill_performance(
        self,
        session: Session | None = None,
        min_applications: int = 1,
    ) -> list[SkillPerformanceMetric]:
        """Analyze win rates and revenue generation attributed to specific skills."""
        sess = session or self.session_factory()
        own_session = session is None

        try:
            stmt = select(ApplicationModel).options(selectinload(ApplicationModel.project))
            apps = list(sess.scalars(stmt).all())

            skill_apps: dict[str, int] = defaultdict(int)
            skill_wins: dict[str, int] = defaultdict(int)
            skill_revenue: dict[str, float] = defaultdict(float)

            for a in apps:
                proj = a.project
                if not proj or not proj.skills:
                    continue

                is_won = a.status == ApplicationStatus.WON.value
                rev = a.final_revenue or 0.0

                for s in proj.skills:
                    s_clean = s.strip().title()
                    skill_apps[s_clean] += 1
                    if is_won:
                        skill_wins[s_clean] += 1
                        skill_revenue[s_clean] += rev

            metrics = []
            for s, total in skill_apps.items():
                if total >= min_applications:
                    wins = skill_wins[s]
                    metrics.append(
                        SkillPerformanceMetric(
                            skill=s,
                            applications_count=total,
                            wins_count=wins,
                            win_rate=round((wins / total) * 100.0, 1),
                            total_revenue=round(skill_revenue[s], 2),
                        )
                    )

            metrics.sort(key=lambda m: (m.wins_count, m.total_revenue), reverse=True)
            return metrics
        finally:
            if own_session:
                sess.close()

    def compute_revenue_metrics(
        self,
        session: Session | None = None,
    ) -> RevenueMetrics:
        """Calculate pipeline and realized revenue indicators."""
        sess = session or self.session_factory()
        own_session = session is None

        try:
            apps = list(sess.scalars(select(ApplicationModel)).all())

            active_pipeline = sum(
                a.proposed_budget
                for a in apps
                if a.proposed_budget
                and a.status
                not in (
                    ApplicationStatus.WON.value,
                    ApplicationStatus.LOST.value,
                    ApplicationStatus.CANCELLED.value,
                    ApplicationStatus.COMPLETED.value,
                )
            )

            won_deals = [
                a.final_revenue
                for a in apps
                if a.status == ApplicationStatus.WON.value and a.final_revenue
            ]
            realized = sum(won_deals)
            avg_deal = realized / len(won_deals) if won_deals else 0.0
            max_deal = max(won_deals) if won_deals else 0.0

            return RevenueMetrics(
                total_pipeline_value=round(active_pipeline, 2),
                realized_revenue=round(realized, 2),
                average_deal_size=round(avg_deal, 2),
                highest_deal_value=round(max_deal, 2),
                currency="USD",
            )
        finally:
            if own_session:
                sess.close()

    def generate_insights(
        self,
        session: Session | None = None,
    ) -> LearningInsights:
        """Synthesize actionable optimization recommendations from historical data."""
        sess = session or self.session_factory()
        own_session = session is None

        try:
            pitch_metrics = self.compute_pitch_angle_performance(session=sess)
            skill_metrics = self.compute_skill_performance(session=sess)
            funnel = self.compute_funnel_metrics(session=sess)

            # Best Pitch Angle
            valid_pitches = [p for p in pitch_metrics if p.total_sent >= 1]
            best_pitch = (
                max(valid_pitches, key=lambda p: (p.win_rate, p.total_revenue)).pitch_angle
                if valid_pitches
                else None
            )

            # High Converting Skills
            top_conv_skills = [
                s.skill
                for s in sorted(
                    skill_metrics, key=lambda s: (s.win_rate, s.wins_count), reverse=True
                )[:5]
            ]
            top_rev_skills = [
                s.skill
                for s in sorted(skill_metrics, key=lambda s: s.total_revenue, reverse=True)[:5]
            ]

            recommendations = []
            if funnel.total_applications == 0:
                recommendations.append(
                    "Begin tracking submitted proposals to generate empirical intelligence."
                )
            else:
                if best_pitch:
                    recommendations.append(
                        f"Strategic angle '{best_pitch.value}' demonstrates the highest response rate. Prioritize for upcoming proposals."
                    )
                if top_conv_skills:
                    recommendations.append(
                        f"High-conversion skill niche detected: {', '.join(top_conv_skills[:3])}."
                    )
                if funnel.response_rate < 30.0 and funnel.total_applications >= 5:
                    recommendations.append(
                        "Response rate is below 30%. Consider testing the Consultative Advisor pitch angle or customizing initial hook sentences."
                    )

            return LearningInsights(
                best_pitch_angle=best_pitch,
                highest_converting_skills=top_conv_skills,
                top_revenue_skills=top_rev_skills,
                recommendations=recommendations,
            )
        finally:
            if own_session:
                sess.close()
