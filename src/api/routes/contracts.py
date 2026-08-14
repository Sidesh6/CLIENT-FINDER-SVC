"""
Proposal Quality Auditor, SOW Milestone Contract Generator, and Legal Scope Guard REST Endpoints.
"""

from fastapi import APIRouter

from src.api.routes.profile import get_current_active_profile
from src.proposal.auditor import (
    ProposalAuditor,
    ProposalAuditRequest,
    ProposalAuditResult,
)
from src.proposal.scope_guard import (
    ContractClause,
    ScopeGuard,
    SOWRequest,
    SOWResult,
)

router = APIRouter(prefix="/api/contracts", tags=["Contracts, SOW & Proposal Quality Audit"])


@router.post("/audit-proposal", response_model=ProposalAuditResult)
def audit_proposal_quality(req: ProposalAuditRequest) -> ProposalAuditResult:
    """
    Perform multi-dimensional conversion audit on a draft proposal (Specificity, Social Proof, CTA, Brevity, Pricing).
    """
    auditor = ProposalAuditor()
    return auditor.audit(req)


@router.post("/generate-sow", response_model=SOWResult)
def generate_scope_of_work(req: SOWRequest) -> SOWResult:
    """
    Generate professional Scope of Work with phased milestones, acceptance gates, payment schedules, and change order clauses.
    """
    profile = get_current_active_profile()
    guard = ScopeGuard(default_profile=profile)
    return guard.generate_sow(req, profile=profile)


@router.get("/clauses", response_model=list[ContractClause])
def get_standard_protective_clauses() -> list[ContractClause]:
    """
    Retrieve standard freelance protective contract clauses (Scope Boundaries, IP Assignment, Late Fees, Acceptance Windows).
    """
    guard = ScopeGuard()
    return guard.get_standard_protective_clauses()
