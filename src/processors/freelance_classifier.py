"""
Freelance Client Classifier.
Evaluates opportunities to strictly identify direct freelance clients, founders, and contract gigs,
while filtering out full-time employment, W2 salaried roles, and recruitment agency spam.
"""

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ClientType(StrEnum):
    DIRECT_FOUNDER = "DIRECT_FOUNDER"
    STARTUP_EXEC = "STARTUP_EXEC"
    PRODUCT_OWNER = "PRODUCT_OWNER"
    AGENCY_OWNER = "AGENCY_OWNER"
    ENTERPRISE_BUYER = "ENTERPRISE_BUYER"
    STAFFING_RECRUITER = "STAFFING_RECRUITER"
    UNKNOWN = "UNKNOWN"


class EngagementType(StrEnum):
    FIXED_MILESTONE = "FIXED_MILESTONE"
    HOURLY_CONTRACT = "HOURLY_CONTRACT"
    MONTHLY_RETAINER = "MONTHLY_RETAINER"
    FRACTIONAL_CTO = "FRACTIONAL_CTO"
    ADVISORY_CONSULTING = "ADVISORY_CONSULTING"
    EMPLOYEE_JOB = "EMPLOYEE_JOB"  # Disqualified


@dataclass
class FreelanceClassificationResult:
    """Evaluation result detailing whether an opportunity represents a legitimate direct client."""

    is_direct_client: bool
    confidence: float
    client_type: ClientType
    engagement_type: EngagementType
    is_freelance_contract: bool
    rejection_reasons: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_direct_client": self.is_direct_client,
            "confidence": self.confidence,
            "client_type": self.client_type.value,
            "engagement_type": self.engagement_type.value,
            "is_freelance_contract": self.is_freelance_contract,
            "rejection_reasons": self.rejection_reasons,
            "explanation": self.explanation,
        }


class FreelanceClientClassifier:
    """
    Classifier analyzing text to strictly distinguish direct freelance buyer requests from employee jobs.
    """

    # Disqualifying employee/recruiter patterns
    EMPLOYEE_DISQUALIFIERS = [
        (re.compile(r"\b(w-?2|1099\s+or\s+w2|w2\s+only)\b", re.IGNORECASE), "W-2 employee tax status required"),
        (re.compile(r"\b(401\s*\(?k\)?|401k\s+match|health\s+dental|medical\s+dental\s+vision|pto\s+days|paid\s+time\s+off)\b", re.IGNORECASE), "Employee benefits package (401k/health insurance/PTO)"),
        (re.compile(r"\b(full\s*-?\s*time\s+(?:employee|hire|permanent|position)|permanent\s+role)\b", re.IGNORECASE), "Permanent full-time employee position"),
        (re.compile(r"\b(staffing\s+agency|recruiting\s+firm|our\s+client\s+is\s+seeking|on\s+behalf\s+of\s+our\s+client|talent\s+acquisition\s+partner)\b", re.IGNORECASE), "Third-party recruiter or staffing agency middleman"),
        (re.compile(r"\b(must\s+be\s+(?:on-?site|in\s+office|hybrid\s+\d+\s+days))\b", re.IGNORECASE), "On-site office requirement (non-remote freelance)"),
        (re.compile(r"\b(annual\s+salary|base\s+salary\s+of\s+\$|base\s+pay\s+range)\b", re.IGNORECASE), "Annual salary employee structure"),
    ]

    # Direct client & buyer intent patterns
    FOUNDER_INTENT_PATTERNS = [
        (re.compile(r"\b(?:i(?:'m|\s+am)|we(?:'re|\s+are)?)\s+(?:the\s+)?(?:founder|co-founder|ceo|cto|building\s+a\s+startup|launching)\b", re.IGNORECASE), ClientType.DIRECT_FOUNDER),
        (re.compile(r"\b(?:my|our)\s+(?:startup|product|mvp|app|saas|platform)\b", re.IGNORECASE), ClientType.DIRECT_FOUNDER),
        (re.compile(r"\b(?:seeking|looking\s+for|need|hiring)\s+(?:a\s+)?(?:freelance|contract(?:or)?|consultant|agency)\b", re.IGNORECASE), ClientType.PRODUCT_OWNER),
        (re.compile(r"\b(?:digital|dev|design)\s+agency\s+(?:partner|white\s*label|overflow)\b", re.IGNORECASE), ClientType.AGENCY_OWNER),
    ]

    # Engagement structure patterns
    ENGAGEMENT_PATTERNS = [
        (re.compile(r"\b(fixed\s*[- ]price|milestone(?:-based)?|project\s+quote|lump\s+sum|budget:\s*\$)\b", re.IGNORECASE), EngagementType.FIXED_MILESTONE),
        (re.compile(r"\b(\$\d+\s*[-/]\s*(?:hr|hour)|hourly\s+rate|per\s+hour|\/hr)\b", re.IGNORECASE), EngagementType.HOURLY_CONTRACT),
        (re.compile(r"\b(monthly\s+retainer|\$\d+[kK]?\s*[-/]\s*month|ongoing\s+maintenance|hours\s+per\s+month)\b", re.IGNORECASE), EngagementType.MONTHLY_RETAINER),
        (re.compile(r"\b(fractional\s+cto|fractional\s+lead|technical\s+advisor|advisory\s+role)\b", re.IGNORECASE), EngagementType.FRACTIONAL_CTO),
    ]

    def classify(self, project: dict[str, Any]) -> FreelanceClassificationResult:
        """
        Classify a project dictionary into direct freelance buyer vs employee job.
        """
        title = project.get("title", "")
        description = project.get("description", "")
        source = project.get("source", "")
        combined = f"{title}\n{description}".strip()

        rejection_reasons: list[str] = []

        # Sources that are inherently 100% direct client requests
        is_client_lead_source = source in ("Client Leads", "Upwork", "Hacker News") or project.get("is_direct_client", False)

        # Check disqualifiers
        for pattern, reason in self.EMPLOYEE_DISQUALIFIERS:
            # For Upwork or Hacker News client posts, allow 'budget' or 'hourly' even if salary words appear in boilerplate
            if is_client_lead_source and "salary" in reason.lower():
                continue
            if pattern.search(combined):
                rejection_reasons.append(reason)

        # Determine client type
        client_type = ClientType.UNKNOWN
        for pattern, c_type in self.FOUNDER_INTENT_PATTERNS:
            if pattern.search(combined):
                client_type = c_type
                break

        if client_type == ClientType.UNKNOWN and is_client_lead_source:
            client_type = ClientType.DIRECT_FOUNDER

        # Determine engagement type
        engagement_type = EngagementType.HOURLY_CONTRACT
        for pattern, e_type in self.ENGAGEMENT_PATTERNS:
            if pattern.search(combined):
                engagement_type = e_type
                break

        # Check if rejected as employee job
        if rejection_reasons:
            is_direct = False
            is_freelance = False
            engagement_type = EngagementType.EMPLOYEE_JOB
            confidence = max(0.85, 0.2 * len(rejection_reasons))
            explanation = f"Disqualified: {'; '.join(rejection_reasons)}"
        else:
            is_direct = True
            is_freelance = True
            confidence = 0.92 if is_client_lead_source or client_type != ClientType.UNKNOWN else 0.78
            explanation = f"Qualified Direct Freelance Client ({client_type.value}) for {engagement_type.value} engagement."

        return FreelanceClassificationResult(
            is_direct_client=is_direct,
            confidence=min(confidence, 1.0),
            client_type=client_type,
            engagement_type=engagement_type,
            is_freelance_contract=is_freelance,
            rejection_reasons=rejection_reasons,
            explanation=explanation,
        )


GLOBAL_FREELANCE_CLASSIFIER = FreelanceClientClassifier()
