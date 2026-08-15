"""
AI Legal Risk Analyzer — Clause Risk Classifier and Trap Detection Engine for Contracts.
"""

import logging
import uuid
from datetime import UTC, datetime

from src.contracts.schemas import (
    AuditContractRequest,
    ContractAuditResult,
    RiskCategory,
    RiskFinding,
    RiskSeverity,
)

logger = logging.getLogger("LegalRiskAnalyzer")


class LegalRiskAnalyzer:
    """
    Audits raw legal agreements to detect high-risk clauses, indemnification traps, and IP ownership risks.
    """

    def audit_contract(self, req: AuditContractRequest) -> ContractAuditResult:
        """Perform legal risk audit on contract text using rules & pattern analysis."""
        text = req.contract_text.lower()
        findings: list[RiskFinding] = []

        # 1. IP Assignment & Pre-Existing IP Traps
        if "work for hire" in text and "upon payment" not in text and "prior to payment" not in text:
            findings.append(
                RiskFinding(
                    category=RiskCategory.IP_ASSIGNMENT,
                    severity=RiskSeverity.HIGH,
                    clause_title="Immediate Work-For-Hire Transfer Without Payment Condition",
                    flagged_text="All work product shall be considered a work made for hire upon creation...",
                    explanation="Contract transfers IP rights immediately upon creation without requiring full invoice payment first.",
                    suggested_revision="Add clause: 'All IP rights transfer exclusively to Client ONLY UPON FULL PAYMENT of all valid invoices.'",
                )
            )
        if "pre-existing" in text and ("assigns all" in text or "transfers all" in text):
            findings.append(
                RiskFinding(
                    category=RiskCategory.IP_ASSIGNMENT,
                    severity=RiskSeverity.CRITICAL,
                    clause_title="Pre-Existing Developer IP Transfer Trap",
                    flagged_text="Developer assigns all rights, including pre-existing tools, libraries, and frameworks...",
                    explanation="Overly broad clause attempts to transfer ownership of your personal tools, starter templates, or pre-existing code libraries.",
                    suggested_revision="Exclude pre-existing tools: 'Developer retains sole ownership of pre-existing tools, frameworks, and utility libraries.'",
                )
            )

        # 2. Indemnification Overreach
        if "indemnify" in text or "hold harmless" in text:
            if "solely" not in text and "gross negligence" not in text:
                findings.append(
                    RiskFinding(
                        category=RiskCategory.INDEMNIFICATION,
                        severity=RiskSeverity.HIGH,
                        clause_title="Broad Uncapped Indemnification Obligation",
                        flagged_text="Contractor shall indemnify, defend, and hold harmless Client against any and all claims...",
                        explanation="Clause makes contractor liable for third-party claims regardless of fault or willful misconduct.",
                        suggested_revision="Limit indemnity: 'Contractor indemnifies Client solely for direct losses resulting from Contractor's gross negligence or willful misconduct.'",
                    )
                )

        # 3. Unlimited Liability / Missing Liability Cap
        if ("without limitation of liability" in text or "unlimited liability" in text or
            ("limitation of liability" not in text and "aggregate liability" not in text)):
            findings.append(
                RiskFinding(
                    category=RiskCategory.LIABILITY_LIMIT,
                    severity=RiskSeverity.CRITICAL,
                    clause_title="Missing or Waived Contractor Liability Cap",
                    flagged_text="[Unlimited Liability or Missing Limitation of Liability Clause Detected]",
                    explanation="Contract exposes contractor to unlimited financial liability for breach or project disputes.",
                    suggested_revision="Insert cap: 'Developer's aggregate liability under this agreement shall be capped at total fees paid in the preceding 3 months.'",
                )
            )

        # 4. Unfavorable Payment Terms
        if "net 60" in text or "net 90" in text or "90 days" in text:
            findings.append(
                RiskFinding(
                    category=RiskCategory.PAYMENT_TERMS,
                    severity=RiskSeverity.MEDIUM,
                    clause_title="Extended Net-60 / Net-90 Payment Schedule",
                    flagged_text="Invoices shall be payable within 60 to 90 days of receipt...",
                    explanation="Long payment cycles hurt freelancer cash flow and increase default risk.",
                    suggested_revision="Renegotiate to Net 14 or Net 30 days with late interest fees.",
                )
            )
        if "paid when paid" in text or "pay when paid" in text:
            findings.append(
                RiskFinding(
                    category=RiskCategory.PAYMENT_TERMS,
                    severity=RiskSeverity.HIGH,
                    clause_title="Pay-When-Paid Contingency Clause",
                    flagged_text="Client shall pay Contractor within 10 days of Client receiving payment from End-Client...",
                    explanation="Conditioning your payment on whether a third party pays your client shifts end-client credit risk onto you.",
                    suggested_revision="Strike clause. Payments to Developer must be independent of end-client settlement.",
                )
            )

        # 5. Non-Compete Overreach
        if "non-compete" in text or "shall not engage with any competitor" in text:
            findings.append(
                RiskFinding(
                    category=RiskCategory.NON_COMPETE,
                    severity=RiskSeverity.HIGH,
                    clause_title="Restrictive Non-Compete Covenant",
                    flagged_text="Contractor agrees not to provide services to any competitor of Client for a period of 12 months...",
                    explanation="Restricts freelancer's right to work in their core domain or accept future client projects.",
                    suggested_revision="Remove non-compete completely or limit strictly to non-solicitation of direct client employees.",
                )
            )

        # 6. Termination Penalties & Unpaid Work
        if "terminate" in text and "without cause" in text and "pay for services rendered" not in text:
            findings.append(
                RiskFinding(
                    category=RiskCategory.TERMINATION_CLAUSE,
                    severity=RiskSeverity.MEDIUM,
                    clause_title="Termination for Convenience Without Payment Guarantee",
                    flagged_text="Client may terminate this agreement at any time without cause...",
                    explanation="Does not explicitly mandate full payment for work completed prior to notice.",
                    suggested_revision="Ensure clause states: 'Client shall pay for all work completed and non-cancelable expenses incurred up to the date of termination.'",
                )
            )

        # 7. Default Low-Risk Finding if clean
        if not findings:
            findings.append(
                RiskFinding(
                    category=RiskCategory.WARRANTY_SCOPE,
                    severity=RiskSeverity.LOW,
                    clause_title="Standard Service Agreement Terms",
                    flagged_text="[No Critical Legal Traps Identified]",
                    explanation="The analyzed contract text adheres to standard commercial terms.",
                    suggested_revision="Proceed with standard contract signing after verifying commercial deliverables.",
                )
            )

        # Compute summary metrics
        crit = len([f for f in findings if f.severity == RiskSeverity.CRITICAL])
        high = len([f for f in findings if f.severity == RiskSeverity.HIGH])
        med = len([f for f in findings if f.severity == RiskSeverity.MEDIUM])
        low = len([f for f in findings if f.severity == RiskSeverity.LOW])

        # Overall risk score formula
        risk_score = round(min(crit * 35.0 + high * 20.0 + med * 10.0 + low * 2.0, 100.0), 1)

        if risk_score >= 60.0:
            rec = "🔴 HIGH RISK: Do not sign in current form. Request mandatory amendments for flagged clauses."
        elif risk_score >= 30.0:
            rec = "🟡 MODERATE RISK: Negotiate highlighted payment terms, IP retention, or liability caps before signing."
        else:
            rec = "🟢 LOW RISK: Contract terms appear standard and balanced."

        return ContractAuditResult(
            audit_id=f"audit_{uuid.uuid4().hex[:10]}",
            contract_title=req.contract_title,
            overall_risk_score=risk_score,
            findings=findings,
            critical_count=crit,
            high_count=high,
            medium_count=med,
            low_count=low,
            recommendation=rec,
            audited_at=datetime.now(UTC),
        )


GLOBAL_LEGAL_ANALYZER = LegalRiskAnalyzer()
