"""
Notification formatters and message templates for Console, Discord, Slack, and Email.
"""

from typing import Any

from src.notifications.schemas import NotificationPayload

# Discord Embed Color Hex Codes (integer)
DISCORD_COLORS = {
    "APPLY_IMMEDIATELY": 0x22C55E,  # Green
    "STRONG_PROSPECT": 0x3B82F6,  # Blue
    "CONSIDER": 0xEAB308,  # Yellow
    "SKIP": 0x64748B,  # Gray
}


def format_discord_embed(payload: NotificationPayload) -> dict[str, Any]:
    """
    Format a NotificationPayload into a rich Discord webhook embed payload.
    """
    color = DISCORD_COLORS.get(payload.recommendation, 0x3B82F6)
    skills_str = ", ".join(payload.skills) if payload.skills else "None specified"

    embed = {
        "title": f"🎯 [{payload.recommendation}] {payload.title[:200]}",
        "url": payload.source_url,
        "color": color,
        "description": payload.explanation,
        "fields": [
            {
                "name": "⭐ Overall Score",
                "value": f"**{payload.overall_score}/100**",
                "inline": True,
            },
            {
                "name": "💰 Budget / Rate",
                "value": payload.budget_display,
                "inline": True,
            },
            {
                "name": "📍 Source",
                "value": payload.source,
                "inline": True,
            },
            {
                "name": "🛠️ Skills",
                "value": f"`{skills_str}`",
                "inline": False,
            },
        ],
        "footer": {
            "text": "Client Finder Service • Real-Time Opportunity Alert",
        },
        "timestamp": payload.timestamp.isoformat(),
    }

    return {
        "username": "Client Finder Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/4712/4712109.png",
        "embeds": [embed],
    }


def format_slack_blocks(payload: NotificationPayload) -> dict[str, Any]:
    """
    Format a NotificationPayload into a Slack Block Kit payload.
    """
    skills_str = ", ".join(payload.skills) if payload.skills else "None specified"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎯 New Opportunity: {payload.recommendation}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<{payload.source_url}|{payload.title}>*\n{payload.explanation}",
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Score:* `{payload.overall_score}/100`",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Budget:* {payload.budget_display}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Source:* {payload.source}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Skills:* `{skills_str}`",
                },
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Opportunity ↗",
                        "emoji": True,
                    },
                    "url": payload.source_url,
                    "style": "primary" if "APPLY" in payload.recommendation else "default",
                }
            ],
        },
        {"type": "divider"},
    ]

    return {"blocks": blocks}


def format_html_email(payload: NotificationPayload) -> str:
    """
    Generate responsive HTML email with inline styling.
    """
    skills_html = (
        "".join(
            f'<span style="background-color:#e2e8f0; color:#334155; padding:3px 8px; border-radius:4px; margin-right:4px; font-size:12px;">{s}</span>'
            for s in payload.skills
        )
        if payload.skills
        else '<span style="color:#94a3b8; font-size:12px;">None specified</span>'
    )

    badge_color = "#22c55e" if "APPLY" in payload.recommendation else "#3b82f6"

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <div style="background-color: #0f172a; padding: 20px 24px; color: #ffffff;">
            <span style="background-color: {badge_color}; color: #ffffff; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                {payload.recommendation}
            </span>
            <h2 style="margin: 12px 0 0 0; font-size: 18px; line-height: 1.4; color: #ffffff;">{payload.title}</h2>
        </div>
        <div style="padding: 24px;">
            <div style="display: flex; margin-bottom: 16px;">
                <div style="flex: 1; padding: 12px; background-color: #f1f5f9; border-radius: 6px; margin-right: 8px;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 600;">Overall Match</div>
                    <div style="font-size: 20px; font-weight: 700; color: #0f172a;">{payload.overall_score}/100</div>
                </div>
                <div style="flex: 1; padding: 12px; background-color: #f1f5f9; border-radius: 6px; margin-right: 8px;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 600;">Budget / Rate</div>
                    <div style="font-size: 16px; font-weight: 600; color: #0f172a; margin-top: 2px;">{payload.budget_display}</div>
                </div>
                <div style="flex: 1; padding: 12px; background-color: #f1f5f9; border-radius: 6px;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 600;">Source</div>
                    <div style="font-size: 16px; font-weight: 600; color: #0f172a; margin-top: 2px;">{payload.source}</div>
                </div>
            </div>

            <div style="margin-bottom: 16px;">
                <div style="font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 6px;">TECH STACK</div>
                <div>{skills_html}</div>
            </div>

            <div style="margin-bottom: 24px; padding: 14px; background-color: #f8fafc; border-left: 4px solid {badge_color}; border-radius: 0 4px 4px 0;">
                <div style="font-size: 12px; color: #475569; line-height: 1.5;">{payload.explanation}</div>
            </div>

            <div style="text-align: center;">
                <a href="{payload.source_url}" style="display: inline-block; background-color: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px;">
                    View & Apply to Opportunity ↗
                </a>
            </div>
        </div>
        <div style="background-color: #f8fafc; padding: 12px 24px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center;">
            Client Finder Service • Automated Opportunity Notification
        </div>
    </div>
</body>
</html>"""


def format_plaintext_email(payload: NotificationPayload) -> str:
    """
    Plaintext email body fallback.
    """
    skills_str = ", ".join(payload.skills) if payload.skills else "None specified"
    return f"""===================================================================
TARGET OPPORTUNITY ALERT: [{payload.recommendation}]
===================================================================
Title        : {payload.title}
Overall Score: {payload.overall_score}/100
Budget / Rate: {payload.budget_display}
Source       : {payload.source}
Skills       : {skills_str}
Link         : {payload.source_url}

Analysis:
{payload.explanation}

--
Client Finder Service
"""
