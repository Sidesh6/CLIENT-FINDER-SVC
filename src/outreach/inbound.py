"""
Inbound Reply Parser & Intent Classifier.
Analyzes incoming client communications, detects commercial intent/objections, automates funnel state transitions, and drafts replies.
"""

import logging

from src.database.models import ApplicationStatus
from src.models.profile import UserProfile, get_default_profile
from src.outreach.schemas import (
    InboundReplyAnalysisResult,
    InboundReplyRequest,
    IntentType,
)
from src.outreach.sequences import GLOBAL_OUTREACH_ENGINE
from src.tracking.tracker import ApplicationTracker

logger = logging.getLogger("InboundReplyClassifier")


class InboundReplyClassifier:
    """
    Classifies incoming prospect replies, calculates sentiment, and recommends/applies status transitions.
    """

    def __init__(self, default_profile: UserProfile | None = None):
        self.default_profile = default_profile or get_default_profile()

    def analyze_reply(
        self,
        req: InboundReplyRequest,
        update_db: bool = True,
        profile: UserProfile | None = None,
    ) -> InboundReplyAnalysisResult:
        """
        Parse raw message text, extract intent and objections, generate draft response, and optionally update DB.
        """
        user_prof = profile or self.default_profile
        text = req.message_text.strip()
        lower_text = text.lower()
        dev_name = user_prof.name
        client = req.client_name or "Client"
        project_title = req.project_title or "this project"

        # 1. Intent & Sentiment Classification
        intent, confidence, sentiment, objections, key_points = self._classify_text(lower_text)

        # 2. Determine recommended funnel status
        rec_status, rec_action = self._determine_status_and_action(intent)

        # 3. Synthesize Suggested Response Draft
        draft_reply = self._generate_response_draft(
            intent=intent,
            client=client,
            project_title=project_title,
            dev_name=dev_name,
            objections=objections,
        )

        # 4. Optional Database Transition & Sequence Auto-Cancellation
        status_updated = False
        if update_db and req.application_id:
            status_updated = self._apply_db_transition(
                app_id=req.application_id,
                rec_status=rec_status,
                notes=f"Inbound reply detected: {intent.value} (Confidence: {confidence:.2f})",
            )

        return InboundReplyAnalysisResult(
            classified_intent=intent,
            confidence=confidence,
            sentiment_score=sentiment,
            detected_objections=objections,
            key_extracted_points=key_points,
            recommended_funnel_status=rec_status,
            recommended_next_action=rec_action,
            suggested_response_draft=draft_reply,
            application_status_updated=status_updated,
        )

    def _classify_text(
        self, lower_text: str
    ) -> tuple[IntentType, float, float, list[str], list[str]]:
        """Rule-based NLP heuristic classification for commercial reply intent."""
        objections: list[str] = []
        key_points: list[str] = []

        # Check for Out of Office
        if any(
            k in lower_text
            for k in [
                "out of the office",
                "out of office",
                "automatic reply",
                "auto-reply",
                "on vacation",
                "limited email access",
                "returning on",
            ]
        ):
            return (
                IntentType.OUT_OF_OFFICE,
                0.95,
                0.0,
                [],
                ["Automated out-of-office autoreply received."],
            )

        # Check for Rejection
        if any(
            k in lower_text
            for k in [
                "not interested",
                "already hired",
                "position filled",
                "filled the position",
                "filled the role",
                "went with another",
                "no longer looking",
                "decline",
                "not a good fit",
                "passed on",
            ]
        ):
            objections.append("ROLE_FILLED_OR_UNAVAILABLE")
            return (
                IntentType.REJECTION,
                0.90,
                -0.7,
                objections,
                ["Client decided to proceed with another candidate or cancelled opening."],
            )

        # Check for Rate Pushback
        if any(
            k in lower_text
            for k in [
                "rate is too high",
                "expensive",
                "out of budget",
                "over our budget",
                "cheaper",
                "discount",
                "lower your rate",
                "lower rate",
                "fixed price instead",
                "tight budget",
                "budget is tight",
            ]
        ):
            objections.append("BUDGET_TOO_HIGH")
            key_points.append("Client pushed back on proposed commercial rates or budget.")
            return (
                IntentType.RATE_PUSHBACK,
                0.88,
                -0.2,
                objections,
                key_points,
            )

        # Check for Scheduling Call
        if any(
            k in lower_text
            for k in [
                "schedule a call",
                "schedule a zoom",
                "zoom call",
                "zoom",
                "hop on a call",
                "jump on zoom",
                "google meet",
                "calendly",
                "interview",
                "free to chat",
                "available for a quick",
                "available for a call",
                "phone number",
                "when are you available",
                "book a time",
                "let's talk",
                "let's connect",
                "free for a call",
            ]
        ):
            key_points.append("Client invited to a technical discovery or interview call.")
            return (
                IntentType.SCHEDULE_CALL,
                0.92,
                0.8,
                [],
                key_points,
            )

        # Check for Scope Question
        if (
            any(
                k in lower_text
                for k in [
                    "can you also",
                    "do you have experience with",
                    "how do you handle",
                    "what is your timeline",
                    "architecture",
                    "tech stack",
                    "questions about",
                ]
            )
            or "?" in lower_text
        ):
            key_points.append("Client asked exploratory technical or architectural questions.")
            return (
                IntentType.SCOPE_QUESTION,
                0.78,
                0.3,
                [],
                key_points,
            )

        # Check for General Positive Interest
        if any(
            k in lower_text
            for k in [
                "interested",
                "sounds great",
                "sounds good",
                "like your background",
                "send portfolio",
                "tell me more",
                "impressed",
                "move forward",
                "looks promising",
            ]
        ):
            key_points.append("Client expressed positive interest in exploring engagement.")
            return (
                IntentType.POSITIVE_INTEREST,
                0.85,
                0.7,
                [],
                key_points,
            )

        return (
            IntentType.UNCERTAIN,
            0.50,
            0.1,
            [],
            ["Uncertain or ambiguous response. Manual review recommended."],
        )

    def _determine_status_and_action(self, intent: IntentType) -> tuple[str, str]:
        """Maps classified intent to ApplicationStatus and next tactical action."""
        if intent == IntentType.SCHEDULE_CALL:
            return (
                "INTERVIEW",
                "Send booking link and review Technical Interview Prep cheatsheet.",
            )
        if intent == IntentType.RATE_PUSHBACK:
            return (
                "NEGOTIATION",
                "Deploy Closing Studio objection counter-offer (Scope Modulation or Milestone Split).",
            )
        if intent in (IntentType.POSITIVE_INTEREST, IntentType.SCOPE_QUESTION):
            return (
                "CLIENT_REPLIED",
                "Send diagnostic response answering technical questions and invite to brief alignment chat.",
            )
        if intent == IntentType.REJECTION:
            return (
                "LOST",
                "Send gracious closing loop response and archive opportunity in CRM.",
            )
        if intent == IntentType.OUT_OF_OFFICE:
            return (
                "APPLIED",
                "Snooze outreach sequence until return date mentioned in autoreply.",
            )
        return ("CLIENT_REPLIED", "Review client message manually and draft custom reply.")

    def _generate_response_draft(
        self,
        intent: IntentType,
        client: str,
        project_title: str,
        dev_name: str,
        objections: list[str],
    ) -> str:
        """Synthesize immediate contextual reply draft based on intent."""
        if intent == IntentType.SCHEDULE_CALL:
            return (
                f"Hi {client},\n\n"
                f"Thanks for getting back to me! I'd love to connect.\n\n"
                f"I'm generally available between 9:00 AM – 5:00 PM EST. Feel free to grab a 15-minute slot on my calendar or let me know a couple of times that work best for you:\n"
                f"- Tuesday: 10:00 AM or 2:00 PM EST\n"
                f"- Wednesday: 11:00 AM or 3:30 PM EST\n\n"
                f"Looking forward to discussing {project_title}!\n\n"
                f"Best,\n{dev_name}"
            )
        if intent == IntentType.RATE_PUSHBACK:
            return (
                f"Hi {client},\n\n"
                f"Thanks for the transparent feedback on budget. I completely understand wanting to ensure cost predictability for {project_title}.\n\n"
                f"To keep within your budget while maintaining senior architectural quality, I recommend we phase the deliverables:\n"
                f"1. Phase 1 (Core MVP): Deliver the essential backend/API foundations and critical features.\n"
                f"2. Phase 2 (Enhancements): Secondary integrations and nice-to-haves.\n\n"
                f"This allows us to get live and validate the core value immediately within your exact target range. Would you be open to a quick 10-minute alignment chat to discuss this milestone breakdown?\n\n"
                f"Best,\n{dev_name}"
            )
        if intent == IntentType.SCOPE_QUESTION:
            return (
                f"Hi {client},\n\n"
                f"Great questions regarding the technical scope for {project_title}. In past implementations, I solve this by "
                f"decoupling the core business logic from asynchronous worker queues and applying strict Pydantic validation on all external feeds.\n\n"
                f"This ensures seamless scalability, zero data loss, and predictable latency.\n\n"
                f"Happy to walk through a quick diagram or jump on a 10-minute call whenever convenient for you.\n\n"
                f"Best,\n{dev_name}"
            )
        if intent == IntentType.REJECTION:
            return (
                f"Hi {client},\n\n"
                f"Thank you for letting me know! Best of luck with {project_title}.\n\n"
                f"If you ever need senior development or architecture assistance on future initiatives, please feel free to reach out.\n\n"
                f"Best regards,\n{dev_name}"
            )
        if intent == IntentType.OUT_OF_OFFICE:
            return "(Autoreply received - no immediate response required. Resume sequence upon return.)"

        # Default / Positive Interest
        return (
            f"Hi {client},\n\n"
            f"Thanks for following up! I'm really excited about what you're building with {project_title}.\n\n"
            f"I have a concrete roadmap ready for the initial milestone and can begin immediately. Would tomorrow morning or afternoon work for a short 10-minute sync to align on specifics?\n\n"
            f"Best,\n{dev_name}"
        )

    def _apply_db_transition(self, app_id: int, rec_status: str, notes: str) -> bool:
        """Apply status transition in the database and auto-cancel pending sequences."""
        from src.tracking.schemas import ApplicationStatusUpdate

        tracker = ApplicationTracker()
        try:
            # Map string to ApplicationStatus enum
            status_enum = ApplicationStatus(rec_status)
            update_payload = ApplicationStatusUpdate(status=status_enum, notes=notes)
            app = tracker.transition_status(app_id=app_id, status_update=update_payload, force=True)
            if app:
                # Cancel pending sequences
                GLOBAL_OUTREACH_ENGINE.handle_application_status_change(
                    application_id=app_id,
                    new_status=rec_status,
                )
                logger.info(
                    "Transitioned app_id=%d to status=%s after inbound reply",
                    app_id,
                    rec_status,
                )
                return True
        except Exception as e:
            logger.warning("Failed to auto-transition app_id=%d in DB: %s", app_id, e)
        return False
