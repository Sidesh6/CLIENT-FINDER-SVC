"""
Scope of Work (SOW), Milestone Schedule, and Contract Scope Guard Engine.
Transforms freelance opportunities into legally-sound milestone schedules with scope-creep guardrails.
"""

from datetime import datetime, timezone
import logging
from typing import Any

from pydantic import BaseModel, Field

from src.models.profile import UserProfile, get_default_profile

logger = logging.getLogger("ScopeGuard")


class ContractClause(BaseModel):
    """Protective contractual clause safeguarding against unpaid revisions and liabilities."""

    clause_title: str
    clause_text: str
    purpose: str


class SOWMilestone(BaseModel):
    """Discrete contract milestone with explicit acceptance criteria and payment triggers."""

    milestone_index: int
    title: str
    duration_weeks: int
    deliverables: list[str]
    acceptance_criteria: list[str]
    payment_amount: float
    payment_trigger: str


class SOWRequest(BaseModel):
    """Inbound request payload for Scope of Work (SOW) synthesis."""

    project_title: str = Field(description="Project opportunity title")
    project_description: str = Field(default="", description="High level scope requirements")
    client_name: str | None = Field(default="Client", description="Client or company name")
    developer_name: str | None = Field(default=None, description="Developer or agency name")
    total_budget: float = Field(default=5000.0, ge=100.0, description="Total project contract value")
    skills: list[str] = Field(default_factory=list, description="Target technologies")
    include_ip_assignment: bool = Field(default=True, description="Include IP transfer clause upon full payment")
    include_change_order_clause: bool = Field(default=True, description="Include formal Change Order scope-creep guard")


class SOWResult(BaseModel):
    """Complete Scope of Work document and milestone breakdown."""

    contract_title: str
    effective_date: str
    total_budget: float
    milestones: list[SOWMilestone]
    protective_clauses: list[ContractClause]
    formatted_markdown_contract: str


class ScopeGuard:
    """
    Synthesizes structured Scopes of Work with milestone escrow gates and change order protections.
    """

    def __init__(self, default_profile: UserProfile | None = None):
        self.default_profile = default_profile or get_default_profile()

    def generate_sow(
        self,
        req: SOWRequest,
        profile: UserProfile | None = None,
    ) -> SOWResult:
        """
        Generate complete Scope of Work with phased milestones, acceptance gates, and protective terms.
        """
        user_prof = profile or self.default_profile
        dev_name = req.developer_name or user_prof.name
        client = req.client_name or "Client"
        total = req.total_budget
        skills = req.skills or ["Python", "FastAPI", "PostgreSQL"]

        # Divide into 3 structured milestones (30% Kickoff, 40% Core Delivery, 30% Acceptance)
        m1_cost = round(total * 0.30, 2)
        m2_cost = round(total * 0.40, 2)
        m3_cost = round(total - m1_cost - m2_cost, 2)

        m1 = SOWMilestone(
            milestone_index=1,
            title="Phase 1: Discovery, Technical Blueprint & Core Environment Setup",
            duration_weeks=1,
            deliverables=[
                f"Architecture Design Document specifying database schemas and API endpoints utilizing {', '.join(skills[:3])}.",
                "Repository initialization with automated CI/CD pipeline, pre-commit linters, and environment configuration.",
                "Initial stubbed API routes and data model validation test suite.",
            ],
            acceptance_criteria=[
                "Client approval of Technical Blueprint and endpoint definitions.",
                "Automated test suite passing in CI environment with zero configuration errors.",
            ],
            payment_amount=m1_cost,
            payment_trigger="Upon delivery and written sign-off of Phase 1 Technical Blueprint (30% upfront deposit).",
        )

        m2 = SOWMilestone(
            milestone_index=2,
            title="Phase 2: Core Feature Implementation & Database Integration",
            duration_weeks=2,
            deliverables=[
                f"Full functional implementation of core business logic and services for '{req.project_title}'.",
                "Database migrations, indexing, and connection pooling.",
                "Asynchronous background workers, circuit breakers, and third-party API integration.",
            ],
            acceptance_criteria=[
                "Live demo in staging environment verifying all primary user workflows.",
                "Integration test coverage exceeding 90% across core services.",
            ],
            payment_amount=m2_cost,
            payment_trigger="Upon delivery and demonstration of working staging environment (40% milestone release).",
        )

        m3 = SOWMilestone(
            milestone_index=3,
            title="Phase 3: Hardening, User Acceptance Testing (UAT) & Production Handover",
            duration_weeks=1,
            deliverables=[
                "Load testing, security audit, and error observability logging setup.",
                "Comprehensive API documentation (Swagger/OpenAPI) and deployment guide.",
                "Production environment deployment and credentials transfer.",
            ],
            acceptance_criteria=[
                "Zero critical or blocking bugs during 5 business day UAT testing window.",
                "Successful production deployment and handover verification.",
            ],
            payment_amount=m3_cost,
            payment_trigger="Upon final production sign-off and repository transfer (30% final milestone release).",
        )

        milestones = [m1, m2, m3]
        clauses = self.get_standard_protective_clauses()

        now_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

        # Synthesize Markdown Document
        md = f"""# STATEMENT OF WORK & MILESTONE CONTRACT

**Project Name:** {req.project_title}  
**Effective Date:** {now_str}  
**Contractor / Lead Engineer:** {dev_name}  
**Client:** {client}  
**Total Contract Value:** ${total:,.2f} USD  

---

## 1. Project Overview & Scope

The Contractor shall design, build, test, and deliver the technical solution for **{req.project_title}** utilizing **{', '.join(skills)}**.

---

## 2. Milestone Deliverables & Payment Schedule

"""
        for m in milestones:
            md += f"### {m.title}\n"
            md += f"- **Estimated Timeline:** {m.duration_weeks} week(s)\n"
            md += f"- **Milestone Fee:** ${m.payment_amount:,.2f} USD\n"
            md += f"- **Payment Trigger:** {m.payment_trigger}\n\n"
            md += "**Deliverables:**\n"
            for d in m.deliverables:
                md += f"  - {d}\n"
            md += "\n**Acceptance Criteria:**\n"
            for ac in m.acceptance_criteria:
                md += f"  - [ ] {ac}\n"
            md += "\n---\n\n"

        md += "## 3. Protective Terms & Operating Guidelines\n\n"
        for c in clauses:
            md += f"### {c.clause_title}\n"
            md += f"{c.clause_text}\n\n"

        md += """---

## 4. Signatures & Acceptance

IN WITNESS WHEREOF, the parties hereto have executed this Statement of Work as of the Effective Date.

**For Client:** ___________________________ &nbsp;&nbsp;&nbsp;&nbsp; **Date:** _______________  
**For Contractor:** _______________________ &nbsp;&nbsp;&nbsp;&nbsp; **Date:** _______________
"""

        return SOWResult(
            contract_title=f"SOW — {req.project_title}",
            effective_date=now_str,
            total_budget=total,
            milestones=milestones,
            protective_clauses=clauses,
            formatted_markdown_contract=md,
        )

    def get_standard_protective_clauses(self) -> list[ContractClause]:
        """
        Return standard freelance protective contract clauses.
        """
        return [
            ContractClause(
                clause_title="Scope Boundary & Formal Change Orders",
                clause_text=(
                    "Any feature, design revision, or task not explicitly enumerated under the Deliverables section of this SOW "
                    "shall be deemed Out of Scope. Additional requested features will be evaluated under a written Change Order "
                    "specifying additional cost and delivery timeline adjustments prior to execution."
                ),
                purpose="Prevents unpaid scope creep and protects project delivery timelines.",
            ),
            ContractClause(
                clause_title="Intellectual Property Assignment Upon Full Payment",
                clause_text=(
                    "Upon receipt of full and final payment for each milestone, Contractor assigns to Client all right, title, "
                    "and interest in the custom deliverables created under that milestone. Pre-existing code templates and tools "
                    "remain the property of Contractor and are licensed to Client on a perpetual, royalty-free basis."
                ),
                purpose="Secures contractor ownership until final milestone payments clear.",
            ),
            ContractClause(
                clause_title="Client Review Window & Deemed Acceptance",
                clause_text=(
                    "Client shall have five (5) business days following milestone delivery to review and test deliverables against "
                    "the Acceptance Criteria. If no written notice of rejection is provided within this window, deliverables shall be "
                    "deemed accepted and corresponding milestone payments shall be released."
                ),
                purpose="Prevents ghosting and delayed sign-offs after milestone completion.",
            ),
            ContractClause(
                clause_title="Late Payment & Suspension of Work",
                clause_text=(
                    "Invoices overdue by more than seven (7) business days shall incur a late charge of 1.5% per month. Contractor "
                    "reserves the right to pause active development and withhold production deployments until account is brought current."
                ),
                purpose="Ensures cash flow integrity during active multi-week engagements.",
            ),
        ]
