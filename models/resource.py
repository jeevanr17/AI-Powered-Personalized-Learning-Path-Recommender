from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Resource(BaseModel):
    id: str
    title: str
    type: str
    description: str
    skills_covered: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    difficulty: str
    estimated_hours: int = 0
    domain: str = "ml"
    learning_outcomes: list[str] = Field(default_factory=list)
    url: str = ""
    interest_tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Resource":
        return cls(**payload)
