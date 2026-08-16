"""
Client Decision-Maker Contact & Channel Extractor.
Extracts direct founder/client reach-out channels (Email, Calendly, Telegram, Twitter/X, Discord)
from raw client project briefs and descriptions.
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClientContactDetails:
    """Extracted direct reach-out channels for a client or founder."""

    emails: list[str] = field(default_factory=list)
    calendly_links: list[str] = field(default_factory=list)
    telegram_handles: list[str] = field(default_factory=list)
    twitter_handles: list[str] = field(default_factory=list)
    discord_handles: list[str] = field(default_factory=list)
    websites: list[str] = field(default_factory=list)
    primary_channel: str = "DIRECT_LINK"
    primary_action_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "emails": self.emails,
            "calendly_links": self.calendly_links,
            "telegram_handles": self.telegram_handles,
            "twitter_handles": self.twitter_handles,
            "discord_handles": self.discord_handles,
            "websites": self.websites,
            "primary_channel": self.primary_channel,
            "primary_action_url": self.primary_action_url,
        }


class ClientContactExtractor:
    """
    Parses unstructured text to discover direct founder contact mechanisms.
    """

    # Email pattern (handles obfuscated emails e.g. founder [at] domain [dot] com)
    EMAIL_REGEX = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    )
    OBFUSCATED_EMAIL_REGEX = re.compile(
        r"\b([A-Za-z0-9._%+-]+)\s*(?:\[at\]|\(at\)|@|\sat\s)\s*([A-Za-z0-9.-]+)\s*(?:\[dot\]|\(dot\)|\.|\sdot\s)\s*([A-Za-z]{2,7})\b",
        re.IGNORECASE,
    )

    # Booking links (Calendly, Cal.com, SavvyCal)
    CALENDLY_REGEX = re.compile(
        r"https?://(?:www\.)?(?:calendly\.com|cal\.com|savvycal\.com)/[A-Za-z0-9_/-]+",
        re.IGNORECASE,
    )

    # Telegram links or handles
    TELEGRAM_REGEX = re.compile(
        r"(?:https?://(?:t\.me|telegram\.me)/[A-Za-z0-9_]+|@([A-Za-z0-9_]{5,32}))",
        re.IGNORECASE,
    )

    # Twitter / X handles
    TWITTER_REGEX = re.compile(
        r"https?://(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)",
        re.IGNORECASE,
    )

    # Generic website URLs
    WEBSITE_REGEX = re.compile(
        r"https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)",
        re.IGNORECASE,
    )

    def extract(self, text: str, default_url: str = "") -> ClientContactDetails:
        """
        Extract all discoverable contact methods from a client post or project description.
        """
        details = ClientContactDetails()
        if not text:
            details.primary_action_url = default_url
            return details

        # 1. Direct Emails
        raw_emails = self.EMAIL_REGEX.findall(text)
        for email in raw_emails:
            lower = email.lower()
            # Ignore common dummy or library emails
            if not any(dummy in lower for dummy in ("example.com", "yourdomain.com", "test.com", "schema.org")):
                if lower not in details.emails:
                    details.emails.append(lower)

        # Obfuscated emails e.g. "alex at mycompany dot com"
        for match in self.OBFUSCATED_EMAIL_REGEX.finditer(text):
            reconstructed = f"{match.group(1)}@{match.group(2)}.{match.group(3)}".lower()
            if reconstructed not in details.emails and "@" in reconstructed:
                details.emails.append(reconstructed)

        # 2. Calendly / Cal.com
        for link in self.CALENDLY_REGEX.findall(text):
            if link not in details.calendly_links:
                details.calendly_links.append(link)

        # 3. Twitter / X
        for t_link in self.TWITTER_REGEX.findall(text):
            handle = f"@{t_link}"
            if handle not in details.twitter_handles:
                details.twitter_handles.append(handle)

        # 4. Telegram
        for tg_match in self.TELEGRAM_REGEX.finditer(text):
            tg_text = tg_match.group(0)
            if tg_text not in details.telegram_handles:
                details.telegram_handles.append(tg_text)

        # Set Primary Reach-out Action
        if details.emails:
            details.primary_channel = "EMAIL"
            details.primary_action_url = f"mailto:{details.emails[0]}"
        elif details.calendly_links:
            details.primary_channel = "CALENDLY"
            details.primary_action_url = details.calendly_links[0]
        elif details.telegram_handles:
            details.primary_channel = "TELEGRAM"
            tg = details.telegram_handles[0]
            details.primary_action_url = tg if tg.startswith("http") else f"https://t.me/{tg.lstrip('@')}"
        elif details.twitter_handles:
            details.primary_channel = "TWITTER_DM"
            details.primary_action_url = f"https://x.com/{details.twitter_handles[0].lstrip('@')}"
        else:
            details.primary_channel = "SOURCE_LINK"
            details.primary_action_url = default_url

        return details


GLOBAL_CONTACT_EXTRACTOR = ClientContactExtractor()
