"""
Application Lifecycle Tracker.
Manages application state transitions, timing metrics, and proposal linkages.
"""

import logging

from sqlalchemy.orm import Session, selectinload

from src.database.connection import SessionLocal
from src.database.models import ApplicationModel, ApplicationStatus
from src.proposal.schemas import GeneratedProposal, PitchAngle
from src.tracking.schemas import (
    ApplicationCreate,
    ApplicationFilter,
    ApplicationResponse,
    ApplicationStatusUpdate,
)

logger = logging.getLogger("ApplicationTracker")


# Legal lifecycle transition pathways
ALLOWED_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.DISCOVERED: {
        ApplicationStatus.QUALIFIED,
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.QUALIFIED: {
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.PROPOSAL_GENERATED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.SHORTLISTED: {
        ApplicationStatus.PROPOSAL_GENERATED,
        ApplicationStatus.APPLIED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.PROPOSAL_GENERATED: {
        ApplicationStatus.APPLIED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.APPLIED: {
        ApplicationStatus.CLIENT_REPLIED,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.LOST,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.CLIENT_REPLIED: {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.NEGOTIATION,
        ApplicationStatus.WON,
        ApplicationStatus.LOST,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.INTERVIEW: {
        ApplicationStatus.NEGOTIATION,
        ApplicationStatus.WON,
        ApplicationStatus.LOST,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.NEGOTIATION: {
        ApplicationStatus.WON,
        ApplicationStatus.LOST,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.WON: {
        ApplicationStatus.COMPLETED,
        ApplicationStatus.CANCELLED,
    },
    ApplicationStatus.LOST: set(),
    ApplicationStatus.CANCELLED: set(),
    ApplicationStatus.COMPLETED: set(),
}


class ApplicationTracker:
    """
    Manages the lifecycle, progression, and outcome tracking of client applications.
    """

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def track_application(
        self,
        payload: ApplicationCreate,
        session: Session | None = None,
    ) -> ApplicationModel:
        """
        Record a new application in the database or update an existing application.
        """
        sess = session or self.session_factory()
        own_session = session is None

        try:
            from src.database.repository import ApplicationRepository

            repo = ApplicationRepository(sess)
            pitch_str = payload.pitch_angle.value if payload.pitch_angle else None

            app = repo.create(
                project_id=payload.project_id,
                status=payload.status.value,
                proposed_budget=payload.proposed_budget,
                currency=payload.currency,
                proposal_text=payload.proposal_text,
                pitch_angle=pitch_str,
                notes=payload.notes,
                session=sess,
            )

            if own_session:
                sess.commit()
                sess.refresh(app)

            logger.info(
                "Tracked application #%d for project ID %d (Status: %s)",
                app.id,
                app.project_id,
                app.status,
            )
            return app
        finally:
            if own_session:
                sess.close()

    def record_from_proposal(
        self,
        project_id: int,
        proposal: GeneratedProposal,
        notes: str | None = None,
        session: Session | None = None,
    ) -> ApplicationModel:
        """
        Convenience helper to record an application directly from a generated proposal.
        """
        proposed_budget = None
        if proposal.pricing_quote:
            try:
                import re

                nums = re.findall(r"\d+(?:,\d+)*(?:\.\d+)?", proposal.pricing_quote)
                if nums:
                    proposed_budget = float(nums[0].replace(",", ""))
            except Exception:
                proposed_budget = None

        payload = ApplicationCreate(
            project_id=project_id,
            status=ApplicationStatus.APPLIED,
            proposed_budget=proposed_budget,
            currency="USD",
            proposal_text=proposal.full_proposal_text,
            pitch_angle=proposal.pitch_angle,
            notes=notes
            or f"Auto-created from AI Proposal (Quality Score: {proposal.quality_score})",
        )
        return self.track_application(payload, session=session)

    def transition_status(
        self,
        app_id: int,
        status_update: ApplicationStatusUpdate,
        force: bool = False,
        session: Session | None = None,
    ) -> ApplicationModel:
        """
        Transition application lifecycle status and record outcome timestamps.
        """
        sess = session or self.session_factory()
        own_session = session is None

        try:
            from src.database.repository import ApplicationRepository

            repo = ApplicationRepository(sess)
            app = repo.get_by_id(app_id, session=sess)
            if not app:
                raise ValueError(f"Application #{app_id} not found.")

            current_status = ApplicationStatus(app.status)
            target_status = status_update.status

            if not force and target_status != current_status:
                allowed = ALLOWED_TRANSITIONS.get(current_status, set())
                if target_status not in allowed:
                    logger.warning(
                        "Attempting non-standard lifecycle jump: %s -> %s for Application #%d",
                        current_status.value,
                        target_status.value,
                        app_id,
                    )

            updated = repo.update_status(
                app_id=app_id,
                new_status=target_status.value,
                client_feedback=status_update.client_feedback,
                final_revenue=status_update.final_revenue,
                notes=status_update.notes,
                session=sess,
            )

            if not updated:
                raise ValueError(f"Failed to update application #{app_id}.")

            if own_session:
                sess.commit()
                sess.refresh(updated)

            logger.info("Application #%d transitioned to %s", app_id, target_status.value)

            try:
                from src.api.events import GLOBAL_EVENT_BROADCASTER, EventType

                GLOBAL_EVENT_BROADCASTER.broadcast_sync(
                    event_type=EventType.APPLICATION_UPDATED,
                    data={
                        "application_id": app_id,
                        "project_id": updated.project_id,
                        "new_status": target_status.value,
                    },
                )
            except Exception:
                pass

            return updated
        finally:
            if own_session:
                sess.close()

    def get_application(
        self,
        app_id: int,
        session: Session | None = None,
    ) -> ApplicationResponse | None:
        """
        Fetch application by ID and return enriched response model.
        """
        sess = session or self.session_factory()
        own_session = session is None

        try:
            app = sess.get(
                ApplicationModel,
                app_id,
                options=[selectinload(ApplicationModel.project)],
            )
            if not app:
                return None
            return self._build_response(app)
        finally:
            if own_session:
                sess.close()

    def list_applications(
        self,
        filters: ApplicationFilter,
        session: Session | None = None,
    ) -> list[ApplicationResponse]:
        """
        List applications matching query filters.
        """
        sess = session or self.session_factory()
        own_session = session is None

        try:
            from src.database.repository import ApplicationRepository

            repo = ApplicationRepository(sess)
            status_str = filters.status.value if filters.status else None
            pitch_str = filters.pitch_angle.value if filters.pitch_angle else None

            apps = repo.list_applications(
                status=status_str,
                pitch_angle=pitch_str,
                min_revenue=filters.min_revenue,
                limit=filters.limit,
                offset=filters.offset,
                session=sess,
            )

            return [self._build_response(a) for a in apps]
        finally:
            if own_session:
                sess.close()

    def delete_application(
        self,
        app_id: int,
        session: Session | None = None,
    ) -> bool:
        """
        Remove an application record.
        """
        sess = session or self.session_factory()
        own_session = session is None

        try:
            from src.database.repository import ApplicationRepository

            repo = ApplicationRepository(sess)
            success = repo.delete(app_id, session=sess)
            if own_session and success:
                sess.commit()
            return success
        finally:
            if own_session:
                sess.close()

    def _build_response(self, app: ApplicationModel) -> ApplicationResponse:
        """Construct enriched ApplicationResponse schema with project details."""
        proj = app.project
        pitch_val = PitchAngle(app.pitch_angle) if app.pitch_angle else None

        return ApplicationResponse(
            id=app.id,
            project_id=app.project_id,
            status=ApplicationStatus(app.status),
            applied_at=app.applied_at,
            response_at=app.response_at,
            interview_at=app.interview_at,
            closed_at=app.closed_at,
            proposed_budget=app.proposed_budget,
            final_revenue=app.final_revenue,
            currency=app.currency,
            proposal_text=app.proposal_text,
            pitch_angle=pitch_val,
            client_feedback=app.client_feedback,
            notes=app.notes,
            created_at=app.created_at,
            updated_at=app.updated_at,
            project_title=proj.title if proj else None,
            project_source=proj.source if proj else None,
            project_url=proj.source_url if proj else None,
            overall_score=proj.score if proj else None,
        )
