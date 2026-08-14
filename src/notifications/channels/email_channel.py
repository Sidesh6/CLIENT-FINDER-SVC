"""
Email notification channel using standard SMTP and responsive HTML templates.
"""

import logging
import os
import smtplib
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.notifications.base import BaseNotifier
from src.notifications.schemas import (
    NotificationChannel,
    NotificationPayload,
    NotificationResult,
)
from src.notifications.templates import format_html_email, format_plaintext_email

logger = logging.getLogger("EmailNotifier")


class EmailNotifier(BaseNotifier):
    """
    Delivers responsive HTML emails with plaintext fallback via standard SMTP.
    """

    channel = NotificationChannel.EMAIL

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        sender_email: str | None = None,
        recipient_email: str | None = None,
        enabled: bool = True,
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.sender_email = sender_email or os.getenv("SMTP_SENDER", "alerts@clientfinder.local")
        self.recipient_email = recipient_email or os.getenv("ALERT_RECIPIENT_EMAIL")
        self.use_tls = use_tls
        self.enabled = enabled and bool(self.smtp_host and self.recipient_email)

    def send(self, payload: NotificationPayload) -> NotificationResult:
        """Send HTML email with plaintext fallback."""
        if not self.enabled or not self.smtp_host or not self.recipient_email:
            logger.debug("SMTP host or recipient unconfigured; skipping email dispatch (dry run)")
            return NotificationResult(
                channel=self.channel,
                success=True,
                delivered_at=datetime.now(UTC),
                error_message="Channel disabled or SMTP unconfigured (dry run)",
            )

        subject = (
            f"🎯 [{payload.recommendation} - {payload.overall_score}/100] {payload.title[:60]}"
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = self.recipient_email

        # Attach text & HTML alternatives
        text_part = MIMEText(format_plaintext_email(payload), "plain", "utf-8")
        html_part = MIMEText(format_html_email(payload), "html", "utf-8")
        msg.attach(text_part)
        msg.attach(html_part)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info("Successfully sent alert email to %s", self.recipient_email)
            return NotificationResult(channel=self.channel, success=True)
        except Exception as exc:
            err = f"Failed to send email alert: {exc}"
            logger.error(err)
            return NotificationResult(channel=self.channel, success=False, error_message=err)

    def send_digest(self, payloads: list[NotificationPayload]) -> NotificationResult:
        """Send a digest email summarizing multiple opportunities."""
        if not self.enabled or not self.smtp_host or not self.recipient_email:
            return NotificationResult(channel=self.channel, success=True)

        subject = f"📢 Opportunity Digest: {len(payloads)} Matched Opportunities"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = self.recipient_email

        rows = "".join(
            f"<tr><td style='padding:8px;border-bottom:1px solid #eee;'><b>{p.overall_score}/100</b></td>"
            f"<td style='padding:8px;border-bottom:1px solid #eee;'><a href='{p.source_url}'>{p.title}</a></td>"
            f"<td style='padding:8px;border-bottom:1px solid #eee;'>{p.budget_display}</td></tr>"
            for p in payloads
        )
        html = f"<h2>Daily Opportunity Digest ({len(payloads)} Found)</h2><table style='width:100%;border-collapse:collapse;'>{rows}</table>"

        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10.0) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            return NotificationResult(channel=self.channel, success=True)
        except Exception as exc:
            return NotificationResult(channel=self.channel, success=False, error_message=str(exc))
