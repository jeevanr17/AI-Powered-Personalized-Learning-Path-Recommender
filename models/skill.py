from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str
    target_level: int = 0
    description: str = ""


class SkillGapReport(BaseModel):
    required_skills: dict[str, int] = Field(default_factory=dict)
    current_skills: dict[str, int] = Field(default_factory=dict)
    gaps: dict[str, int] = Field(default_factory=dict)
    critical_gaps: list[str] = Field(default_factory=list)
    moderate_gaps: list[str] = Field(default_factory=list)
    low_gaps: list[str] = Field(default_factory=list)
    mastered_skills: list[str] = Field(default_factory=list)
    summary: str = ""
