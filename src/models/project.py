from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl

class Project(BaseModel):
    title: str = Field(min_length=1, 
                       description="Title of the project")

    description: str = Field(min_length=1,
                             description="Description of the project")

    source: str = Field(min_length=1,
                        description="Source of the project")

    source_url: HttpUrl = Field(min_length=1,
                                description="URL of the project source")

    client_name: Optional[str] = Field(None)

    budget: Optional[float] = Field(None, 
                                    ge=0)

    currency: Optional[str] = Field(None)

    project_type: Optional[str] = Field(None)

    skills: list[str] = Field(default_factory=list)

    project_start_date: Optional[datetime] = Field(None)

    project_end_date: Optional[datetime] = Field(None)

    score: Optional[float] = Field(default=None,
                                   ge=0,
                                   le=100)