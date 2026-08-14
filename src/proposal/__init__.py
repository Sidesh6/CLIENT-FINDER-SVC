"""
Proposal generation subsystem for automated client pitch and cover letter synthesis.
"""

from src.proposal.generator import ProposalGenerator
from src.proposal.heuristic import HeuristicProposalGenerator
from src.proposal.prompts import PROPOSAL_SYSTEM_PROMPT, build_proposal_prompt
from src.proposal.schemas import (
    PitchAngle,
    ProposalRequest,
    ProposalResult,
    ProposalTone,
)

__all__ = [
    "HeuristicProposalGenerator",
    "PitchAngle",
    "ProposalGenerator",
    "ProposalRequest",
    "ProposalResult",
    "ProposalTone",
    "PROPOSAL_SYSTEM_PROMPT",
    "build_proposal_prompt",
]
