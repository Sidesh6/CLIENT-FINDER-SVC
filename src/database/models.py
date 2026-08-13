from dataclasses import dataclass, field


@dataclass
class Project:
    """
    Represents a project opportunity.
    """

    title: str
    description: str

    source: str | None = None
    source_url: str | None = None

    client_name: str | None = None

    budget: float | None = None
    currency: str | None = None

    project_type: str | None = None

    skills: list[str] = field(default_factory=list)

    deadline: str | None = None

    score: float | None = None
