from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AssessmentQuestion(BaseModel):
    id: str
    skill: str
    question: str
    options: list[str]
    answer: str
    explanation: str = ""


class Assessment(BaseModel):
    id: str
    title: str
    description: str = ""
    skills: list[str] = Field(default_factory=list)
    questions: list[AssessmentQuestion] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Assessment":
        return cls(**payload)
