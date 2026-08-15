"""
FastAPI REST Router for Client Background Intelligence, Scam Risk Sentinel, and Scope Feasibility.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.database.connection import SessionLocal
from src.database.models import ProjectModel
from src.intelligence.dossier import ClientDossierEngine
from src.intelligence.feasibility import (
    GLOBAL_FEASIBILITY_ANALYZER,
)
from src.intelligence.scam_sentinel import (
    GLOBAL_SCAM_SENTINEL,
)
from src.intelligence.schemas import (
    BudgetFeasibilityRequest,
    BudgetFeasibilityResult,
    ClientDossierRequest,
    ClientDossierResult,
    ScamAuditRequest,
    ScamAuditResult,
)

router = APIRouter(prefix="/api/intelligence", tags=["Client Intelligence & Scam Sentinel"])


class FullProjectIntelligenceResponse(BaseModel):
    """Combined intelligence report for a saved project opportunity."""

    project_id: int
    project_title: str
    client_dossier: ClientDossierResult
    scam_audit: ScamAuditResult
    budget_feasibility: BudgetFeasibilityResult


@router.post("/client-dossier", response_model=ClientDossierResult)
def generate_client_dossier(req: ClientDossierRequest) -> ClientDossierResult:
    """
    Synthesize deep client background intelligence dossier, extract domain credentials, and compute trust score.
    """
    engine = ClientDossierEngine()
    return engine.generate_dossier(req=req)


@router.post("/scam-audit", response_model=ScamAuditResult)
def audit_scam_risk(req: ScamAuditRequest) -> ScamAuditResult:
    """
    Scan project description and client details for freelance scams, check cashing schemes, and unpaid test traps.
    """
    sentinel = GLOBAL_SCAM_SENTINEL
    return sentinel.audit_opportunity(req=req)


@router.post("/budget-feasibility", response_model=BudgetFeasibilityResult)
def evaluate_budget_feasibility(req: BudgetFeasibilityRequest) -> BudgetFeasibilityResult:
    """
    Compare technical scope complexity against offered budget and calculate fair market pricing.
    """
    analyzer = GLOBAL_FEASIBILITY_ANALYZER
    return analyzer.evaluate_feasibility(req=req)


@router.get("/from-project/{project_id}", response_model=FullProjectIntelligenceResponse)
def get_full_project_intelligence(
    project_id: int,
) -> FullProjectIntelligenceResponse:
    """
    One-click comprehensive background dossier, scam audit, and budget feasibility check for a stored project.
    """
    with SessionLocal() as session:
        proj = session.get(ProjectModel, project_id)
        if not proj:
            raise HTTPException(
                status_code=404, detail=f"Project #{project_id} not found in database."
            )

        title = proj.title
        desc = proj.description or ""
        client_name = proj.client_name or "Client"
        budget = proj.budget
        source_url = proj.source_url
        source = proj.source or "Public Web"
        skills = proj.skills or []

    # 1. Dossier
    dossier_engine = ClientDossierEngine()
    dossier_req = ClientDossierRequest(
        client_name=client_name,
        project_title=title,
        project_description=desc,
        source=source,
        source_url=source_url,
        claimed_budget=budget,
    )
    dossier = dossier_engine.generate_dossier(dossier_req)

    # 2. Scam Audit
    scam_req = ScamAuditRequest(
        project_title=title,
        project_description=desc,
        client_name=client_name,
        claimed_budget=budget,
    )
    scam_res = GLOBAL_SCAM_SENTINEL.audit_opportunity(scam_req)

    # 3. Feasibility
    feasibility_req = BudgetFeasibilityRequest(
        project_title=title,
        project_description=desc,
        proposed_budget=budget if budget and budget > 0 else 3000.0,
        target_skills=skills,
    )
    feasibility_res = GLOBAL_FEASIBILITY_ANALYZER.evaluate_feasibility(feasibility_req)

    return FullProjectIntelligenceResponse(
        project_id=project_id,
        project_title=title,
        client_dossier=dossier,
        scam_audit=scam_res,
        budget_feasibility=feasibility_res,
    )
