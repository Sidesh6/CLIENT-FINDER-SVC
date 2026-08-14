"""
Commercial Client Negotiation and Objection Handling Engine.
Synthesizes high-conversion counter-offers, scope modulation trade-offs, and commercial response scripts.
"""

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.models.profile import UserProfile, get_default_profile

logger = logging.getLogger("NegotiationAdvisor")


class ObjectionType(str, Enum):
    """Common objections encountered during freelance and agency closing conversations."""

    RATE_TOO_HIGH = "RATE_TOO_HIGH"
    FIXED_PRICE_REQUEST = "FIXED_PRICE_REQUEST"
    TIGHT_DEADLINE = "TIGHT_DEADLINE"
    LACK_OF_DIRECT_EXPERIENCE = "LACK_OF_DIRECT_EXPERIENCE"
    SCOPE_UNCERTAINTY = "SCOPE_UNCERTAINTY"
    COMPETITOR_COMPARISON = "COMPETITOR_COMPARISON"


class NegotiationStrategy(str, Enum):
    """Proven sales strategies to counter client objections without compromising professional yield."""

    VALUE_ANCHORING = "VALUE_ANCHORING"
    SCOPE_MODULATION = "SCOPE_MODULATION"
    MILESTONE_SPLIT = "MILESTONE_SPLIT"
    DISCOUNT_FOR_TERM = "DISCOUNT_FOR_TERM"
    DEPOSIT_RETAINER = "DEPOSIT_RETAINER"


class NegotiationRequest(BaseModel):
    """Inbound request payload for commercial counter-offer synthesis."""

    project_title: str = Field(description="Title of the target opportunity")
    project_description: str = Field(description="Scope description or context")
    objection_type: ObjectionType = Field(
        default=ObjectionType.RATE_TOO_HIGH, description="Type of client objection"
    )
    strategy: NegotiationStrategy = Field(
        default=NegotiationStrategy.VALUE_ANCHORING, description="Negotiation strategy"
    )
    client_message: str | None = Field(
        default=None, description="Actual quote or message from client"
    )
    target_hourly_rate: float = Field(
        default=95.0, ge=10.0, description="Developer target standard hourly rate"
    )
    client_budget: float | None = Field(
        default=None, description="Client stated budget or proposed rate limit"
    )


class NegotiationResponse(BaseModel):
    """Structured response script and counter-offer package."""

    strategy_used: NegotiationStrategy
    objection_type: ObjectionType
    recommended_response: str
    alternative_counter_offer: str
    commercial_terms: dict[str, Any]
    concession_rules: list[str]


class NegotiationAdvisor:
    """
    Expert sales advisor generating context-aware objection responses and structured counter-proposals.
    """

    def __init__(self, default_profile: UserProfile | None = None):
        self.default_profile = default_profile or get_default_profile()

    def advise(
        self,
        req: NegotiationRequest,
        profile: UserProfile | None = None,
    ) -> NegotiationResponse:
        """
        Generate strategic negotiation script and terms based on objection type and chosen strategy.
        """
        user_prof = profile or self.default_profile
        rate = req.target_hourly_rate or user_prof.target_hourly_rate or 95.0
        client_bud = req.client_budget

        if req.objection_type == ObjectionType.RATE_TOO_HIGH:
            return self._handle_rate_too_high(req, rate, client_bud, user_prof)
        elif req.objection_type == ObjectionType.FIXED_PRICE_REQUEST:
            return self._handle_fixed_price_request(req, rate, user_prof)
        elif req.objection_type == ObjectionType.TIGHT_DEADLINE:
            return self._handle_tight_deadline(req, rate, user_prof)
        elif req.objection_type == ObjectionType.SCOPE_UNCERTAINTY:
            return self._handle_scope_uncertainty(req, rate, user_prof)
        else:
            return self._handle_generic_objection(req, rate, user_prof)

    def _handle_rate_too_high(
        self,
        req: NegotiationRequest,
        rate: float,
        client_bud: float | None,
        profile: UserProfile,
    ) -> NegotiationResponse:
        budget_ref = f"${client_bud:,.2f}" if client_bud else "your allocated budget"

        if req.strategy == NegotiationStrategy.VALUE_ANCHORING:
            response_text = (
                f"Hi there,\n\n"
                f"I completely understand budget considerations are critical for '{req.project_title}'. "
                f"My standard rate of ${rate:.0f}/hr reflects a senior-level focus that emphasizes getting the architecture "
                f"and core features right on the first iteration without technical debt or rework.\n\n"
                f"In past projects, this proactive approach has consistently reduced debugging cycles by over 40% and delivered "
                f"a rock-solid foundation that scales effortlessly. I'd love to hop on a quick 15-minute alignment call to review "
                f"the critical path deliverables and make sure we maximize every dollar spent."
            )
            counter = (
                f"Offer an initial 10-hour exploratory milestone at ${rate:.0f}/hr ($ {rate * 10:,.0f}) to deliver the core MVP architecture "
                f"and validate delivery velocity before committing to the full project scope."
            )
        elif req.strategy == NegotiationStrategy.SCOPE_MODULATION:
            response_text = (
                f"Hi there,\n\n"
                f"I want to make sure we make '{req.project_title}' a complete success while staying within {budget_ref}. "
                f"Rather than compromising on code quality or testing by lowering the hourly rate, I propose we streamline the "
                f"initial Phase 1 scope to the absolute must-have core deliverables.\n\n"
                f"This guarantees you get a fully functional, production-ready release on schedule, and we can defer nice-to-have "
                f"enhancements to a subsequent Phase 2 once initial traction is established."
            )
            counter = "Split deliverables into Phase 1 (Core MVP within budget) and Phase 2 (Optional extensions)."
        elif req.strategy == NegotiationStrategy.DISCOUNT_FOR_TERM:
            disc_rate = round(rate * 0.9, 0)
            response_text = (
                f"Hi there,\n\n"
                f"While my standard rate is ${rate:.0f}/hr, if we structure this as a dedicated monthly retainer (e.g., 20+ hours/week "
                f"for a minimum of 2 months), I can adjust my rate to ${disc_rate:.0f}/hr.\n\n"
                f"This provides you guaranteed priority capacity and predictable monthly velocity while keeping overall development costs within target."
            )
            counter = f"Structured 2-month retainer at ${disc_rate:.0f}/hr (10% volume discount) with bi-weekly billing."
        else:
            response_text = (
                f"Hi there,\n\n"
                f"To accommodate budget flexibility for '{req.project_title}', we can divide the project into 3 distinct milestones "
                f"with clear acceptance criteria. Each milestone is funded independently upon delivery, giving you total cash flow control."
            )
            counter = "3-part milestone structure with 33% upfront escrow deposit."

        return NegotiationResponse(
            strategy_used=req.strategy,
            objection_type=req.objection_type,
            recommended_response=response_text,
            alternative_counter_offer=counter,
            commercial_terms={
                "base_rate": rate,
                "client_budget": client_bud,
                "strategy": req.strategy.value,
            },
            concession_rules=[
                "Never discount hourly rate without reducing scope or securing a longer-term commitment.",
                "Always anchor on total business value and risk reduction rather than cost of inputs.",
                "Require an upfront deposit (30-50%) before commencement on all milestone arrangements.",
            ],
        )

    def _handle_fixed_price_request(
        self,
        req: NegotiationRequest,
        rate: float,
        profile: UserProfile,
    ) -> NegotiationResponse:
        response_text = (
            f"Hi there,\n\n"
            f"I am open to structuring a fixed-price arrangement for '{req.project_title}'. "
            f"To guarantee we hit every deadline without surprises, I propose a tightly scoped Phase 1 milestone with explicit "
            f"acceptance criteria and deliverable boundaries.\n\n"
            f"Any additional out-of-scope feature requests can be seamlessly logged in a backlog and quoted as modular add-on sprints "
            f"at our agreed benchmark."
        )
        return NegotiationResponse(
            strategy_used=req.strategy,
            objection_type=req.objection_type,
            recommended_response=response_text,
            alternative_counter_offer="Fixed-price Phase 1 milestone with 50% deposit and formal Change Order protocol for additional requests.",
            commercial_terms={
                "base_rate": rate,
                "model": "FIXED_PRICE_MILESTONE",
                "deposit_pct": 50,
            },
            concession_rules=[
                "Fixed price contracts must contain an explicit Deliverables & Acceptance Criteria clause.",
                "Include a 20% buffer in fixed estimates to accommodate discovery and edge cases.",
                "All scope expansions require written approval via change order.",
            ],
        )

    def _handle_tight_deadline(
        self,
        req: NegotiationRequest,
        rate: float,
        profile: UserProfile,
    ) -> NegotiationResponse:
        rush_rate = round(rate * 1.25, 0)
        response_text = (
            f"Hi there,\n\n"
            f"I have the dedicated capacity to fast-track '{req.project_title}' and meet your accelerated launch timeline. "
            f"To execute with maximum velocity, I will dedicate full-time priority focus and utilize pre-built, production-tested "
            f"architectural templates to compress the delivery schedule.\n\n"
            f"Let's confirm the core user flows today so I can spin up the environment and push the initial working build within 48 hours."
        )
        return NegotiationResponse(
            strategy_used=req.strategy,
            objection_type=req.objection_type,
            recommended_response=response_text,
            alternative_counter_offer=f"Dedicated sprint reservation with priority scheduling at ${rush_rate:.0f}/hr rush rate.",
            commercial_terms={
                "base_rate": rate,
                "rush_rate": rush_rate,
                "priority_turnaround": True,
            },
            concession_rules=[
                "Confirm all third-party API credentials and assets prior to project kickoff.",
                "Establish daily asynchronous Loom/Slack check-ins to prevent review bottlenecks.",
            ],
        )

    def _handle_scope_uncertainty(
        self,
        req: NegotiationRequest,
        rate: float,
        profile: UserProfile,
    ) -> NegotiationResponse:
        scoping_fee = round(rate * 6, 0)
        response_text = (
            f"Hi there,\n\n"
            f"It's completely normal for the detailed technical requirements of '{req.project_title}' to evolve during early stages. "
            f"To protect your budget and avoid building unnecessary features, I recommend kicking off with a 2-day Discovery & Architecture Sprint ($ {scoping_fee:,.0f}).\n\n"
            f"During this sprint, I will deliver a comprehensive Technical Blueprint, database schema, and fixed-cost milestone roadmap "
            f"that you can use to build with total confidence."
        )
        return NegotiationResponse(
            strategy_used=req.strategy,
            objection_type=req.objection_type,
            recommended_response=response_text,
            alternative_counter_offer=f"Paid Discovery & Technical Blueprint Sprint ($ {scoping_fee:,.0f}) credited towards full implementation.",
            commercial_terms={"base_rate": rate, "scoping_fee": scoping_fee},
            concession_rules=[
                "Paid discovery de-risks the project and establishes immediate domain authority.",
                "The deliverable is a tangible architectural blueprint with exact milestones.",
            ],
        )

    def _handle_generic_objection(
        self,
        req: NegotiationRequest,
        rate: float,
        profile: UserProfile,
    ) -> NegotiationResponse:
        response_text = (
            f"Hi there,\n\n"
            f"Thank you for sharing your thoughts regarding '{req.project_title}'. My priority is ensuring you achieve a reliable, "
            f"high-performance solution with zero headaches.\n\n"
            f"I would welcome the opportunity to discuss your specific goals and tailor a collaborative approach that fits your roadmap perfectly."
        )
        return NegotiationResponse(
            strategy_used=req.strategy,
            objection_type=req.objection_type,
            recommended_response=response_text,
            alternative_counter_offer="Schedule a 15-minute technical discovery call.",
            commercial_terms={"base_rate": rate},
            concession_rules=["Listen actively to client concerns before presenting solutions."],
        )
