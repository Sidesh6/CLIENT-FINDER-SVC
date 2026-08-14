"""
Unit tests for multi-channel notification dispatcher, templates, channels, and rate limiter.
"""

from unittest.mock import MagicMock, patch

from pydantic import HttpUrl

from src.models.project import Project
from src.notifications.channels.console import ConsoleNotifier
from src.notifications.channels.desktop import DesktopNotifier
from src.notifications.channels.discord import DiscordNotifier
from src.notifications.channels.email_channel import EmailNotifier
from src.notifications.channels.slack import SlackNotifier
from src.notifications.dispatcher import NotificationDispatcher
from src.notifications.rate_limiter import NotificationRateLimiter
from src.notifications.schemas import (
    NotificationChannel,
    NotificationPayload,
)
from src.notifications.templates import (
    format_discord_embed,
    format_html_email,
    format_plaintext_email,
    format_slack_blocks,
)
from src.scoring.schemas import OpportunityScoreBreakdown, ScoringRecommendation


class TestNotificationTemplates:
    """Tests for payload formatters across Discord, Slack, and Email."""

    def test_discord_embed_format(self):
        payload = NotificationPayload(
            title="FastAPI LLM Microservice",
            source="Hacker News",
            source_url="https://example.com/job",
            overall_score=88.5,
            recommendation="APPLY_IMMEDIATELY",
            budget_display="USD 5,000 (Fixed Price)",
            skills=["Python", "FastAPI", "LangChain"],
            explanation="Outstanding match with 88.5% score.",
        )

        discord_data = format_discord_embed(payload)
        assert "embeds" in discord_data
        embed = discord_data["embeds"][0]
        assert embed["color"] == 0x22C55E  # Green for APPLY_IMMEDIATELY
        assert "FastAPI LLM Microservice" in embed["title"]
        assert any(f["name"] == "⭐ Overall Score" for f in embed["fields"])

    def test_slack_block_format(self):
        payload = NotificationPayload(
            title="Senior React Native Engineer",
            source="RemoteOK",
            source_url="https://remoteok.com/job/123",
            overall_score=75.0,
            recommendation="STRONG_PROSPECT",
            budget_display="$85/hr (Hourly)",
            skills=["React Native", "TypeScript"],
            explanation="Solid match.",
        )

        slack_data = format_slack_blocks(payload)
        assert "blocks" in slack_data
        blocks = slack_data["blocks"]
        assert any(b["type"] == "header" for b in blocks)
        assert any(b["type"] == "actions" for b in blocks)

    def test_email_html_and_plaintext(self):
        payload = NotificationPayload(
            title="AI Pipeline Engineer",
            source="Hacker News",
            source_url="https://news.ycombinator.com/item?id=999",
            overall_score=92.0,
            recommendation="APPLY_IMMEDIATELY",
            budget_display="USD 8,000",
            skills=["Python", "PyTorch", "RAG"],
            explanation="Priority target.",
        )

        html = format_html_email(payload)
        assert "<!DOCTYPE html>" in html
        assert "AI Pipeline Engineer" in html
        assert "92.0/100" in html

        text = format_plaintext_email(payload)
        assert "TARGET OPPORTUNITY ALERT" in text
        assert "https://news.ycombinator.com/item?id=999" in text


class TestRateLimiter:
    """Tests for cooldown and global rate limiting."""

    def test_rate_limiter_cooldown(self):
        limiter = NotificationRateLimiter(cooldown_seconds=3600.0)

        # First alert allowed
        allowed, reason = limiter.should_send("https://example.com/project-1")
        assert allowed is True
        assert reason is None

        # Mark sent
        limiter.record_sent("https://example.com/project-1")

        # Second alert within cooldown should be blocked
        allowed2, reason2 = limiter.should_send("https://example.com/project-1")
        assert allowed2 is False
        assert "already notified" in str(reason2)

        # Different project key should still be allowed
        allowed_diff, _ = limiter.should_send("https://example.com/project-2")
        assert allowed_diff is True

    def test_rate_limiter_global_throttle(self):
        limiter = NotificationRateLimiter(max_alerts_per_minute=2)

        limiter.record_sent("p1")
        limiter.record_sent("p2")

        # Third project within 60s should be throttled
        allowed, reason = limiter.should_send("p3")
        assert allowed is False
        assert "Global rate limit reached" in str(reason)


class TestNotificationChannels:
    """Tests for individual notifier channel implementations."""

    def test_console_notifier(self, capsys):
        notifier = ConsoleNotifier(enabled=True, use_colors=False)
        payload = NotificationPayload(
            title="Backend Architect Needed",
            source="Hacker News",
            source_url="https://example.com/arch",
            overall_score=82.0,
            recommendation="APPLY_IMMEDIATELY",
            explanation="Excellent fit.",
        )

        res = notifier.send(payload)
        assert res.success is True
        assert res.channel == NotificationChannel.CONSOLE

        captured = capsys.readouterr()
        assert "Backend Architect Needed" in captured.out
        assert "82.0/100" in captured.out

    def test_discord_notifier_with_mock_http(self):
        mock_http = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_http.post_json.return_value = mock_resp

        notifier = DiscordNotifier(
            webhook_url="https://discord.com/api/webhooks/mock",
            enabled=True,
            http_client=mock_http,
        )

        payload = NotificationPayload(
            title="Discord Alert Test",
            source="HN",
            source_url="https://example.com",
            overall_score=85.0,
            recommendation="APPLY_IMMEDIATELY",
            explanation="Test audit.",
        )

        res = notifier.send(payload)
        assert res.success is True
        mock_http.post_json.assert_called_once()

    def test_slack_notifier_with_mock_http(self):
        mock_http = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http.post_json.return_value = mock_resp

        notifier = SlackNotifier(
            webhook_url="https://hooks.slack.com/services/mock",
            enabled=True,
            http_client=mock_http,
        )

        payload = NotificationPayload(
            title="Slack Alert Test",
            source="RemoteOK",
            source_url="https://example.com",
            overall_score=78.0,
            recommendation="STRONG_PROSPECT",
            explanation="Test audit.",
        )

        res = notifier.send(payload)
        assert res.success is True
        mock_http.post_json.assert_called_once()

    @patch("smtplib.SMTP")
    def test_email_notifier_with_mock_smtp(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            recipient_email="developer@example.com",
            enabled=True,
            use_tls=False,
        )

        payload = NotificationPayload(
            title="Email Alert Test",
            source="HN",
            source_url="https://example.com",
            overall_score=89.0,
            recommendation="APPLY_IMMEDIATELY",
            explanation="Great match.",
        )

        res = notifier.send(payload)
        assert res.success is True
        mock_server.send_message.assert_called_once()

    def test_desktop_notifier(self):
        notifier = DesktopNotifier(enabled=True)
        payload = NotificationPayload(
            title="Desktop Alert Test",
            source="HN",
            source_url="https://example.com",
            overall_score=80.0,
            recommendation="APPLY_IMMEDIATELY",
            explanation="Desktop test.",
        )
        res = notifier.send(payload)
        assert res.success is True


class TestNotificationDispatcher:
    """Tests for dispatcher threshold filtering and multi-channel broadcast."""

    def test_dispatcher_threshold_filtering(self):
        mock_channel = MagicMock()
        mock_channel.enabled = True
        mock_channel.send.return_value = MagicMock(success=True)

        dispatcher = NotificationDispatcher(
            channels=[mock_channel],
            min_score_threshold=70.0,
        )

        project = Project(
            title="Low Score Opportunity",
            description="Fix small CSS issue",
            source="HN",
            source_url=HttpUrl("https://example.com/low"),
            skills=["CSS"],
        )

        low_breakdown = OpportunityScoreBreakdown(
            overall_score=45.0,
            skill_match_score=40.0,
            budget_score=50.0,
            client_score=50.0,
            competition_score=50.0,
            complexity_score=50.0,
            freshness_score=50.0,
            win_probability=40.0,
            recommendation=ScoringRecommendation.SKIP,
            explanation="Low fit.",
        )

        # Should skip because 45.0 < 70.0
        results = dispatcher.dispatch(project, low_breakdown)
        assert len(results) == 0
        mock_channel.send.assert_not_called()

    def test_dispatcher_broadcast_eligible_opportunity(self):
        mock_channel_1 = MagicMock()
        mock_channel_1.enabled = True
        mock_channel_1.channel = NotificationChannel.CONSOLE
        mock_channel_1.send.return_value = MagicMock(success=True)

        mock_channel_2 = MagicMock()
        mock_channel_2.enabled = True
        mock_channel_2.channel = NotificationChannel.DISCORD
        mock_channel_2.send.return_value = MagicMock(success=True)

        dispatcher = NotificationDispatcher(
            channels=[mock_channel_1, mock_channel_2],
            min_score_threshold=70.0,
        )

        project = Project(
            title="High Priority AI Opportunity",
            description="Build RAG system with LangChain",
            source="Hacker News",
            source_url=HttpUrl("https://example.com/high"),
            skills=["Python", "FastAPI", "LangChain"],
            budget=6000.0,
        )

        high_breakdown = OpportunityScoreBreakdown(
            overall_score=85.0,
            skill_match_score=90.0,
            budget_score=85.0,
            client_score=80.0,
            competition_score=80.0,
            complexity_score=85.0,
            freshness_score=90.0,
            win_probability=85.0,
            recommendation=ScoringRecommendation.APPLY_IMMEDIATELY,
            explanation="Priority fit.",
        )

        results = dispatcher.dispatch(project, high_breakdown)
        assert len(results) == 2
        mock_channel_1.send.assert_called_once()
        mock_channel_2.send.assert_called_once()

    def test_dispatcher_digest(self):
        mock_channel = MagicMock()
        mock_channel.enabled = True
        mock_channel.channel = NotificationChannel.CONSOLE
        mock_channel.send_digest.return_value = MagicMock(success=True)

        dispatcher = NotificationDispatcher(channels=[mock_channel])

        proj = {"title": "FastAPI Job", "source_url": "https://example.com/1", "source": "HN"}
        breakdown = OpportunityScoreBreakdown(
            overall_score=75.0,
            skill_match_score=80.0,
            budget_score=70.0,
            client_score=70.0,
            competition_score=70.0,
            complexity_score=70.0,
            freshness_score=70.0,
            win_probability=75.0,
            recommendation=ScoringRecommendation.STRONG_PROSPECT,
            explanation="Good.",
        )

        results = dispatcher.dispatch_digest([(proj, breakdown)], min_score=60.0)
        assert len(results) == 1
        mock_channel.send_digest.assert_called_once()
