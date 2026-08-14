"""
Notification schemas, channel enums, and delivery status models.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class NotificationChannel(StrEnum):
    """Supported alert delivery channels."""

    CONSOLE = "CONSOLE"
    DISCORD = "DISCORD"
    SLACK = "SLACK"
    EMAIL = "EMAIL"
    DESKTOP = "DESKTOP"


class NotificationPriority(StrEnum):
    """Notification urgency level."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class NotificationPayload(BaseModel):
    """
    Standardized message payload dispatched to notification channels.
    """

    project_id: int | None = Field(default=None, description="Optional database project ID")
    title: str = Field(description="Project or opportunity title")
    source: str = Field(description="Discovery source name (e.g. Hacker News)")
    source_url: str = Field(description="Direct link to source posting")
    overall_score: float = Field(ge=0.0, le=100.0, description="Composite opportunity score")
    recommendation: str = Field(description="Decision tier (e.g. APPLY_IMMEDIATELY)")
    budget_display: str = Field(default="Unstated", description="Human-readable budget display")
    skills: list[str] = Field(default_factory=list, description="Required or matched skills")
    explanation: str = Field(description="Detailed opportunity audit summary")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Notification creation timestamp",
    )
    priority: NotificationPriority = Field(
        default=NotificationPriority.MEDIUM,
        description="Notification urgency priority",
    )


class NotificationResult(BaseModel):
    """
    Result status of a notification dispatch attempt.
    """

    channel: NotificationChannel = Field(description="Channel that handled the dispatch")
    success: bool = Field(description="Whether the notification was successfully delivered")
    delivered_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of delivery attempt",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if delivery failed",
    )
