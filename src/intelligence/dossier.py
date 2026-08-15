"""
Client Dossier & Deep Background Intelligence Engine.
Synthesizes comprehensive company profiles, detects domain fingerprints, and calculates multi-factor Client Trust Scores.
"""

import logging
import re
from datetime import UTC, datetime
from urllib.parse import urlparse

from src.intelligence.schemas import (
    ClientDossierRequest,
    ClientDossierResult,
    ClientTrustBreakdown,
)
from src.models.profile import UserProfile, get_default_profile

logger = logging.getLogger("ClientDossierEngine")


class ClientDossierEngine:
    """
    Generates rich client intelligence dossiers, extracts domain credentials, and scores client credibility.
    """

    def __init__(self, default_profile: UserProfile | None = None):
        self.default_profile = default_profile or get_default_profile()

    def generate_dossier(
        self,
        req: ClientDossierRequest,
        profile: UserProfile | None = None,
    ) -> ClientDossierResult:
        """
        Synthesize client intelligence profile and calculate credibility metrics.
        """
        text = f"{req.project_title} {req.project_description}".strip()
        lower_text = text.lower()

        # 1. Infer Company Domain / Entity Fingerprint
        domain = self._extract_domain(req.source_url, text)

        # 2. Extract Technical Stack Footprints
        tech_stack = self._detect_tech_stack(lower_text)

        # 3. Multi-Factor Trust Dimension Scoring
        breakdown, positive_signals, caution_warnings = self._evaluate_trust_dimensions(
            req=req, lower_text=lower_text, domain=domain, tech_stack=tech_stack
        )

        # 4. Calculate Overall Trust Score
        overall = (
            (breakdown.domain_credibility * 0.25)
            + (breakdown.hiring_history_score * 0.25)
            + (breakdown.budget_transparency * 0.20)
            + (breakdown.requirement_clarity * 0.15)
            + (breakdown.payment_security_score * 0.15)
        )
        overall = round(overall, 1)

        # 5. Determine Trust Grade
        if overall >= 85.0:
            grade = "EXCELLENT"
            posture = "Standard commercial engagement. Propose 30% upfront kickoff with bi-weekly milestones."
        elif overall >= 70.0:
            grade = "VERIFIED"
            posture = "Standard freelance agreement with formal Change Order clauses and 5-day review window."
        elif overall >= 55.0:
            grade = "MODERATE"
            posture = "Require 50% upfront escrow deposit or weekly sprint billing to mitigate scope/payment risks."
        elif overall >= 40.0:
            grade = "UNVERIFIED"
            posture = "High caution. Insist on 100% funded platform escrow or small paid exploratory milestone first."
        else:
            grade = "SUSPICIOUS"
            posture = "Critical risk. Do not write unpaid code or accept off-platform unverified payments."

        return ClientDossierResult(
            client_name=req.client_name or "Client",
            inferred_company_domain=domain,
            detected_tech_stack=tech_stack,
            overall_trust_score=overall,
            trust_grade=grade,
            trust_breakdown=breakdown,
            positive_signals=positive_signals,
            caution_warnings=caution_warnings,
            recommended_commercial_posture=posture,
            generated_at=datetime.now(UTC),
        )

    def _extract_domain(self, source_url: str | None, text: str) -> str | None:
        """Extract or infer company domain from URL or text."""
        if source_url:
            try:
                parsed = urlparse(source_url)
                netloc = parsed.netloc.lower()
                # If it's a job board, search in text
                if not any(
                    board in netloc
                    for board in [
                        "news.ycombinator.com",
                        "remoteok.com",
                        "weworkremotely.com",
                        "upwork.com",
                    ]
                ):
                    return netloc.replace("www.", "")
            except Exception:
                pass

        # Search for company website patterns in text (e.g. https://company.com, company.io)
        domain_match = re.search(
            r"https?://(?:www\.)?([a-zA-Z0-9-]+\.(?:com|io|co|ai|org|dev|net|app|tech))", text
        )
        if domain_match:
            return domain_match.group(1).lower()

        return None

    def _detect_tech_stack(self, lower_text: str) -> list[str]:
        """Identify modern technical stack signatures in client text."""
        known_tools = [
            "Python",
            "FastAPI",
            "Django",
            "Flask",
            "React",
            "Next.js",
            "TypeScript",
            "Node.js",
            "PostgreSQL",
            "MongoDB",
            "Redis",
            "Docker",
            "Kubernetes",
            "AWS",
            "GCP",
            "GraphQL",
            "Tailwind",
            "PyTorch",
            "LangChain",
            "OpenAI",
            "LlamaIndex",
        ]
        detected = []
        for tool in known_tools:
            if re.search(r"\b" + re.escape(tool.lower()) + r"\b", lower_text):
                detected.append(tool)
        return detected or ["Python", "FastAPI"]

    def _evaluate_trust_dimensions(
        self,
        req: ClientDossierRequest,
        lower_text: str,
        domain: str | None,
        tech_stack: list[str],
    ) -> tuple[ClientTrustBreakdown, list[str], list[str]]:
        """Evaluate the 5 core trust dimensions."""
        positive_signals: list[str] = []
        caution_warnings: list[str] = []

        # 1. Domain Credibility
        if domain:
            domain_score = 90.0
            positive_signals.append(f"Verified custom company domain: {domain}")
        elif req.client_name and req.client_name.lower() not in (
            "client",
            "anonymous",
            "hiring manager",
        ):
            domain_score = 75.0
            positive_signals.append(f"Identified public organization/name: {req.client_name}")
        else:
            domain_score = 50.0
            caution_warnings.append("Anonymous poster or unverified company domain.")

        # 2. Hiring History & Team Scale
        history_keywords = [
            "series a",
            "series b",
            "funded",
            "vc backed",
            "our team",
            "engineering team",
            "cto",
            "existing codebase",
            "production environment",
            "github repo",
            "active users",
        ]
        history_hits = sum(1 for k in history_keywords if k in lower_text)
        if history_hits >= 2:
            history_score = 92.0
            positive_signals.append("Mentions established engineering team or production codebase.")
        elif history_hits == 1:
            history_score = 75.0
            positive_signals.append("Contains indicators of active product infrastructure.")
        else:
            history_score = 55.0
            caution_warnings.append("Limited team or organizational history specified in posting.")

        # 3. Budget Transparency
        if req.claimed_budget and req.claimed_budget >= 1000.0:
            budget_score = 90.0
            positive_signals.append(
                f"Explicit advertised milestone/contract budget (${req.claimed_budget:,.2f})."
            )
        elif req.claimed_budget and req.claimed_budget > 0:
            budget_score = 70.0
            positive_signals.append(f"Fixed budget specified (${req.claimed_budget:,.2f}).")
        elif any(k in lower_text for k in ["$", "usd", "hourly", "budget", "competitive rate"]):
            budget_score = 65.0
        else:
            budget_score = 45.0
            caution_warnings.append("Budget unspecified or negotiable without transparent bounds.")

        # 4. Requirement Clarity
        if len(tech_stack) >= 3 and len(lower_text.split()) >= 60:
            clarity_score = 95.0
            positive_signals.append(
                f"High architectural precision citing {len(tech_stack)} specific stack components."
            )
        elif len(tech_stack) >= 1 and len(lower_text.split()) >= 30:
            clarity_score = 75.0
        else:
            clarity_score = 50.0
            caution_warnings.append(
                "Sparse project description may lead to evolving scope requirements."
            )

        # 5. Payment Security & Platform Reputability
        if any(src in req.source.lower() for src in ["hacker news", "weworkremotely", "remoteok"]):
            security_score = 88.0
            positive_signals.append(f"Discovered via reputable verified board ({req.source}).")
        else:
            security_score = 60.0

        breakdown = ClientTrustBreakdown(
            domain_credibility=domain_score,
            hiring_history_score=history_score,
            budget_transparency=budget_score,
            requirement_clarity=clarity_score,
            payment_security_score=security_score,
        )

        return breakdown, positive_signals, caution_warnings
