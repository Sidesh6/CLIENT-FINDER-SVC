"""
Abstract base class for notification channels.
"""

from abc import ABC, abstractmethod

from src.notifications.schemas import (
    NotificationChannel,
    NotificationPayload,
    NotificationResult,
)


class BaseNotifier(ABC):
    """
    Abstract interface for notification channel handlers.
    """

    channel: NotificationChannel
    enabled: bool = True

    @abstractmethod
    def send(self, payload: NotificationPayload) -> NotificationResult:
        """
        Send a single opportunity notification.
        """
        raise NotImplementedError

    @abstractmethod
    def send_digest(self, payloads: list[NotificationPayload]) -> NotificationResult:
        """
        Send a periodic batch digest of multiple opportunities.
        """
        raise NotImplementedError
