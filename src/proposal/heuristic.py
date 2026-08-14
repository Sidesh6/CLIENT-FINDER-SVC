"""
Heuristic rule-based proposal generator for offline, instant, and high-converting proposals.
"""

from typing import Any

from src.models.profile import UserProfile
from src.models.project import Project
from src.proposal.schemas import PitchAngle, ProposalResult, ProposalTone


class HeuristicProposalGenerator:
    """
    Synthesizes customized proposals using deterministic domain rules and templates.
    """

    def generate(
        self,
        project: Project | dict[str, Any],
        profile: UserProfile,
        pitch_angle: PitchAngle = PitchAngle.TECHNICAL_EXPERT,
        tone: ProposalTone = ProposalTone.CONFIDENT,
        include_pricing: bool = True,
    ) -> ProposalResult:
        """Generate tailored proposal structure."""
        if isinstance(project, Project):
            title = project.title
            skills = project.skills or ["Python", "Backend"]
            budget = project.budget
            currency = project.currency or "USD"
            project_type = project.project_type or "Contract"
        else:
            title = str(project.get("title", "Project"))
            skills = list(project.get("skills", ["Python", "Backend"]))
            budget = project.get("budget")
            currency = str(project.get("currency", "USD"))
            project_type = str(project.get("project_type", "Contract"))

        primary_tech = skills[0] if skills else "Software Engineering"
        tech_list_str = ", ".join(skills[:3]) if skills else "modern tech stack"

        # 1. Subject Line
        subject_line = self._generate_subject(title, primary_tech, pitch_angle)

        # 2. Opening Hook
        hook = self._generate_hook(title, primary_tech, tech_list_str, pitch_angle)

        # 3. Main Solution Body
        body = self._generate_body(tech_list_str, pitch_angle, profile)

        # 4. Relevant Projects & Case Studies
        relevant_projects = self._generate_case_studies(skills, profile)

        # 5. Pricing Quote
        pricing_quote = self._generate_pricing(
            budget, currency, project_type, profile, include_pricing
        )

        # 6. Call to Action
        cta = self._generate_cta(pitch_angle)

        # 7. Assemble Full Proposal Markdown
        full_text = self._assemble_full_proposal(
            profile_name=profile.name,
            profile_title=profile.title,
            subject=subject_line,
            hook=hook,
            body=body,
            relevant_projects=relevant_projects,
            pricing=pricing_quote,
            cta=cta,
        )

        return ProposalResult(
            subject_line=subject_line,
            hook=hook,
            body=body,
            relevant_projects=relevant_projects,
            call_to_action=cta,
            pricing_quote=pricing_quote,
            full_proposal_text=full_text,
            pitch_angle=pitch_angle,
            quality_score=90.0,
        )

    def _generate_subject(self, title: str, primary_tech: str, angle: PitchAngle) -> str:
        """Generate high-open subject line."""
        clean_title = title.split("|")[0].split("-")[0].strip()[:40]
        if angle == PitchAngle.FAST_DELIVERY:
            return f"Quick Solution & Immediate Availability: {clean_title} ({primary_tech})"
        elif angle == PitchAngle.VALUE_ROI:
            return f"High-ROI Execution for {clean_title} • {primary_tech} Engineer"
        elif angle == PitchAngle.PORTFOLIO_PROOF:
            return f"Past Case Studies & Technical Approach: {clean_title}"
        elif angle == PitchAngle.CONSULTATIVE_ADVISOR:
            return f"Architectural Approach & Discovery for {clean_title}"
        return f"Senior {primary_tech} Specialist for {clean_title}"

    def _generate_hook(
        self, title: str, primary_tech: str, tech_list: str, angle: PitchAngle
    ) -> str:
        """Craft specific opening hook."""
        if angle == PitchAngle.TECHNICAL_EXPERT:
            return (
                f"I reviewed your requirements for '{title[:50]}' and can design a robust, "
                f"production-grade architecture utilizing {tech_list}."
            )
        elif angle == PitchAngle.FAST_DELIVERY:
            return (
                f"I have immediate availability to step in and deliver a clean, tested MVP for "
                f"'{title[:50]}' using {tech_list} within your target timeline."
            )
        elif angle == PitchAngle.VALUE_ROI:
            return (
                f"Your project presents a great opportunity to build a high-performance system with {tech_list} "
                f"while optimizing for low operational overhead and rapid time-to-market."
            )
        elif angle == PitchAngle.PORTFOLIO_PROOF:
            return (
                f"I have previously built and deployed similar production systems powered by {tech_list}, "
                f"making this engagement a direct match for my technical background."
            )
        else:  # CONSULTATIVE_ADVISOR
            return (
                f"I analyzed your project goals for '{title[:50]}' and see a few high-impact architectural choices "
                f"that will ensure scalability across your {tech_list} stack."
            )

    def _generate_body(self, tech_list: str, angle: PitchAngle, profile: UserProfile) -> str:
        """Generate core technical approach."""
        if angle == PitchAngle.TECHNICAL_EXPERT:
            return (
                f"As a {profile.title}, I specialize in building type-safe, resilient backend architectures. "
                f"For this system, I will implement clean separation of concerns, comprehensive automated test coverage, "
                f"and optimized data pipelines across {tech_list} to guarantee sub-second latency and seamless maintainability."
            )
        elif angle == PitchAngle.FAST_DELIVERY:
            return (
                f"My workflow is geared towards fast, iterative milestones. I break delivery into concrete sprint targets: "
                f"Day 1-2 for core schema & infrastructure setup, Day 3-5 for feature implementation across {tech_list}, "
                f"and Day 6-7 for end-to-end testing and deployment handover."
            )
        elif angle == PitchAngle.VALUE_ROI:
            return (
                f"I focus on delivering pragmatic, high-leverage software. By selecting proven patterns in {tech_list}, "
                f"we can minimize infrastructure cloud costs and eliminate technical debt upfront, "
                f"ensuring your engineering spend translates directly into measurable product velocity."
            )
        elif angle == PitchAngle.PORTFOLIO_PROOF:
            return (
                f"Over the past several years, I have architected distributed systems and AI integrations in {tech_list}. "
                f"My previous implementations maintain 99.9% uptime and handle high-throughput workloads with zero data loss."
            )
        else:
            return (
                f"Rather than jumping into assumptions, I like to evaluate your specific scale requirements and constraints. "
                f"We can explore either a lightweight monolithic approach or modular microservices in {tech_list} "
                f"depending on your team's immediate roadmap."
            )

    def _generate_case_studies(self, skills: list[str], profile: UserProfile) -> list[str]:
        """Generate relevant case study highlights."""
        highlights = [
            f"Built and scaled a production backend microservice in {skills[0] if skills else 'Python'}, reducing latency by 45%.",
            "Designed end-to-end data pipelines and automated workflows handling 50k+ daily transactions.",
            "Implemented modern CI/CD, containerized deployments, and full test suites with 90%+ code coverage.",
        ]
        return highlights

    def _generate_pricing(
        self,
        budget: float | None,
        currency: str,
        project_type: str,
        profile: UserProfile,
        include_pricing: bool,
    ) -> str | None:
        """Construct commercial quote."""
        if not include_pricing:
            return None

        if budget:
            return f"{currency} {budget:,.0f} ({project_type})"
        rate = profile.target_hourly_rate or 95.0
        return f"${rate:.0f}/hr (Estimated milestones provided upon initial scope confirmation)"

    def _generate_cta(self, angle: PitchAngle) -> str:
        """Construct frictionless call to action."""
        if angle == PitchAngle.FAST_DELIVERY:
            return "I am available to start immediately this week. When is a good time for a brief 10-minute kickoff chat?"
        elif angle == PitchAngle.CONSULTATIVE_ADVISOR:
            return "Would you be open to a complimentary 15-minute architecture brainstorm call to align on scope?"
        return "Let me know if you'd like to review live demo references or discuss milestones in a quick 15-minute call."

    def _assemble_full_proposal(
        self,
        profile_name: str,
        profile_title: str,
        subject: str,
        hook: str,
        body: str,
        relevant_projects: list[str],
        pricing: str | None,
        cta: str,
    ) -> str:
        """Assemble full Markdown proposal letter."""
        projects_md = "\n".join([f"• {p}" for p in relevant_projects])
        pricing_md = f"\n**Proposed Investment:** {pricing}\n" if pricing else ""

        return f"""**Subject:** {subject}

Hi there,

{hook}

{body}

**Relevant Track Record & Case Studies:**
{projects_md}
{pricing_md}
{cta}

Best regards,
**{profile_name}**
{profile_title}
"""
