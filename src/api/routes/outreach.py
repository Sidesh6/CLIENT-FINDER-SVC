"""
FastAPI REST Endpoints for Autonomous Outreach Sequences, Inbound Intent Parsing, and A/B Testing.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.outreach.experiments import GLOBAL_PROPOSAL_EXPERIMENTER
from src.outreach.inbound import InboundReplyClassifier
from src.outreach.schemas import (
    ABExperimentSummary,
    InboundReplyAnalysisResult,
    InboundReplyRequest,
    OutreachSequenceCreate,
    OutreachSequenceResult,
    SequenceStatus,
)
from src.outreach.sequences import GLOBAL_OUTREACH_ENGINE
from src.proposal.schemas import PitchAngle

router = APIRouter(prefix="/api/outreach", tags=["Outreach & A/B Engine"])

inbound_classifier = InboundReplyClassifier()


class RecordEventPayload(BaseModel):
    """Payload to record an A/B pitch event."""

    pitch_angle: PitchAngle
    event_type: str = Field(
        description="Event type: IMPRESSION, REPLY, or WIN", examples=["IMPRESSION"]
    )
    category: str = Field(default="General", description="Project category")


@router.post("/sequences", response_model=OutreachSequenceResult)
def create_outreach_sequence(req: OutreachSequenceCreate) -> OutreachSequenceResult:
    """
    Initialize an automated 5-step outreach sequence for an application.
    """
    return GLOBAL_OUTREACH_ENGINE.create_sequence(req)


@router.get("/sequences", response_model=list[OutreachSequenceResult])
def list_outreach_sequences(
    status: SequenceStatus | None = Query(
        default=None, description="Filter by sequence lifecycle status"
    ),
    application_id: int | None = Query(
        default=None, description="Filter by target application ID"
    ),
) -> list[OutreachSequenceResult]:
    """
    List tracked outreach sequences and upcoming steps.
    """
    return GLOBAL_OUTREACH_ENGINE.list_sequences(
        status=status, application_id=application_id
    )


@router.get("/sequences/{sequence_id}", response_model=OutreachSequenceResult)
def get_outreach_sequence(sequence_id: str) -> OutreachSequenceResult:
    """
    Retrieve full step timeline and copy for a specific sequence.
    """
    seq = GLOBAL_OUTREACH_ENGINE.get_sequence(sequence_id)
    if not seq:
        raise HTTPException(
            status_code=404, detail=f"Sequence '{sequence_id}' not found."
        )
    return seq


@router.post("/sequences/{sequence_id}/advance", response_model=OutreachSequenceResult)
def advance_outreach_sequence(sequence_id: str) -> OutreachSequenceResult:
    """
    Execute current pending touchpoint and advance cadence to next step.
    """
    try:
        return GLOBAL_OUTREACH_ENGINE.advance_step(sequence_id)
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Sequence '{sequence_id}' not found."
        )


@router.post("/sequences/{sequence_id}/pause", response_model=OutreachSequenceResult)
def pause_outreach_sequence(sequence_id: str) -> OutreachSequenceResult:
    """
    Pause an active outreach cadence.
    """
    try:
        return GLOBAL_OUTREACH_ENGINE.pause_sequence(sequence_id)
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Sequence '{sequence_id}' not found."
        )


@router.post("/sequences/{sequence_id}/resume", response_model=OutreachSequenceResult)
def resume_outreach_sequence(sequence_id: str) -> OutreachSequenceResult:
    """
    Resume a paused outreach cadence.
    """
    try:
        return GLOBAL_OUTREACH_ENGINE.resume_sequence(sequence_id)
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Sequence '{sequence_id}' not found."
        )


@router.post("/sequences/{sequence_id}/cancel", response_model=OutreachSequenceResult)
def cancel_outreach_sequence(
    sequence_id: str,
    reason: str = Query(
        default="Manual cancellation", description="Cancellation reason"
    ),
) -> OutreachSequenceResult:
    """
    Cancel an outreach sequence.
    """
    try:
        return GLOBAL_OUTREACH_ENGINE.cancel_sequence(sequence_id, reason=reason)
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Sequence '{sequence_id}' not found."
        )


@router.post("/inbound/analyze", response_model=InboundReplyAnalysisResult)
def analyze_inbound_reply(
    req: InboundReplyRequest,
    update_db: bool = Query(
        default=True,
        description="Whether to automatically transition application status in database",
    ),
) -> InboundReplyAnalysisResult:
    """
    Classify incoming client reply text, extract commercial intent, update application funnel status, and synthesize draft response.
    """
    return inbound_classifier.analyze_reply(req=req, update_db=update_db)


@router.get("/experiments/pitch-stats", response_model=ABExperimentSummary)
def get_ab_pitch_experiment_summary() -> ABExperimentSummary:
    """
    Retrieve statistical A/B pitch testing performance, confidence intervals, and category recommendations.
    """
    return GLOBAL_PROPOSAL_EXPERIMENTER.get_summary()


@router.post("/experiments/record")
def record_ab_pitch_event(payload: RecordEventPayload) -> dict[str, str]:
    """
    Record an outreach funnel event (IMPRESSION, REPLY, or WIN) for A/B pitch conversion optimization.
    """
    GLOBAL_PROPOSAL_EXPERIMENTER.record_event(
        pitch_angle=payload.pitch_angle,
        event_type=payload.event_type,
        category=payload.category,
    )
    return {"status": "success", "message": f"Recorded {payload.event_type} event"}


@router.get("/experiments/recommend-pitch")
def recommend_optimal_pitch(
    category: str = Query(
        default="General", description="Project category or domain"
    ),
) -> dict[str, str]:
    """
    Recommend the statistically optimal proposal pitch angle for a given project category.
    """
    optimal = GLOBAL_PROPOSAL_EXPERIMENTER.select_optimal_pitch_angle(category=category)
    return {"category": category, "recommended_pitch_angle": optimal.value}
