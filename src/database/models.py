from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Project:
    """
    Represents a project opportunity.
    """

    title: str
    description: str

    source: Optional[str] = None
    source_url: Optional[str] = None

    client_name: Optional[str] = None

    budget: Optional[float] = None
    currency: Optional[str] = None

    project_type: Optional[str] = None

    skills: list[str] = field(default_factory=list)

    deadline: Optional[str] = None

    score: Optional[float] = None