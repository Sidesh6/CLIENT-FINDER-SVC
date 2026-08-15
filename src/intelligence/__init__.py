"""
Client Background Intelligence, Scam Risk Sentinel, and Scope Feasibility Package.
"""

from src.intelligence.dossier import ClientDossierEngine
from src.intelligence.feasibility import (
    GLOBAL_FEASIBILITY_ANALYZER,
    BudgetFeasibilityAnalyzer,
)
from src.intelligence.scam_sentinel import (
    GLOBAL_SCAM_SENTINEL,
    ScamSentinel,
)
from src.intelligence.schemas import (
    BudgetFeasibilityRequest,
    BudgetFeasibilityResult,
    ClientDossierRequest,
    ClientDossierResult,
    ClientTrustBreakdown,
    FeasibilityRating,
    RedFlagTrigger,
    RiskTier,
    ScamAuditRequest,
    ScamAuditResult,
    ScamPatternType,
)

__all__ = [
    "ClientDossierEngine",
    "ScamSentinel",
    "GLOBAL_SCAM_SENTINEL",
    "BudgetFeasibilityAnalyzer",
    "GLOBAL_FEASIBILITY_ANALYZER",
    "RiskTier",
    "ScamPatternType",
    "FeasibilityRating",
    "RedFlagTrigger",
    "ClientTrustBreakdown",
    "ClientDossierRequest",
    "ClientDossierResult",
    "ScamAuditRequest",
    "ScamAuditResult",
    "BudgetFeasibilityRequest",
    "BudgetFeasibilityResult",
]
