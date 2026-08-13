from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class Project(BaseModel):
    title: str = Field(min_length=1, description="Title of the project")

    description: str = Field(min_length=1, description="Description of the project")

    source: str = Field(min_length=1, description="Source of the project")

    source_url: HttpUrl = Field(min_length=1, description="URL of the project source")

    client_name: str | None = Field(None)

    budget: float | None = Field(None, ge=0)

    currency: str | None = Field(None)

    project_type: str | None = Field(None)

    skills: list[str] = Field(default_factory=list)

    project_start_date: datetime | None = Field(None)

    project_end_date: datetime | None = Field(None)

    score: float | None = Field(default=None, ge=0, le=100)
