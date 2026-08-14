"""
Context-Aware Proposal Follow-Up and Cold Lead Re-engagement Cadence Manager.
Generates non-intrusive, value-adding messages optimized for conversion across the client journey.
"""

import logging
from enum import Enum

from pydantic import BaseModel, Field

from src.models.profile import UserProfile, get_default_profile

logger = logging.getLogger("FollowUpManager")


class FollowUpStage(str, Enum):
    """Timing stages across the post-proposal follow-up sequence."""

    DAY_3_CHECKIN = "DAY_3_CHECKIN"
    DAY_7_VALUE_ADD = "DAY_7_VALUE_ADD"
    DAY_14_BREAKUP = "DAY_14_BREAKUP"
    REVIVE_COLD_LEAD = "REVIVE_COLD_LEAD"


class FollowUpRequest(BaseModel):
    """Inbound request payload for follow-up message generation."""

    project_title: str = Field(description="Title of target project")
    project_description: str = Field(description="Summary of project requirements")
    client_name: str | None = Field(default=None, description="Client or poster name")
    stage: FollowUpStage = Field(default=FollowUpStage.DAY_3_CHECKIN, description="Cadence stage")
    days_elapsed: int = Field(default=3, ge=1, description="Days elapsed since initial proposal")
    proposal_summary: str | None = Field(
        default=None, description="Brief summary of original proposal pitch"
    )


class FollowUpResponse(BaseModel):
    """Structured follow-up message with timing recommendations."""

    stage: FollowUpStage
    subject_line: str
    body_text: str
    strategic_intent: str
    recommended_send_timing: str


class FollowUpManager:
    """
    Automates synthesis of strategic follow-up messages based on elapsed time and project context.
    """

    def __init__(self, default_profile: UserProfile | None = None):
        self.default_profile = default_profile or get_default_profile()

    def generate(
        self,
        req: FollowUpRequest,
        profile: UserProfile | None = None,
    ) -> FollowUpResponse:
        """
        Synthesize follow-up message tailored to the specific cadence stage.
        """
        user_prof = profile or self.default_profile
        greeting = f"Hi {req.client_name}," if req.client_name else "Hi there,"

        if req.stage == FollowUpStage.DAY_3_CHECKIN:
            subject = f"Quick follow-up regarding {req.project_title}"
            body = (
                f"{greeting}\n\n"
                f"I wanted to briefly follow up on my earlier proposal for '{req.project_title}'. "
                f"I know reviewing candidates takes time, so I just wanted to confirm you received everything and see if you had any "
                f"questions about my proposed technical approach or roadmap.\n\n"
                f"I'm currently finalizing my availability for next week and would love to reserve a sprint slot for your project. "
                f"Are you free for a quick 10-minute chat this Tuesday or Wednesday?\n\n"
                f"Best regards,\n{user_prof.name}"
            )
            intent = "Light confirmation touchpoint verifying receipt and creating subtle urgency with calendar scheduling."
            timing = "Send 3 business days after initial proposal submission in morning hours (9-11 AM client timezone)."

        elif req.stage == FollowUpStage.DAY_7_VALUE_ADD:
            subject = f"Idea for your {req.project_title} architecture"
            body = (
                f"{greeting}\n\n"
                f"While reviewing the requirements for '{req.project_title}' this week, I put together a quick architectural concept "
                f"that could potentially save substantial development time on the core data pipeline.\n\n"
                f"Specifically, using an async queue and modular schema design will allow zero-downtime scaling as your user base expands. "
                f"I'd be happy to record a quick 2-minute Loom walkthrough or share the diagram if that would be helpful for your team.\n\n"
                f"Let me know if you'd like me to send that over!\n\n"
                f"Best,\n{user_prof.name}"
            )
            intent = "Deliver unsolicited value and demonstrate proactive domain expertise without asking for an immediate contract."
            timing = "Send 7 days after initial proposal."

        elif req.stage == FollowUpStage.DAY_14_BREAKUP:
            subject = f"Permission to close the loop on {req.project_title}?"
            body = (
                f"{greeting}\n\n"
                f"I haven't heard back regarding '{req.project_title}', so I'm assuming you've either filled the role or the project "
                f"priorities have shifted—which is completely fine!\n\n"
                f"I'll close out my file for now so I don't clutter your inbox. If you ever need assistance with Python, FastAPI, or "
                f"autonomous AI systems down the line, feel free to reach back out anytime.\n\n"
                f"Wishing you and your team continued success!\n\n"
                f"Best regards,\n{user_prof.name}"
            )
            intent = "Reverse-psychology breakup email that prompts action from busy founders who intended to reply."
            timing = "Send 14-20 days post-proposal."

        else:  # REVIVE_COLD_LEAD
            subject = f"New case study relevant to {req.project_title}"
            body = (
                f"{greeting}\n\n"
                f"I hope you're having a productive month! I recently wrapped up a project very similar to what we discussed for "
                f"'{req.project_title}'—building an automated data extraction and AI ranking pipeline that achieved 99.4% uptime and 4x faster processing.\n\n"
                f"It reminded me of your initiative, and I wanted to check in to see if you have any upcoming development cycles "
                f"where an experienced engineer could help accelerate your roadmap.\n\n"
                f"Best,\n{user_prof.name}"
            )
            intent = (
                "Re-engage cold leads with verified social proof and tangible recent achievements."
            )
            timing = "Send 30-60 days after last correspondence."

        return FollowUpResponse(
            stage=req.stage,
            subject_line=subject,
            body_text=body,
            strategic_intent=intent,
            recommended_send_timing=timing,
        )
