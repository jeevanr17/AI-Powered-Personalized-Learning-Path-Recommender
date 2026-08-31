import json
import re
from typing import Any

from models.learner import LearnerProfile


class LearnerProfiler:
    """Create a structured learner profile from natural language input."""

    def from_natural_language(self, text: str) -> LearnerProfile:
        normalized = text.strip()
        if not normalized:
            raise ValueError("Natural language input is required.")

        goal = self._extract_goal(normalized)
        weekly_hours = self._extract_hours(normalized)
        deadline_months = self._extract_deadline(normalized)
        skills = self._extract_current_skills(normalized)
        interests = self._extract_interests(normalized)

        return LearnerProfile(
            goal=goal,
            experience_level=self._extract_experience(normalized),
            current_skills=skills,
            interests=interests,
            weekly_hours=weekly_hours,
            deadline_months=deadline_months,
            learning_history=[],
            completed_courses=[],
            preferred_learning_style="self_paced",
        )

    def _extract_goal(self, text: str) -> str:
        if "machine learning engineer" in text.lower():
            return "Machine Learning Engineer"
        if "data scientist" in text.lower():
            return "Data Scientist"
        if "software engineer" in text.lower() or "software engineering" in text.lower() or "software developer" in text.lower():
            return "Software Engineer"
        if "ai engineer" in text.lower():
            return "AI Engineer"
        return ""

    def _extract_experience(self, text: str) -> str:
        lower = text.lower()
        if "advanced" in lower or "expert" in lower:
            return "advanced"
        if "intermediate" in lower or "some" in lower or "basic" in lower:
            return "beginner_intermediate"
        return "beginner"

    def _extract_hours(self, text: str) -> int:
        match = re.search(r"(\d+)\s*hours?\s*(?:per\s*week|a\s*week|weekly)", text.lower())
        if match:
            return int(match.group(1))
        return 10

    def _extract_deadline(self, text: str) -> int:
        match = re.search(r"(\d+)\s*months?", text.lower())
        if match:
            return int(match.group(1))
        return 6

    def _extract_current_skills(self, text: str) -> dict[str, int]:
        skills: dict[str, int] = {}
        if "python" in text.lower():
            skills["Python"] = 3
        if "statistics" in text.lower():
            skills["Statistics"] = 2
        if "pandas" in text.lower():
            skills["Pandas"] = 2
        if "numpy" in text.lower():
            skills["NumPy"] = 2
        return skills

    def _extract_interests(self, text: str) -> list[str]:
        interests: list[str] = []
        lower = text.lower()
        if "nlp" in lower:
            interests.append("NLP")
        if "deep learning" in lower:
            interests.append("deep learning")
        if "computer vision" in lower:
            interests.append("computer vision")
        return interests

    def to_dict(self, profile: LearnerProfile) -> dict[str, Any]:
        return json.loads(profile.model_dump_json())
