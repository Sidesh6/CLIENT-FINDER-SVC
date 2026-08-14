"""
Multi-Channel Notification Dispatcher subsystem.
Provides alerting across Console, Discord, Slack, Email, and Desktop channels.
"""

from src.notifications.base import BaseNotifier
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
    NotificationPriority,
    NotificationResult,
)

__all__ = [
    "BaseNotifier",
    "ConsoleNotifier",
    "DesktopNotifier",
    "DiscordNotifier",
    "EmailNotifier",
    "NotificationChannel",
    "NotificationDispatcher",
    "NotificationPayload",
    "NotificationPriority",
    "NotificationRateLimiter",
    "NotificationResult",
    "SlackNotifier",
]
