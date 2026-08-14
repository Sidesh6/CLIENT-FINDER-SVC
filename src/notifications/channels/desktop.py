"""
Desktop notification channel for local OS toast alerts.
"""

import logging
import os
import subprocess
import sys
from datetime import UTC, datetime

from src.notifications.base import BaseNotifier
from src.notifications.schemas import (
    NotificationChannel,
    NotificationPayload,
    NotificationResult,
)

logger = logging.getLogger("DesktopNotifier")


class DesktopNotifier(BaseNotifier):
    """
    Dispatches native desktop toast notifications on Windows, macOS, and Linux.
    """

    channel = NotificationChannel.DESKTOP

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def send(self, payload: NotificationPayload) -> NotificationResult:
        """Display native OS desktop notification."""
        if not self.enabled:
            return NotificationResult(
                channel=self.channel,
                success=True,
                delivered_at=datetime.now(UTC),
                error_message="Channel disabled",
            )

        title = f"[{payload.recommendation}] {payload.title[:40]}"
        message = f"Score: {payload.overall_score}/100 • {payload.budget_display}\n{payload.source}"

        try:
            if sys.platform == "win32":
                # PowerShell balloon / toast fallback on Windows
                escaped_title = title.replace('"', '`"')
                escaped_msg = message.replace('"', '`"').replace("\n", " - ")
                ps_cmd = (
                    f'[reflection.assembly]::loadwithpartialname("System.Windows.Forms") | Out-Null; '
                    f"$notify = new-object system.windows.forms.notifyicon; "
                    f"$notify.icon = [system.drawing.systemicons]::Information; "
                    f"$notify.visible = $true; "
                    f'$notify.showballoontip(5000, "{escaped_title}", "{escaped_msg}", [system.windows.forms.tooltipicon]::Info)'
                )
                subprocess.Popen(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif sys.platform == "darwin":
                # AppleScript on macOS
                escaped_title = title.replace('"', '\\"')
                escaped_msg = message.replace('"', '\\"')
                os.system(
                    f'osascript -e \'display notification "{escaped_msg}" with title "{escaped_title}"\''
                )
            elif sys.platform.startswith("linux"):
                # notify-send on Linux
                os.system(f'notify-send "{title}" "{message}"')

            logger.info("Desktop notification dispatched for '%s'", payload.title[:30])
            return NotificationResult(channel=self.channel, success=True)
        except Exception as exc:
            logger.warning("Desktop notification failed: %s", exc)
            return NotificationResult(channel=self.channel, success=False, error_message=str(exc))

    def send_digest(self, payloads: list[NotificationPayload]) -> NotificationResult:
        """Display desktop summary notification."""
        if not self.enabled or not payloads:
            return NotificationResult(channel=self.channel, success=True)

        summary_payload = NotificationPayload(
            title=f"Digest: {len(payloads)} Opportunities Found",
            source="Client Finder",
            source_url="http://localhost",
            overall_score=payloads[0].overall_score if payloads else 0.0,
            recommendation="OPPORTUNITY DIGEST",
            explanation=f"Found {len(payloads)} matches. Top fit: {payloads[0].title[:40]}",
        )
        return self.send(summary_payload)
