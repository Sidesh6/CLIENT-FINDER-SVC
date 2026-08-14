"""
User profile and skill proficiency data models.
"""

from pydantic import BaseModel, Field

from src.ai.schemas import ExperienceLevel, PaymentType, ProjectCategory


class SkillProficiency(BaseModel):
    """
    Individual technical skill with proficiency ranking (1 to 10 scale).
    """

    name: str = Field(min_length=1, description="Canonical or recognizable skill name")
    proficiency: int = Field(
        default=8,
        ge=1,
        le=10,
        description="Proficiency level on a 1-10 scale (1=Novice, 10=World-class Master)",
    )
    years_of_experience: float | None = Field(
        default=None,
        ge=0,
        description="Years of professional experience with this technology",
    )
    is_primary: bool = Field(
        default=True,
        description="Whether this is a primary core skill or a secondary skill",
    )


class UserProfile(BaseModel):
    """
    Developer profile defining technical capabilities, preferred compensation,
    and target project categories.
    """

    user_id: str = Field(default="default_user", description="Unique user identifier")
    name: str = Field(default="Developer", description="User's full name")
    title: str = Field(
        default="Senior Full-Stack AI & Python Engineer",
        description="Professional headline",
    )
    bio: str | None = Field(
        default=None,
        description="Short summary of background and expertise",
    )
    skills: list[SkillProficiency] = Field(
        default_factory=list,
        description="List of technical skills and proficiencies",
    )
    preferred_categories: list[ProjectCategory] = Field(
        default_factory=lambda: [
            ProjectCategory.AI_DEVELOPMENT,
            ProjectCategory.WEB_DEVELOPMENT,
            ProjectCategory.AUTOMATION_SCRAPING,
            ProjectCategory.SYSTEMS_BACKEND,
        ],
        description="Target project domains",
    )
    minimum_hourly_rate: float | None = Field(
        default=50.0,
        ge=0,
        description="Minimum acceptable hourly rate in USD",
    )
    target_hourly_rate: float | None = Field(
        default=90.0,
        ge=0,
        description="Target ideal hourly rate in USD",
    )
    minimum_fixed_budget: float | None = Field(
        default=1000.0,
        ge=0,
        description="Minimum acceptable fixed-price budget in USD",
    )
    preferred_payment_types: list[PaymentType] = Field(
        default_factory=lambda: [
            PaymentType.HOURLY,
            PaymentType.FIXED_PRICE,
            PaymentType.CONTRACT,
        ],
        description="Preferred engagement payment models",
    )
    target_experience_level: ExperienceLevel = Field(
        default=ExperienceLevel.SENIOR,
        description="Target seniority level for opportunities",
    )

    def get_skill_names(self) -> set[str]:
        """Return lowercase set of all skill names in the profile."""
        return {s.name.lower() for s in self.skills}

    def get_skill_map(self) -> dict[str, SkillProficiency]:
        """Return dictionary mapping lowercase skill name to SkillProficiency object."""
        return {s.name.lower(): s for s in self.skills}

    def get_skill_proficiency(self, skill_name: str) -> int | None:
        """Fetch numeric proficiency (1-10) for a given skill if present."""
        prof = self.get_skill_map().get(skill_name.lower())
        return prof.proficiency if prof else None


def get_default_profile() -> UserProfile:
    """
    Factory creating a comprehensive default profile for a Senior AI & Python Engineer.
    """
    return UserProfile(
        user_id="default_engineer",
        name="Alex Mercer",
        title="Senior Full-Stack AI & Python Engineer",
        bio="Specialized in building RAG systems, LLM agents, FastAPI microservices, and modern web applications.",
        skills=[
            # Core AI / ML
            SkillProficiency(
                name="Python", proficiency=10, years_of_experience=7.0, is_primary=True
            ),
            SkillProficiency(
                name="FastAPI", proficiency=10, years_of_experience=5.0, is_primary=True
            ),
            SkillProficiency(
                name="LangChain", proficiency=9, years_of_experience=2.5, is_primary=True
            ),
            SkillProficiency(
                name="LlamaIndex", proficiency=9, years_of_experience=2.0, is_primary=True
            ),
            SkillProficiency(name="RAG", proficiency=10, years_of_experience=3.0, is_primary=True),
            SkillProficiency(
                name="OpenAI", proficiency=10, years_of_experience=3.0, is_primary=True
            ),
            SkillProficiency(name="LLM", proficiency=10, years_of_experience=3.0, is_primary=True),
            SkillProficiency(
                name="PyTorch", proficiency=8, years_of_experience=4.0, is_primary=True
            ),
            SkillProficiency(
                name="Vector Database", proficiency=9, years_of_experience=3.0, is_primary=True
            ),
            SkillProficiency(
                name="HuggingFace", proficiency=8, years_of_experience=3.0, is_primary=False
            ),
            # Databases & Infrastructure
            SkillProficiency(
                name="PostgreSQL", proficiency=9, years_of_experience=6.0, is_primary=True
            ),
            SkillProficiency(name="SQL", proficiency=9, years_of_experience=7.0, is_primary=True),
            SkillProficiency(
                name="Redis", proficiency=8, years_of_experience=4.0, is_primary=False
            ),
            SkillProficiency(
                name="Docker", proficiency=9, years_of_experience=5.0, is_primary=True
            ),
            SkillProficiency(name="AWS", proficiency=8, years_of_experience=4.0, is_primary=False),
            # Frontend & Web
            SkillProficiency(
                name="TypeScript", proficiency=8, years_of_experience=4.0, is_primary=False
            ),
            SkillProficiency(
                name="JavaScript", proficiency=8, years_of_experience=5.0, is_primary=False
            ),
            SkillProficiency(
                name="React", proficiency=8, years_of_experience=4.0, is_primary=False
            ),
            SkillProficiency(
                name="Next.js", proficiency=8, years_of_experience=3.0, is_primary=False
            ),
            SkillProficiency(
                name="TailwindCSS", proficiency=8, years_of_experience=3.0, is_primary=False
            ),
            # Automation & Scraping
            SkillProficiency(
                name="Playwright", proficiency=9, years_of_experience=3.0, is_primary=True
            ),
            SkillProficiency(
                name="Web Scraping", proficiency=9, years_of_experience=5.0, is_primary=True
            ),
            SkillProficiency(
                name="Selenium", proficiency=8, years_of_experience=4.0, is_primary=False
            ),
        ],
        preferred_categories=[
            ProjectCategory.AI_DEVELOPMENT,
            ProjectCategory.WEB_DEVELOPMENT,
            ProjectCategory.AUTOMATION_SCRAPING,
            ProjectCategory.SYSTEMS_BACKEND,
        ],
        minimum_hourly_rate=50.0,
        target_hourly_rate=95.0,
        minimum_fixed_budget=1000.0,
        preferred_payment_types=[
            PaymentType.HOURLY,
            PaymentType.FIXED_PRICE,
            PaymentType.CONTRACT,
        ],
        target_experience_level=ExperienceLevel.SENIOR,
    )
