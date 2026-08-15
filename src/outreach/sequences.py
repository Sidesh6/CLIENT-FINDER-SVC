"""
Outreach Sequence Engine.
Orchestrates multi-touch client outreach schedules, step synthesis, cadence progression, and auto-cancellation.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from src.models.profile import UserProfile, get_default_profile
from src.outreach.schemas import (
    OutreachSequenceCreate,
    OutreachSequenceResult,
    OutreachStep,
    SequenceStatus,
    SequenceStepType,
    StepStatus,
)
from src.proposal.schemas import PitchAngle

logger = logging.getLogger("OutreachSequenceEngine")


class OutreachSequenceEngine:
    """
    Manages automated multi-touch outreach cadences, step generation, and execution progression.
    """

    def __init__(self, default_profile: UserProfile | None = None):
        self.default_profile = default_profile or get_default_profile()
        self._sequences: dict[str, OutreachSequenceResult] = {}

    def create_sequence(
        self,
        req: OutreachSequenceCreate,
        profile: UserProfile | None = None,
    ) -> OutreachSequenceResult:
        """
        Generate and register a 5-step automated outreach sequence.
        """
        user_prof = profile or self.default_profile
        dev_name = user_prof.name
        client = req.client_name or "Client"
        title = req.project_title
        skills = req.target_skills or ["Python", "FastAPI", "PostgreSQL"]
        skills_str = ", ".join(skills[:3])
        budget_str = f"${req.proposed_budget:,.2f}" if req.proposed_budget else "the agreed budget"

        seq_id = f"seq_{uuid.uuid4().hex[:10]}"
        now = datetime.now(UTC)

        # Step 1: Initial Proposal (Day 0)
        s1_copy = self._synthesize_initial_pitch(
            client=client,
            title=title,
            skills_str=skills_str,
            dev_name=dev_name,
            pitch_angle=req.pitch_angle,
            budget_str=budget_str,
        )
        step1 = OutreachStep(
            step_index=1,
            step_type=SequenceStepType.INITIAL_PROPOSAL,
            delay_days=0,
            subject=f"Proposal: {title} — {dev_name}",
            message_content=s1_copy,
            status=StepStatus.EXECUTED if req.auto_start else StepStatus.PENDING,
            scheduled_for=now,
            executed_at=now if req.auto_start else None,
        )

        # Step 2: Day 3 Technical Diagnosis
        step2 = OutreachStep(
            step_index=2,
            step_type=SequenceStepType.DAY_3_DIAGNOSIS,
            delay_days=3,
            subject=f"Quick technical note regarding {title}",
            message_content=(
                f"Hi {client},\n\n"
                f"Following up on my proposal for {title}. While reviewing the architecture requirements for {skills_str}, "
                f"I put together a quick outline of how to handle asynchronous worker queuing, connection pooling, and fault tolerance "
                f"to prevent downtime under peak traffic.\n\n"
                f"Happy to walk through this 1-page breakdown over a brief 10-minute chat this week if helpful.\n\n"
                f"Best,\n{dev_name}"
            ),
            status=StepStatus.PENDING,
            scheduled_for=now + timedelta(days=3),
        )

        # Step 3: Day 7 Case Study & Proof
        step3 = OutreachStep(
            step_index=3,
            step_type=SequenceStepType.DAY_7_CASE_STUDY,
            delay_days=7,
            subject=f"Relevant case study for {title}",
            message_content=(
                f"Hi {client},\n\n"
                f"Sharing a relevant benchmark: I recently completed a similar implementation using {skills_str} where we "
                f"cut API latency by 42% and achieved zero-downtime deployments. Built with strict typing and automated test suites.\n\n"
                f"Are you still actively looking to kick off {title}? Let me know if you'd like to see the live demo.\n\n"
                f"Best,\n{dev_name}"
            ),
            status=StepStatus.PENDING,
            scheduled_for=now + timedelta(days=7),
        )

        # Step 4: Day 14 Breakup Pitch
        step4 = OutreachStep(
            step_index=4,
            step_type=SequenceStepType.DAY_14_BREAKUP,
            delay_days=14,
            subject=f"Closing the loop on {title}",
            message_content=(
                f"Hi {client},\n\n"
                f"I know how busy things get when launching new initiatives. Since I haven't heard back, I'll assume your priorities "
                f"have shifted or you've already found another engineer for {title}.\n\n"
                f"I'm closing out my file on this for now. If you ever need senior {skills_str} help down the road, feel free to reach back out.\n\n"
                f"Wishing you continued success!\n\n"
                f"Best regards,\n{dev_name}"
            ),
            status=StepStatus.PENDING,
            scheduled_for=now + timedelta(days=14),
        )

        # Step 5: Day 30 Revive Lead
        step5 = OutreachStep(
            step_index=5,
            step_type=SequenceStepType.DAY_30_REVIVE,
            delay_days=30,
            subject=f"Checking in — {title} & {skills_str}",
            message_content=(
                f"Hi {client},\n\n"
                f"Hope all is going well! Circling back to see how the {title} initiative unfolded. "
                f"I currently have an open sprint window starting next week and thought of your project.\n\n"
                f"If you are planning a Phase 2 or have any new technical bottlenecks in {skills_str}, I'd be happy to reconnect.\n\n"
                f"Best,\n{dev_name}"
            ),
            status=StepStatus.PENDING,
            scheduled_for=now + timedelta(days=30),
        )

        seq_result = OutreachSequenceResult(
            sequence_id=seq_id,
            application_id=req.application_id,
            project_title=title,
            client_name=client,
            pitch_angle=req.pitch_angle,
            status=SequenceStatus.ACTIVE if req.auto_start else SequenceStatus.PENDING,
            current_step_index=2 if req.auto_start else 1,
            total_steps=5,
            created_at=now,
            updated_at=now,
            steps=[step1, step2, step3, step4, step5],
        )

        self._sequences[seq_id] = seq_result
        logger.info(
            "Created outreach sequence %s for app_id=%d (%s)",
            seq_id,
            req.application_id,
            title,
        )
        return seq_result

    def _synthesize_initial_pitch(
        self,
        client: str,
        title: str,
        skills_str: str,
        dev_name: str,
        pitch_angle: PitchAngle,
        budget_str: str,
    ) -> str:
        """Synthesize tailored initial proposal text based on pitch angle."""
        if pitch_angle == PitchAngle.TECHNICAL_EXPERT:
            return (
                f"Hi {client},\n\n"
                f"I reviewed your requirements for '{title}'. As a senior software engineer specializing in {skills_str}, "
                f"I build scalable, modular architectures with 90%+ test coverage, automated CI/CD, and robust error resilience.\n\n"
                f"I can deliver this within {budget_str} across clear, demonstrable milestones.\n\n"
                f"Are you free for a quick 10-minute introductory call this week?\n\n"
                f"Best,\n{dev_name}"
            )
        if pitch_angle == PitchAngle.FAST_DELIVERY:
            return (
                f"Hi {client},\n\n"
                f"I have immediate availability to start '{title}' today and deliver an initial working staging build in 5 business days using {skills_str}.\n\n"
                f"Zero ramp-up time needed. Ready to begin immediately within {budget_str}.\n\n"
                f"Let me know if you'd like to sync today!\n\n"
                f"Best,\n{dev_name}"
            )
        if pitch_angle == PitchAngle.VALUE_ROI:
            return (
                f"Hi {client},\n\n"
                f"Regarding '{title}': my focus is maximizing commercial ROI by delivering high-throughput, maintainable software in {skills_str} "
                f"that lowers long-term cloud hosting and maintenance costs.\n\n"
                f"Proposed milestone investment: {budget_str}.\n\n"
                f"When is a good time for a short alignment chat?\n\n"
                f"Best,\n{dev_name}"
            )
        # Default / Consultative
        return (
            f"Hi {client},\n\n"
            f"I came across '{title}' and would love to assist. Based on your target tech stack ({skills_str}), "
            f"I recommend a phased milestone structure that delivers value in iterative 1-week sprints.\n\n"
            f"Would you be open to a brief call to align on your launch milestones?\n\n"
            f"Best,\n{dev_name}"
        )

    def advance_step(self, sequence_id: str) -> OutreachSequenceResult:
        """
        Execute the current pending step and advance cadence.
        """
        seq = self._sequences.get(sequence_id)
        if not seq:
            raise KeyError(f"Sequence with ID '{sequence_id}' not found.")

        if seq.status not in (SequenceStatus.ACTIVE, SequenceStatus.PENDING):
            logger.warning(
                "Cannot advance sequence %s because status is %s", sequence_id, seq.status
            )
            return seq

        idx = seq.current_step_index
        now = datetime.now(UTC)

        # Mark current step as executed
        for step in seq.steps:
            if step.step_index == idx:
                step.status = StepStatus.EXECUTED
                step.executed_at = now
                break

        if idx >= seq.total_steps:
            seq.status = SequenceStatus.COMPLETED
            logger.info("Sequence %s completed all steps.", sequence_id)
        else:
            seq.current_step_index = idx + 1
            seq.status = SequenceStatus.ACTIVE

        seq.updated_at = now
        return seq

    def pause_sequence(self, sequence_id: str) -> OutreachSequenceResult:
        """Pause active outreach cadence."""
        seq = self._sequences.get(sequence_id)
        if not seq:
            raise KeyError(f"Sequence with ID '{sequence_id}' not found.")
        seq.status = SequenceStatus.PAUSED
        seq.updated_at = datetime.now(UTC)
        logger.info("Paused sequence %s", sequence_id)
        return seq

    def resume_sequence(self, sequence_id: str) -> OutreachSequenceResult:
        """Resume paused outreach cadence."""
        seq = self._sequences.get(sequence_id)
        if not seq:
            raise KeyError(f"Sequence with ID '{sequence_id}' not found.")
        seq.status = SequenceStatus.ACTIVE
        seq.updated_at = datetime.now(UTC)
        logger.info("Resumed sequence %s", sequence_id)
        return seq

    def cancel_sequence(
        self, sequence_id: str, reason: str = "Manual cancellation"
    ) -> OutreachSequenceResult:
        """Cancel outreach sequence."""
        seq = self._sequences.get(sequence_id)
        if not seq:
            raise KeyError(f"Sequence with ID '{sequence_id}' not found.")
        seq.status = SequenceStatus.CANCELLED
        seq.updated_at = datetime.now(UTC)
        logger.info("Cancelled sequence %s (Reason: %s)", sequence_id, reason)
        return seq

    def get_sequence(self, sequence_id: str) -> OutreachSequenceResult | None:
        """Get sequence by ID."""
        return self._sequences.get(sequence_id)

    def list_sequences(
        self,
        status: SequenceStatus | None = None,
        application_id: int | None = None,
    ) -> list[OutreachSequenceResult]:
        """List all sequences filtered by optional status or application_id."""
        results = list(self._sequences.values())
        if status:
            results = [s for s in results if s.status == status]
        if application_id is not None:
            results = [s for s in results if s.application_id == application_id]
        return sorted(results, key=lambda s: s.updated_at, reverse=True)

    def handle_application_status_change(self, application_id: int, new_status: str) -> int:
        """
        Auto-pause/cancel active sequences if application state advances beyond APPLIED.
        Returns number of sequences updated.
        """
        terminal_or_engaged_statuses = {
            "CLIENT_REPLIED",
            "INTERVIEW",
            "NEGOTIATION",
            "WON",
            "LOST",
            "CANCELLED",
            "COMPLETED",
        }
        if new_status.upper() not in terminal_or_engaged_statuses:
            return 0

        updated = 0
        for seq in self._sequences.values():
            if seq.application_id == application_id and seq.status == SequenceStatus.ACTIVE:
                seq.status = SequenceStatus.CANCELLED
                seq.updated_at = datetime.now(UTC)
                updated += 1
                logger.info(
                    "Auto-cancelled sequence %s due to app_id=%d entering status %s",
                    seq.sequence_id,
                    application_id,
                    new_status,
                )
        return updated


# Default Singleton Instance
GLOBAL_OUTREACH_ENGINE = OutreachSequenceEngine()
