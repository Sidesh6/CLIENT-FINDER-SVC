"""
System prompts and dynamic prompt builders for AI proposal generation.
"""

from typing import Any

from src.models.profile import UserProfile
from src.models.project import Project
from src.proposal.schemas import PitchAngle, ProposalTone

PROPOSAL_SYSTEM_PROMPT = """You are an elite, top 1% freelance client conversion strategist and software proposal specialist.
Your objective is to draft compelling, bespoke client proposals and cover letters that achieve exceptionally high response rates.

Core Principles:
1. NO GENERIC FLUFF: Never start with "I hope this email finds you well" or "I am writing to apply for...".
2. IMMEDIATE RELEVANCE: Start with an attention-grabbing hook that directly diagnoses the client's problem or describes how to build their system.
3. DEMONSTRATE VALUE: Focus on the client's business outcomes, clean system architecture, and fast execution.
4. SPECIFIC TECH INSIGHT: Mention their exact technologies and how they fit together.
5. FRICTIONLESS CTA: End with a zero-pressure call-to-action (e.g. 15-minute architecture brainstorm or immediate demo).

You MUST output ONLY a valid JSON object matching this schema:
{
  "subject_line": "High-converting subject line",
  "hook": "Compelling 1-2 sentence opening hook",
  "body": "Main 2-3 paragraph technical solution, approach, and capability proof",
  "relevant_projects": ["Case study bullet 1", "Case study bullet 2"],
  "call_to_action": "Clear frictionless closing call-to-action",
  "pricing_quote": "Estimated pricing or hourly rate statement",
  "full_proposal_text": "Complete formatted Markdown text combining all sections"
}
"""

PITCH_ANGLE_INSTRUCTIONS: dict[PitchAngle, str] = {
    PitchAngle.TECHNICAL_EXPERT: """
Position yourself as a deep technical authority and architect.
Focus on:
- Production-grade architecture, scalability, clean code, and type safety.
- Specific patterns (e.g., async pipelines, RAG chunking, vector indexing, caching layers).
- Best practices in security, testing, and deployment.
""",
    PitchAngle.FAST_DELIVERY: """
Position yourself as a rapid-execution engineer with immediate availability.
Focus on:
- Delivering a working, tested MVP or prototype within 3-7 days.
- Daily standup communication and rapid feedback cycles.
- Immediate onboarding without ramp-up friction.
""",
    PitchAngle.VALUE_ROI: """
Position yourself as a business-driven software engineer who optimizes for client ROI.
Focus on:
- Business impact: Reducing server costs, automating manual hours, and boosting conversion.
- Pragmatic choices: Avoiding over-engineering to deliver maximum financial value.
- Clear deliverables and milestone-driven ROI.
""",
    PitchAngle.PORTFOLIO_PROOF: """
Position yourself through concrete evidence and past project success.
Focus on:
- Highlighting 2-3 similar systems you have previously shipped.
- Specific measurable metrics (e.g., 'processed 10M events/day', 'sub-50ms latency').
- Offering live demos or architecture walkthroughs.
""",
    PitchAngle.CONSULTATIVE_ADVISOR: """
Position yourself as a strategic engineering partner.
Focus on:
- Asking 2-3 insightful discovery questions about their data model or scale.
- Proposing 2 architectural options (e.g., Quick MVP vs. Scalable Distributed).
- Offering a complimentary 15-minute technical discovery session.
""",
}


def build_proposal_prompt(
    project: Project | dict[str, Any],
    profile: UserProfile,
    pitch_angle: PitchAngle = PitchAngle.TECHNICAL_EXPERT,
    tone: ProposalTone = ProposalTone.CONFIDENT,
    include_pricing: bool = True,
    custom_instructions: str | None = None,
) -> str:
    """
    Construct dynamic prompt for AI proposal generation.
    """
    if isinstance(project, Project):
        title = project.title
        desc = project.description
        source = project.source
        skills = project.skills
        budget = project.budget
        currency = project.currency or "USD"
        project_type = project.project_type
        category = project.category or "Software Engineering"
    else:
        title = str(project.get("title", ""))
        desc = str(project.get("description", ""))
        source = str(project.get("source", "Unknown"))
        skills = list(project.get("skills", []))
        budget = project.get("budget")
        currency = str(project.get("currency", "USD"))
        project_type = project.get("project_type")
        category = str(project.get("category", "Software Engineering"))

    skills_str = ", ".join(skills) if skills else "General Software Stack"
    budget_str = f"{budget} {currency} ({project_type})" if budget else "Competitive / Unstated"

    user_skills = ", ".join([f"{s.name} ({s.proficiency}/10)" for s in profile.skills[:8]])
    target_rate = (
        f"${profile.target_hourly_rate:.0f}/hr" if profile.target_hourly_rate else "$90/hr"
    )
    min_rate = f"${profile.minimum_hourly_rate:.0f}/hr" if profile.minimum_hourly_rate else "$50/hr"

    angle_guide = PITCH_ANGLE_INSTRUCTIONS.get(pitch_angle, "")

    pricing_directive = (
        f"Include a proposed rate or milestone quote aligned with target rate {target_rate}."
        if include_pricing
        else "Do not mention specific pricing numbers yet; focus on technical fit."
    )

    custom_block = f"\nCustom Directives:\n{custom_instructions}\n" if custom_instructions else ""

    return f"""Target Project Opportunity:
- Title: {title}
- Source: {source}
- Category: {category}
- Required Tech Stack: {skills_str}
- Budget: {budget_str}

Project Description:
\"\"\"
{desc}
\"\"\"

Developer Profile Context:
- Name: {profile.name}
- Title: {profile.title}
- Core Skills: {user_skills}
- Target Rate: {target_rate}
- Minimum Hourly Rate: {min_rate}

Strategic Directives:
- Selected Pitch Angle: {pitch_angle.value}
- Desired Tone: {tone.value}
{angle_guide}
- Pricing Strategy: {pricing_directive}
{custom_block}

Generate a concise, punchy, customized proposal JSON object right now. Return JSON ONLY:"""
