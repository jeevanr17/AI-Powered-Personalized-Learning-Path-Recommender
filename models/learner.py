from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LearnerProfile(BaseModel):
    goal: str = ""
    experience_level: str = ""
    current_skills: dict[str, int] = Field(default_factory=dict)
    interests: list[str] = Field(default_factory=list)
    weekly_hours: int = 0
    deadline_months: int = 0
    learning_history: list[str] = Field(default_factory=list)
    completed_courses: list[str] = Field(default_factory=list)
    preferred_learning_style: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LearnerProfile":
        return cls(**payload)
