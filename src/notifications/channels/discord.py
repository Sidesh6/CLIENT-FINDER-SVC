"""
Discord Webhook notification channel with rich embed cards.
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
from src.notifications.templates import format_discord_embed
from src.utils.http_client import HttpClient

logger = logging.getLogger("DiscordNotifier")


class DiscordNotifier(BaseNotifier):
    """
    Delivers rich Embed alert cards to a Discord channel via incoming Webhook.
    """

    channel = NotificationChannel.DISCORD

    def __init__(
        self,
        webhook_url: str | None = None,
        enabled: bool = True,
        http_client: HttpClient | None = None,
    ):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.enabled = enabled and bool(self.webhook_url)
        self.http_client = http_client or HttpClient()

    def send(self, payload: NotificationPayload) -> NotificationResult:
        """Post a single opportunity embed to Discord webhook."""
        if not self.enabled or not self.webhook_url:
            logger.debug("Discord webhook not configured or disabled; skipping alert")
            return NotificationResult(
                channel=self.channel,
                success=True,
                delivered_at=datetime.now(UTC),
                error_message="Channel disabled or webhook_url unconfigured (dry run)",
            )

        discord_data = format_discord_embed(payload)

        try:
            response = self.http_client.post_json(self.webhook_url, json=discord_data)
            if response.status_code in {200, 204}:
                logger.info("Successfully delivered Discord alert for '%s'", payload.title[:30])
                return NotificationResult(channel=self.channel, success=True)
            else:
                err = f"Discord returned status code {response.status_code}: {response.text}"
                logger.warning(err)
                return NotificationResult(channel=self.channel, success=False, error_message=err)
        except Exception as exc:
            err = f"Discord notification error: {exc}"
            logger.error(err)
            return NotificationResult(channel=self.channel, success=False, error_message=err)

    def send_digest(self, payloads: list[NotificationPayload]) -> NotificationResult:
        """Post a digest of multiple opportunities to Discord."""
        if not self.enabled or not self.webhook_url:
            return NotificationResult(channel=self.channel, success=True)

        lines = [
            f"• **[{p.overall_score}/100]** [{p.recommendation}] [{p.title[:60]}]({p.source_url})"
            for p in payloads[:15]
        ]
        digest_content = {
            "username": "Client Finder Bot",
            "embeds": [
                {
                    "title": f"📢 Daily Opportunity Digest ({len(payloads)} Matched)",
                    "description": "\n".join(lines),
                    "color": 0x3B82F6,
                }
            ],
        }

        try:
            response = self.http_client.post_json(self.webhook_url, json=digest_content)
            return NotificationResult(
                channel=self.channel, success=response.status_code in {200, 204}
            )
        except Exception as exc:
            return NotificationResult(channel=self.channel, success=False, error_message=str(exc))
