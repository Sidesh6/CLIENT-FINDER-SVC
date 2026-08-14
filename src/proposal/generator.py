"""
Context-aware AI proposal generator coordinating LLM generation, heuristics, and pitch strategy.
"""

import json
import logging
from typing import Any

from src.ai.client import BaseLLMClient, get_llm_client
from src.models.profile import UserProfile, get_default_profile
from src.models.project import Project
from src.proposal.heuristic import HeuristicProposalGenerator
from src.proposal.prompts import PROPOSAL_SYSTEM_PROMPT, build_proposal_prompt
from src.proposal.schemas import (
    PitchAngle,
    ProposalRequest,
    ProposalResult,
    ProposalTone,
)
from src.scoring.schemas import OpportunityScoreBreakdown

logger = logging.getLogger("ProposalGenerator")


class ProposalGenerator:
    """
    Coordinates context-aware proposal and cover letter synthesis.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        default_profile: UserProfile | None = None,
    ):
        self.llm_client = llm_client if llm_client is not None else get_llm_client()
        self.default_profile = default_profile or get_default_profile()
        self.heuristic_generator = HeuristicProposalGenerator()

    def auto_select_pitch_angle(
        self,
        project: Project | dict[str, Any],
        score_breakdown: OpportunityScoreBreakdown | None = None,
    ) -> PitchAngle:
        """
        Intelligently recommend the optimal pitch angle based on project signals.
        """
        if isinstance(project, Project):
            title = project.title.lower()
            desc = project.description.lower()
            category = (project.category or "").lower()
            skills = {s.lower() for s in project.skills}
            budget = project.budget
        else:
            title = str(project.get("title", "")).lower()
            desc = str(project.get("description", "")).lower()
            category = str(project.get("category", "")).lower()
            skills = {s.lower() for s in project.get("skills", [])}
            budget = project.get("budget")

        text = f"{title} {desc}"

        # 1. Urgent timeline signals -> Fast Delivery
        if any(w in text for w in ["urgent", "asap", "immediate", "quick turnaround", "fast"]):
            return PitchAngle.FAST_DELIVERY

        # 2. High-budget or business outcome signals -> Value ROI
        if (budget and budget >= 5000.0) or any(
            w in text for w in ["roi", "revenue", "conversion", "cost reduction"]
        ):
            return PitchAngle.VALUE_ROI

        # 3. High-complexity or advanced AI stack -> Technical Expert
        if "ai" in category or (
            skills & {"langchain", "rag", "pytorch", "kubernetes", "vector database"}
        ):
            return PitchAngle.TECHNICAL_EXPERT

        # 4. Track record or case study requests -> Portfolio Proof
        if any(
            w in text for w in ["case study", "portfolio", "past work", "examples", "references"]
        ):
            return PitchAngle.PORTFOLIO_PROOF

        # 5. Open-ended MVP / architecture inquiry -> Consultative Advisor
        if any(w in text for w in ["mvp", "advice", "consult", "strategy", "roadmap", "options"]):
            return PitchAngle.CONSULTATIVE_ADVISOR

        return PitchAngle.TECHNICAL_EXPERT

    def generate(self, request: ProposalRequest) -> ProposalResult:
        """
        Generate customized proposal using LLM or rule-based fallback.
        """
        profile = request.user_profile or self.default_profile
        pitch_angle = request.pitch_angle

        # If LLM client is available, attempt AI generation
        if self.llm_client:
            prompt = build_proposal_prompt(
                project=request.project,
                profile=profile,
                pitch_angle=pitch_angle,
                tone=request.tone,
                include_pricing=request.include_pricing,
                custom_instructions=request.custom_instructions,
            )

            try:
                raw_response = self.llm_client.generate(
                    prompt=prompt,
                    system_prompt=PROPOSAL_SYSTEM_PROMPT,
                    temperature=0.4,
                )

                parsed_json = self._parse_llm_json(raw_response)
                if parsed_json and "hook" in parsed_json and "body" in parsed_json:
                    quality = self.evaluate_quality(parsed_json, request.project)
                    return ProposalResult(
                        subject_line=parsed_json.get(
                            "subject_line", f"Proposal for {getattr(request.project, 'title', '')}"
                        ),
                        hook=parsed_json["hook"],
                        body=parsed_json["body"],
                        relevant_projects=parsed_json.get("relevant_projects", []),
                        call_to_action=parsed_json.get(
                            "call_to_action", "Let's connect for a brief call."
                        ),
                        pricing_quote=parsed_json.get("pricing_quote"),
                        full_proposal_text=parsed_json.get(
                            "full_proposal_text",
                            f"{parsed_json['hook']}\n\n{parsed_json['body']}",
                        ),
                        pitch_angle=pitch_angle,
                        quality_score=quality,
                    )
            except Exception as exc:
                logger.warning(
                    "LLM proposal generation encountered error, falling back to heuristic: %s", exc
                )

        # Fallback to rule-based heuristic generator
        return self.heuristic_generator.generate(
            project=request.project,
            profile=profile,
            pitch_angle=pitch_angle,
            tone=request.tone,
            include_pricing=request.include_pricing,
        )

    def generate_for_project(
        self,
        project: Project | dict[str, Any],
        profile: UserProfile | None = None,
        pitch_angle: PitchAngle | None = None,
        tone: ProposalTone = ProposalTone.CONFIDENT,
        include_pricing: bool = True,
        custom_instructions: str | None = None,
    ) -> ProposalResult:
        """
        Convenience method to generate proposal with automatic pitch angle selection if omitted.
        """
        selected_angle = pitch_angle or self.auto_select_pitch_angle(project)
        request = ProposalRequest(
            project=project,
            user_profile=profile or self.default_profile,
            pitch_angle=selected_angle,
            tone=tone,
            include_pricing=include_pricing,
            custom_instructions=custom_instructions,
        )
        return self.generate(request)

    def evaluate_quality(
        self, proposal_data: dict[str, Any] | ProposalResult, project: Project | dict[str, Any]
    ) -> float:
        """
        Evaluate proposal quality on a 0-100 scale based on completeness, relevance, and punchiness.
        """
        score = 70.0  # Base quality
        if isinstance(proposal_data, ProposalResult):
            hook = proposal_data.hook
            body = proposal_data.body
            cta = proposal_data.call_to_action
            case_studies = proposal_data.relevant_projects
        else:
            hook = str(proposal_data.get("hook", ""))
            body = str(proposal_data.get("body", ""))
            cta = str(proposal_data.get("call_to_action", ""))
            case_studies = list(proposal_data.get("relevant_projects", []))

        # Check hook length & punchiness
        if 40 <= len(hook) <= 300:
            score += 8.0

        # Check body technical depth
        if 150 <= len(body) <= 1200:
            score += 8.0

        # Check case studies presence
        if len(case_studies) >= 2:
            score += 7.0

        # Check actionable CTA
        if len(cta) >= 20 and any(
            w in cta.lower() for w in ["call", "chat", "connect", "discuss", "kickoff"]
        ):
            score += 7.0

        return max(0.0, min(100.0, round(score, 1)))

    def _parse_llm_json(self, raw_response: str) -> dict[str, Any] | None:
        """Clean markdown markers and parse JSON output."""
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception:
            return None
