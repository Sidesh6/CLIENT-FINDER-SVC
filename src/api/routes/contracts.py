"""
FastAPI Router for AI Contract Generator & Legal Risk Analyzer (LegalTech Studio).
Includes Phase 15 Proposal Auditor & Scope Guard endpoints + Phase 25 Contract Generator endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Body, status

from src.auth.dependencies import get_current_tenant, get_current_user
from src.auth.schemas import TenantResponse, UserProfileResponse
from src.contracts.analyzer import GLOBAL_LEGAL_ANALYZER
from src.contracts.registry import GLOBAL_CONTRACT_REGISTRY
from src.contracts.schemas import (
    AuditContractRequest,
    ContractAuditResult,
    ContractRecord,
    ContractStatus,
    GenerateContractRequest,
)
from src.proposal.auditor import (
    ProposalAuditRequest,
    ProposalAuditResult,
    ProposalAuditor,
)
from src.proposal.scope_guard import (
    ContractClause,
    ScopeGuard,
    SOWRequest,
    SOWResult,
)

router = APIRouter(prefix="/api/contracts", tags=["AI Contract Generator & Legal Risk Analyzer"])

_AUDITOR = ProposalAuditor()
_SCOPE_GUARD = ScopeGuard()


# ----- Phase 15: Proposal Auditor & Scope Guard Endpoints -----

@router.post("/audit-proposal", response_model=ProposalAuditResult)
def audit_proposal(req: ProposalAuditRequest) -> ProposalAuditResult:
    """Audit draft proposal text for win-rate readiness across 5 dimensions."""
    return _AUDITOR.audit(req)


@router.post("/generate-sow", response_model=SOWResult)
def generate_sow(req: SOWRequest) -> SOWResult:
    """Generate structured Scope of Work (SOW) with milestone breakdown."""
    return _SCOPE_GUARD.generate_sow(req)


@router.get("/clauses", response_model=list[ContractClause])
def get_standard_clauses() -> list[ContractClause]:
    """Retrieve standard protective freelance contract clauses."""
    return _SCOPE_GUARD.get_standard_protective_clauses()


# ----- Phase 25: AI LegalTech Studio & Contract Registry Endpoints -----

@router.post("/generate", response_model=ContractRecord, status_code=status.HTTP_201_CREATED)
def generate_contract(
    req: GenerateContractRequest,
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> ContractRecord:
    """
    Generate a standardized, protective legal agreement (MSA, SOW, NDA, Contractor Agreement).
    """
    return GLOBAL_CONTRACT_REGISTRY.create_contract(tenant_id=tenant.tenant_id, req=req)


@router.post("/audit", response_model=ContractAuditResult)
def audit_contract_text(
    req: AuditContractRequest,
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> ContractAuditResult:
    """
    Audit raw legal contract text for legal risks, IP traps, indemnification liabilities, and payment term traps.
    """
    return GLOBAL_LEGAL_ANALYZER.audit_contract(req=req)


@router.get("", response_model=list[ContractRecord])
def list_contracts(
    status_filter: ContractStatus | None = None,
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> list[ContractRecord]:
    """List all stored legal contracts for the workspace."""
    return GLOBAL_CONTRACT_REGISTRY.list_contracts(tenant_id=tenant.tenant_id, status_filter=status_filter)


@router.get("/{contract_id}", response_model=ContractRecord)
def get_contract_by_id(
    contract_id: str,
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> ContractRecord:
    """Retrieve details and markdown content of a specific legal agreement."""
    contract = GLOBAL_CONTRACT_REGISTRY.get_contract(contract_id)
    if not contract or contract.tenant_id != tenant.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Contract '{contract_id}' not found.")
    return contract


@router.post("/{contract_id}/sign", response_model=ContractRecord)
def sign_contract(
    contract_id: str,
    signer_name: str = Body(..., embed=True),
    signer_email: str = Body(..., embed=True),
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> ContractRecord:
    """Record an e-signature execution against a legal agreement."""
    result = GLOBAL_CONTRACT_REGISTRY.sign_contract(
        contract_id=contract_id,
        tenant_id=tenant.tenant_id,
        signer_name=signer_name,
        signer_email=signer_email,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Contract '{contract_id}' not found.")
    return result
