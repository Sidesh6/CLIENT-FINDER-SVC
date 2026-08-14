"""
AI Proposal Quality, Win-Rate Readiness, and Conversion Auditor.
Evaluates draft proposals across 5 dimensions: Specificity, Social Proof, CTA, Brevity, and Pricing.
"""

import re

from pydantic import BaseModel, Field


class ProposalAuditRequest(BaseModel):
    """Inbound request payload for proposal conversion readiness audit."""

    proposal_text: str = Field(description="Draft proposal or cover letter text")
    project_title: str = Field(description="Target project title")
    project_description: str = Field(default="", description="Original project requirements")
    target_skills: list[str] = Field(default_factory=list, description="Target technical skills")
    target_budget: float | None = Field(default=None, description="Proposed or target budget")


class ProposalAuditDimension(BaseModel):
    """Score and feedback for an individual conversion dimension."""

    dimension_name: str
    score: float = Field(ge=0.0, le=100.0)
    passed: bool
    feedback: str


class ProposalAuditResult(BaseModel):
    """Complete proposal readiness assessment and actionable optimization recommendations."""

    overall_readiness_score: float = Field(ge=0.0, le=100.0)
    grade: str
    word_count: int
    dimensions: list[ProposalAuditDimension]
    detected_strengths: list[str]
    actionable_recommendations: list[str]


class ProposalAuditor:
    """
    Evaluates proposal drafts against commercial conversion heuristics.
    """

    def audit(self, req: ProposalAuditRequest) -> ProposalAuditResult:
        """
        Perform multidimensional audit on the given proposal text.
        """
        text = req.proposal_text.strip()
        words = text.split()
        word_count = len(words)

        dimensions: list[ProposalAuditDimension] = []
        strengths: list[str] = []
        recommendations: list[str] = []

        # 1. SPECIFICITY AUDIT
        skills_matched = [s for s in req.target_skills if s.lower() in text.lower()]
        title_words = [w.lower() for w in re.findall(r"\w+", req.project_title) if len(w) > 3]
        title_matched = [w for w in title_words if w in text.lower()]

        spec_score = 40.0
        if skills_matched:
            spec_score += min(40.0, len(skills_matched) * 15.0)
        if title_matched:
            spec_score += 20.0
        spec_score = min(100.0, spec_score)

        if spec_score >= 70.0:
            strengths.append(
                f"Strong technical specificity citing relevant tools ({', '.join(skills_matched[:3]) or 'target stack'})."
            )
            spec_feedback = "Proposal directly addresses client's tech stack and project domain."
        else:
            recommendations.append(
                "Mention the client's specific technologies (e.g. "
                + ", ".join(req.target_skills[:3] or ["FastAPI", "Python"])
                + ") to avoid sounding like a generic template."
            )
            spec_feedback = (
                "Lacks direct references to the client's explicit technical requirements."
            )

        dimensions.append(
            ProposalAuditDimension(
                dimension_name="Specificity & Diagnosis",
                score=round(spec_score, 1),
                passed=spec_score >= 70.0,
                feedback=spec_feedback,
            )
        )

        # 2. SOCIAL PROOF & QUANTITATIVE METRICS AUDIT
        metric_matches = re.findall(
            r"(\d+%\s*|\d+x\s*|\$\d+[\d,]*|\d+\+?\s*(hours|days|weeks|months|users|rps))",
            text,
            re.IGNORECASE,
        )
        case_study_phrases = [
            "in past projects",
            "previously built",
            "delivered",
            "reduced",
            "scaled to",
            "achieved",
            "case study",
            "portfolio",
        ]
        has_case_study = any(p in text.lower() for p in case_study_phrases)

        proof_score = 30.0
        if metric_matches:
            proof_score += min(40.0, len(metric_matches) * 20.0)
        if has_case_study:
            proof_score += 30.0
        proof_score = min(100.0, proof_score)

        if proof_score >= 70.0:
            strengths.append("Contains concrete quantitative proof and past achievements.")
            proof_feedback = "Includes verified metrics or relevant case study references."
        else:
            recommendations.append(
                "Include at least one measurable past achievement (e.g., 'reduced API latency by 45%', 'scaled to 50k DAU')."
            )
            proof_feedback = (
                "Needs concrete quantitative results rather than unverified assertions."
            )

        dimensions.append(
            ProposalAuditDimension(
                dimension_name="Social Proof & Metrics",
                score=round(proof_score, 1),
                passed=proof_score >= 70.0,
                feedback=proof_feedback,
            )
        )

        # 3. CALL TO ACTION (CTA) AUDIT
        cta_keywords = [
            "call",
            "chat",
            "zoom",
            "loom",
            "discuss",
            "hop on",
            "available",
            "schedule",
            "free for a quick",
        ]
        has_cta = any(k in text.lower() for k in cta_keywords)
        has_question_mark = "?" in text

        cta_score = 30.0
        if has_cta:
            cta_score += 40.0
        if has_question_mark:
            cta_score += 30.0
        cta_score = min(100.0, cta_score)

        if cta_score >= 70.0:
            strengths.append("Clear, frictionless Call-to-Action inviting next steps.")
            cta_feedback = "Direct and conversational closing inviting low-commitment alignment."
        else:
            recommendations.append(
                "End with a low-friction question (e.g., 'Are you free for a quick 10-minute chat this Tuesday?')."
            )
            cta_feedback = (
                "Missing an explicit, conversational Call-to-Action to prompt client reply."
            )

        dimensions.append(
            ProposalAuditDimension(
                dimension_name="Call to Action (CTA)",
                score=round(cta_score, 1),
                passed=cta_score >= 70.0,
                feedback=cta_feedback,
            )
        )

        # 4. BREVITY & READABILITY AUDIT (Optimal: 80 - 280 words)
        if 80 <= word_count <= 260:
            brevity_score = 100.0
            brevity_feedback = (
                f"Ideal length ({word_count} words). Highly readable on mobile and desktop."
            )
            strengths.append(f"Optimal conciseness ({word_count} words) respects client attention.")
        elif word_count < 80:
            brevity_score = max(40.0, (word_count / 80.0) * 80.0)
            brevity_feedback = (
                f"Too brief ({word_count} words). May appear low-effort to discerning clients."
            )
            recommendations.append(
                "Expand slightly on your technical approach or relevant case studies."
            )
        else:  # word_count > 260
            brevity_score = max(50.0, 100.0 - ((word_count - 260) / 4.0))
            brevity_feedback = f"Slightly verbose ({word_count} words). Founders often skim proposals longer than 250 words."
            recommendations.append(
                "Trim filler sentences to keep proposal tightly focused under 250 words."
            )

        dimensions.append(
            ProposalAuditDimension(
                dimension_name="Brevity & Readability",
                score=round(brevity_score, 1),
                passed=brevity_score >= 70.0,
                feedback=brevity_feedback,
            )
        )

        # 5. RISK & PRICING TRANSPARENCY AUDIT
        pricing_terms = [
            "milestone",
            "sprint",
            "$",
            "rate",
            "phase 1",
            "timeline",
            "scope",
            "deposit",
        ]
        has_pricing_terms = any(t in text.lower() for t in pricing_terms)
        risk_score = 75.0 if has_pricing_terms else 55.0

        if risk_score >= 70.0:
            risk_feedback = "Includes structured milestone delivery or pricing framing."
        else:
            recommendations.append(
                "Mention a phased milestone structure or clear timeline to reduce client perceived risk."
            )
            risk_feedback = "Could benefit from mentioning delivery phases or milestone structure."

        dimensions.append(
            ProposalAuditDimension(
                dimension_name="Risk & Scope Transparency",
                score=round(risk_score, 1),
                passed=risk_score >= 70.0,
                feedback=risk_feedback,
            )
        )

        # Compute Overall Score (Weighted)
        weights = [0.25, 0.25, 0.20, 0.15, 0.15]
        overall = sum(d.score * w for d, w in zip(dimensions, weights, strict=False))
        overall = round(overall, 1)

        if overall >= 88.0:
            grade = "EXCELLENT"
        elif overall >= 75.0:
            grade = "STRONG"
        elif overall >= 60.0:
            grade = "NEEDS_IMPROVEMENT"
        else:
            grade = "POOR"

        return ProposalAuditResult(
            overall_readiness_score=overall,
            grade=grade,
            word_count=word_count,
            dimensions=dimensions,
            detected_strengths=strengths,
            actionable_recommendations=recommendations,
        )
