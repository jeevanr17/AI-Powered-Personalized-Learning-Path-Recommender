from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PathItem(BaseModel):
    resource_id: str
    title: str
    type: str
    difficulty: str
    estimated_hours: int
    skills: list[str] = Field(default_factory=list)
    score: float = 0.0
    explanation: str = ""
    completed: bool = False
    phase: str = ""


class Phase(BaseModel):
    name: str
    objectives: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    resources: list[PathItem] = Field(default_factory=list)
    milestone: str = ""
    assessment: str = ""
    completion_status: float = 0.0


class LearningPath(BaseModel):
    title: str
    phases: list[Phase] = Field(default_factory=list)
    total_hours: int = 0
    feasibility: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
