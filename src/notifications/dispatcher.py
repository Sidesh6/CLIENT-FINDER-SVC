"""
Multi-Channel Notification Dispatcher and orchestration coordinator.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from src.models.project import Project
from src.notifications.base import BaseNotifier
from src.notifications.channels.console import ConsoleNotifier
from src.notifications.channels.desktop import DesktopNotifier
from src.notifications.channels.discord import DiscordNotifier
from src.notifications.channels.email_channel import EmailNotifier
from src.notifications.channels.slack import SlackNotifier
from src.notifications.rate_limiter import NotificationRateLimiter
from src.notifications.schemas import (
    NotificationPayload,
    NotificationPriority,
    NotificationResult,
)
from src.scoring.schemas import OpportunityScoreBreakdown, ScoringRecommendation

logger = logging.getLogger("NotificationDispatcher")


class NotificationDispatcher:
    """
    Coordinates and broadcasts high-priority project opportunities across all enabled notification channels.
    """

    def __init__(
        self,
        channels: list[BaseNotifier] | None = None,
        rate_limiter: NotificationRateLimiter | None = None,
        min_score_threshold: float = 65.0,
    ):
        self.channels = channels if channels is not None else self._get_default_channels()
        self.rate_limiter = rate_limiter or NotificationRateLimiter()
        self.min_score_threshold = min_score_threshold

    def register_channel(self, channel: BaseNotifier) -> None:
        """Register an additional notification channel."""
        self.channels.append(channel)

    def dispatch(
        self,
        project: Project | dict[str, Any],
        score_breakdown: OpportunityScoreBreakdown,
        min_score: float | None = None,
    ) -> list[NotificationResult]:
        """
        Dispatch a single opportunity alert across all active channels if it meets score thresholds.
        """
        threshold = min_score if min_score is not None else self.min_score_threshold

        # Score filter threshold
        if score_breakdown.overall_score < threshold:
            proj_title = project.title if isinstance(project, Project) else str(project.get("title", ""))
            logger.debug(
                "Skipping dispatch for '%s' (Score %s < Threshold %s)",
                proj_title[:30],
                score_breakdown.overall_score,
                threshold,
            )
            return []

        payload = self._build_payload(project, score_breakdown)
        project_key = payload.source_url or payload.title

        # Check rate limiter
        allowed, reason = self.rate_limiter.should_send(project_key)
        if not allowed:
            logger.info("Rate limiter blocked alert for '%s': %s", payload.title[:30], reason)
            return []

        results: list[NotificationResult] = []
        any_success = False

        for channel in self.channels:
            if not channel.enabled:
                continue
            try:
                res = channel.send(payload)
                results.append(res)
                if res.success:
                    any_success = True
            except Exception as exc:
                logger.error("Channel %s failed with error: %s", channel.channel, exc)
                results.append(
                    NotificationResult(
                        channel=channel.channel,
                        success=False,
                        error_message=str(exc),
                    )
                )

        if any_success:
            self.rate_limiter.record_sent(project_key)

        return results

    def dispatch_batch(
        self,
        opportunities: list[tuple[Project | dict[str, Any], OpportunityScoreBreakdown]],
        min_score: float | None = None,
    ) -> list[tuple[Any, list[NotificationResult]]]:
        """
        Evaluate and dispatch a batch of scored opportunities.
        """
        batch_results: list[tuple[Any, list[NotificationResult]]] = []
        for proj, breakdown in opportunities:
            res = self.dispatch(proj, breakdown, min_score=min_score)
            batch_results.append((proj, res))
        return batch_results

    def dispatch_digest(
        self,
        opportunities: list[tuple[Project | dict[str, Any], OpportunityScoreBreakdown]],
        min_score: float = 50.0,
    ) -> list[NotificationResult]:
        """
        Compile and broadcast a summary digest across all registered channels.
        """
        eligible = [
            self._build_payload(p, s) for p, s in opportunities if s.overall_score >= min_score
        ]

        if not eligible:
            logger.info("No opportunities meet digest threshold of %s; skipping digest", min_score)
            return []

        # Sort descending by score
        eligible.sort(key=lambda p: p.overall_score, reverse=True)

        results: list[NotificationResult] = []
        for channel in self.channels:
            if not channel.enabled:
                continue
            try:
                res = channel.send_digest(eligible)
                results.append(res)
            except Exception as exc:
                logger.error("Channel %s digest failed: %s", channel.channel, exc)
                results.append(
                    NotificationResult(
                        channel=channel.channel,
                        success=False,
                        error_message=str(exc),
                    )
                )
        return results

    def _build_payload(
        self,
        project: Project | dict[str, Any],
        score_breakdown: OpportunityScoreBreakdown,
    ) -> NotificationPayload:
        """Construct standardized NotificationPayload from project & score breakdown."""
        if isinstance(project, Project):
            title = project.title
            source = project.source
            source_url = str(project.source_url)
            skills = project.skills
            budget = project.budget
            currency = project.currency or "USD"
            project_type = project.project_type or "Contract"
        elif isinstance(project, dict):
            title = str(project.get("title", ""))
            source = str(project.get("source", "Unknown"))
            source_url = str(project.get("source_url", project.get("url", "")))
            skills = list(project.get("skills", []))
            budget = project.get("budget")
            currency = str(project.get("currency", "USD"))
            project_type = str(project.get("project_type", "Contract"))
        else:
            raise TypeError(f"Unsupported project type: {type(project)}")

        if budget is not None:
            budget_display = f"{currency} {budget:,.0f} ({project_type})"
        else:
            budget_display = "Unstated / Competitive"

        # Determine notification priority
        rec = score_breakdown.recommendation
        if rec == ScoringRecommendation.APPLY_IMMEDIATELY:
            priority = NotificationPriority.URGENT
        elif rec == ScoringRecommendation.STRONG_PROSPECT:
            priority = NotificationPriority.HIGH
        elif rec == ScoringRecommendation.CONSIDER:
            priority = NotificationPriority.MEDIUM
        else:
            priority = NotificationPriority.LOW

        return NotificationPayload(
            title=title,
            source=source,
            source_url=source_url,
            overall_score=score_breakdown.overall_score,
            recommendation=str(rec),
            budget_display=budget_display,
            skills=skills,
            explanation=score_breakdown.explanation,
            priority=priority,
            timestamp=datetime.now(UTC),
        )

    def _get_default_channels(self) -> list[BaseNotifier]:
        """Instantiate default active notification channels."""
        return [
            ConsoleNotifier(enabled=True),
            DiscordNotifier(enabled=True),
            SlackNotifier(enabled=True),
            EmailNotifier(enabled=True),
            DesktopNotifier(enabled=True),
        ]
