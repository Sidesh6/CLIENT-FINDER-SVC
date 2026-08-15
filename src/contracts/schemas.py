"""
Pydantic Schemas for AI Contract Generator & Legal Risk Analyzer (LegalTech Studio).
Covers MSAs, SOWs, NDAs, risk categories, legal audit findings, and e-signatures.
"""

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class ContractType(str, Enum):
    """Supported legal contract types."""

    MSA = "MSA"  # Master Services Agreement
    SOW = "SOW"  # Statement of Work
    NDA = "NDA"  # Non-Disclosure Agreement
    CONTRACTOR_AGREEMENT = "CONTRACTOR_AGREEMENT"
    SOFTWARE_LICENSE = "SOFTWARE_LICENSE"


class ContractStatus(str, Enum):
    """Lifecycle states of a contract."""

    DRAFT = "DRAFT"
    PENDING_SIGNATURE = "PENDING_SIGNATURE"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    CANCELLED = "CANCELLED"


class RiskSeverity(str, Enum):
    """Risk rating level for audited contract clauses."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskCategory(str, Enum):
    """Legal risk categories audited by AI Legal Auditor."""

    IP_ASSIGNMENT = "IP_ASSIGNMENT"
    INDEMNIFICATION = "INDEMNIFICATION"
    LIABILITY_LIMIT = "LIABILITY_LIMIT"
    PAYMENT_TERMS = "PAYMENT_TERMS"
    NON_COMPETE = "NON_COMPETE"
    TERMINATION_CLAUSE = "TERMINATION_CLAUSE"
    JURISDICTION_VENUE = "JURISDICTION_VENUE"
    WARRANTY_SCOPE = "WARRANTY_SCOPE"


class RiskFinding(BaseModel):
    """A specific legal risk identified during contract audit."""

    category: RiskCategory
    severity: RiskSeverity
    clause_title: str
    flagged_text: str
    explanation: str
    suggested_revision: str


class ContractAuditResult(BaseModel):
    """Complete audit summary of a client-provided legal contract."""

    audit_id: str
    contract_title: str
    overall_risk_score: float = Field(..., ge=0.0, le=100.0, description="0 = Safe, 100 = Critical Risk")
    findings: list[RiskFinding] = Field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    recommendation: str
    audited_at: datetime


class GenerateContractRequest(BaseModel):
    """Request payload to generate a custom legal agreement."""

    contract_type: ContractType = ContractType.MSA
    client_name: str
    client_address: str = ""
    developer_name: str = "Freelance Engineer"
    developer_address: str = ""
    project_title: str
    governing_state_country: str = "Delaware, USA"
    payment_terms_days: int = 30
    retain_ip_until_paid: bool = True
    liability_cap_usd: float = 10000.0
    termination_notice_days: int = 14
    effective_date: date | None = None


class AuditContractRequest(BaseModel):
    """Request payload to audit raw contract text for legal risks."""

    contract_title: str = "Client Service Agreement"
    contract_text: str = Field(..., min_length=20, description="Raw text of the contract to analyze")


class SignatureRecord(BaseModel):
    """E-signature audit record for an executed contract."""

    signature_id: str
    signer_name: str
    signer_email: str
    signed_at: datetime
    ip_address: str = "127.0.0.1"
    verification_hash: str


class ContractRecord(BaseModel):
    """Full stored legal contract record."""

    id: str
    contract_number: str
    tenant_id: str = "default_tenant"
    contract_type: ContractType
    title: str
    client_name: str
    developer_name: str
    status: ContractStatus = ContractStatus.DRAFT
    content_markdown: str
    effective_date: date
    expiration_date: date | None = None
    signatures: list[SignatureRecord] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def is_fully_executed(self) -> bool:
        return len(self.signatures) >= 2 or self.status == ContractStatus.EXECUTED
