"""
Slack Incoming Webhook notification channel with Block Kit message format.
"""

import logging
import os
from datetime import UTC, datetime

from src.notifications.base import BaseNotifier
from src.notifications.schemas import (
    NotificationChannel,
    NotificationPayload,
    NotificationResult,
)
from src.notifications.templates import format_slack_blocks
from src.utils.http_client import HttpClient

logger = logging.getLogger("SlackNotifier")


class SlackNotifier(BaseNotifier):
    """
    Delivers Block Kit formatted message cards to Slack channels via incoming Webhooks.
    """

    channel = NotificationChannel.SLACK

    def __init__(
        self,
        webhook_url: str | None = None,
        enabled: bool = True,
        http_client: HttpClient | None = None,
    ):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.enabled = enabled and bool(self.webhook_url)
        self.http_client = http_client or HttpClient()

    def send(self, payload: NotificationPayload) -> NotificationResult:
        """Post a single opportunity alert to Slack webhook."""
        if not self.enabled or not self.webhook_url:
            logger.debug("Slack webhook not configured or disabled; skipping alert")
            return NotificationResult(
                channel=self.channel,
                success=True,
                delivered_at=datetime.now(UTC),
                error_message="Channel disabled or webhook_url unconfigured (dry run)",
            )

        slack_data = format_slack_blocks(payload)

        try:
            response = self.http_client.post_json(self.webhook_url, json=slack_data)
            if response.status_code == 200:
                logger.info("Successfully delivered Slack alert for '%s'", payload.title[:30])
                return NotificationResult(channel=self.channel, success=True)
            else:
                err = f"Slack returned status code {response.status_code}: {response.text}"
                logger.warning(err)
                return NotificationResult(channel=self.channel, success=False, error_message=err)
        except Exception as exc:
            err = f"Slack notification error: {exc}"
            logger.error(err)
            return NotificationResult(channel=self.channel, success=False, error_message=err)

    def send_digest(self, payloads: list[NotificationPayload]) -> NotificationResult:
        """Post a digest of opportunities to Slack."""
        if not self.enabled or not self.webhook_url:
            return NotificationResult(channel=self.channel, success=True)

        fields = [
            {
                "type": "mrkdwn",
                "text": f"• *`{p.overall_score}/100`* <{p.source_url}|{p.title[:50]}>",
            }
            for p in payloads[:10]
        ]

        slack_data = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📢 Opportunity Digest ({len(payloads)} Matched)",
                        "emoji": True,
                    },
                },
                {"type": "section", "fields": fields},
                {"type": "divider"},
            ]
        }

        try:
            response = self.http_client.post_json(self.webhook_url, json=slack_data)
            return NotificationResult(channel=self.channel, success=response.status_code == 200)
        except Exception as exc:
            return NotificationResult(channel=self.channel, success=False, error_message=str(exc))
