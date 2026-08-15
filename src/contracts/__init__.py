"""
Phase 25: AI Contract Generator & Legal Risk Analyzer (LegalTech Studio) Package.
"""

from src.contracts.analyzer import GLOBAL_LEGAL_ANALYZER, LegalRiskAnalyzer
from src.contracts.generator import GLOBAL_CONTRACT_GENERATOR, ContractGeneratorEngine
from src.contracts.registry import GLOBAL_CONTRACT_REGISTRY, ContractRegistry
from src.contracts.schemas import (
    AuditContractRequest,
    ContractAuditResult,
    ContractRecord,
    ContractStatus,
    ContractType,
    GenerateContractRequest,
    RiskCategory,
    RiskFinding,
    RiskSeverity,
    SignatureRecord,
)

__all__ = [
    "GLOBAL_LEGAL_ANALYZER",
    "GLOBAL_CONTRACT_GENERATOR",
    "GLOBAL_CONTRACT_REGISTRY",
    "LegalRiskAnalyzer",
    "ContractGeneratorEngine",
    "ContractRegistry",
    "ContractType",
    "ContractStatus",
    "RiskSeverity",
    "RiskCategory",
    "RiskFinding",
    "ContractAuditResult",
    "GenerateContractRequest",
    "AuditContractRequest",
    "SignatureRecord",
    "ContractRecord",
]
