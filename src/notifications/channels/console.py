"""
Console / Terminal notification channel with color-coded CLI output.
"""

import logging
import sys
from datetime import UTC, datetime

from src.notifications.base import BaseNotifier
from src.notifications.schemas import (
    NotificationChannel,
    NotificationPayload,
    NotificationResult,
)

logger = logging.getLogger("ConsoleNotifier")

# ANSI color codes
ANSI_GREEN = "\033[92m"
ANSI_CYAN = "\033[96m"
ANSI_YELLOW = "\033[93m"
ANSI_GRAY = "\033[90m"
ANSI_BOLD = "\033[1m"
ANSI_RESET = "\033[0m"


class ConsoleNotifier(BaseNotifier):
    """
    Prints color-coded opportunity alert cards to the terminal/stdout.
    """

    channel = NotificationChannel.CONSOLE

    def __init__(self, enabled: bool = True, use_colors: bool = True):
        self.enabled = enabled
        self.use_colors = use_colors and hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def send(self, payload: NotificationPayload) -> NotificationResult:
        """Print an individual alert card to stdout."""
        if not self.enabled:
            return NotificationResult(
                channel=self.channel,
                success=True,
                delivered_at=datetime.now(UTC),
                error_message="Channel disabled",
            )

        rec = payload.recommendation
        color = ANSI_GREEN if "APPLY" in rec else ANSI_CYAN if "STRONG" in rec else ANSI_YELLOW

        rec_str = f"{color}{ANSI_BOLD}[{rec}]{ANSI_RESET}" if self.use_colors else f"[{rec}]"
        score_str = (
            f"{color}{ANSI_BOLD}{payload.overall_score}/100{ANSI_RESET}"
            if self.use_colors
            else f"{payload.overall_score}/100"
        )

        skills_str = ", ".join(payload.skills) if payload.skills else "None specified"

        output = (
            f"\n{ANSI_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{ANSI_RESET}\n"
            f"🔔 {rec_str} Score: {score_str} | {payload.title}\n"
            f"   ├─ Source: {payload.source} | Budget: {payload.budget_display}\n"
            f"   ├─ Tech Stack: {skills_str}\n"
            f"   ├─ URL: {payload.source_url}\n"
            f"   └─ Summary: {payload.explanation}\n"
            f"{ANSI_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{ANSI_RESET}"
        )

        print(output)
        return NotificationResult(channel=self.channel, success=True)

    def send_digest(self, payloads: list[NotificationPayload]) -> NotificationResult:
        """Print a summary table of opportunities."""
        if not self.enabled:
            return NotificationResult(channel=self.channel, success=True)

        print(f"\n📢 OPPORTUNITY DIGEST: {len(payloads)} Matched Opportunities")
        print("─" * 76)
        for idx, p in enumerate(payloads, 1):
            print(
                f"{idx:2d}. [{p.overall_score:4.1f}/100] [{p.recommendation:17s}] {p.title[:45]}..."
            )
        print("─" * 76)

        return NotificationResult(channel=self.channel, success=True)
