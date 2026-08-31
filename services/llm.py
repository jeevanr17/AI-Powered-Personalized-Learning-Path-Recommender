from __future__ import annotations

import re
from typing import Any

from config.settings import get_settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


class LLMClient:
    """Minimal LLM abstraction used only for profile extraction and explanations."""

    def __init__(self):
        self.settings = get_settings()
        self.mock_mode = self.settings.mock_mode or not self.settings.llm_api_key
        self.client = None
        if not self.mock_mode and OpenAI is not None:
            try:
                client_kwargs = {"api_key": self.settings.llm_api_key}
                if self.settings.llm_base_url:
                    client_kwargs["base_url"] = self.settings.llm_base_url
                self.client = OpenAI(**client_kwargs)
            except Exception:
                self.mock_mode = True
                self.client = None

    def extract_profile(self, text: str) -> dict[str, Any]:
        if self.mock_mode:
            return {
                "goal": "Machine Learning Engineer",
                "experience_level": "beginner_intermediate",
                "current_skills": {"Python": 3, "Statistics": 2},
                "interests": ["NLP", "deep learning"],
                "weekly_hours": 10,
                "deadline_months": 6,
                "learning_history": [],
                "completed_courses": [],
                "preferred_learning_style": "self_paced",
            }

        if not self.client:
            raise ValueError("LLM client is unavailable.")

        try:
            response = self.client.responses.create(
                model=self.settings.llm_model,
                input=[{"role": "user", "content": f"Return valid JSON for learner profile: {text}"}],
            )
            return response.output_text
        except Exception:
            self.mock_mode = True
            return self.extract_profile(text)

    def explain_recommendation(self, resource: dict[str, Any], profile: dict[str, Any], skill_gap: dict[str, Any]) -> str:
        if self.mock_mode:
            missing = [skill for skill, gap in skill_gap.get("gaps", {}).items() if gap > 0][:2]
            missing_text = ", ".join(missing) if missing else "core ML skills"
            return (
                f"This resource targets {missing_text} and fits your {profile.get('experience_level', 'beginner_intermediate')} experience. "
                f"It aligns with your interest in {', '.join(profile.get('interests', [])) or 'ML'} and matches your weekly study time."
            )

        if not self.client:
            return "A real LLM is not configured; this recommendation uses the deterministic reasoning engine."

        try:
            response = self.client.responses.create(
                model=self.settings.llm_model,
                input=[{"role": "user", "content": f"Explain why this course is recommended: {resource.get('title')}; profile: {profile}; gaps: {skill_gap}"}],
            )
            return response.output_text
        except Exception:
            self.mock_mode = True
            return self.explain_recommendation(resource, profile, skill_gap)

    @staticmethod
    def _roadmap_hours(roadmap: dict[str, Any] | list[dict[str, Any]]) -> float:
        if isinstance(roadmap, dict):
            if roadmap.get("total_hours"):
                return float(roadmap["total_hours"])
            return sum(
                resource.get("estimated_hours", 0)
                for phase in roadmap.get("phases", [])
                for resource in phase.get("resources", [])
            )
        return 0.0

    @staticmethod
    def _next_resource(roadmap: dict[str, Any] | list[dict[str, Any]]) -> str | None:
        if not isinstance(roadmap, dict):
            return None
        for phase in roadmap.get("phases", []):
            for resource in phase.get("resources", []):
                if not resource.get("completed"):
                    return resource.get("title")
        return None

    def answer_question(self, question: str, profile: dict[str, Any], roadmap: dict[str, Any] | list[dict[str, Any]]) -> str:
        if self.mock_mode:
            normalized = question.lower()
            if "stack" in normalized:
                return (
                    "A stack is a last-in, first-out (LIFO) data structure—like a stack of plates. "
                    "Use push to add an item, pop to remove the newest item, and peek to view the newest item."
                )
            if any(term in normalized for term in ("how long", "how many days", "how many weeks", "hrs", "hours")):
                hour_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:hrs?|hours?)", normalized)
                weekly_hours = float(hour_matches[-1]) if hour_matches else float(profile.get("weekly_hours") or 0)
                total_hours = self._roadmap_hours(roadmap)
                if weekly_hours > 0 and total_hours > 0:
                    weeks = total_hours / weekly_hours
                    days = weeks * 7
                    return (
                        f"This roadmap contains about {total_hours:.0f} study hours. At {weekly_hours:g} hours per week, "
                        f"it should take about {weeks:.1f} weeks ({days:.0f} days), assuming a steady pace."
                    )
                return "Add a weekly study time and generate a roadmap so I can estimate the duration."
            if "statistics" in normalized:
                return "Statistics matters because nearly every ML model depends on data distributions, uncertainty, and evaluation metrics."
            if "next" in normalized or "study" in normalized:
                next_resource = self._next_resource(roadmap)
                if next_resource:
                    return f"Your next unfinished roadmap item is **{next_resource}**. Complete it before moving to the next phase."
                return "All current roadmap items are complete. Update your profile or regenerate the roadmap for the next goal."
            return (
                f"Your {profile.get('goal', 'learning')} roadmap is based on your current skills, interests, "
                "available study time, completed courses, assessment results, and feedback. Ask me about a concept, "
                "your next step, or how long the roadmap will take."
            )

        if not self.client:
            return "The assistant is in deterministic fallback mode because no LLM API key is configured."

        try:
            response = self.client.responses.create(
                model=self.settings.llm_model,
                input=[{"role": "user", "content": f"Answer as a coaching tutor using this profile: {profile}; roadmap: {roadmap}; question: {question}"}],
            )
            return response.output_text
        except Exception:
            self.mock_mode = True
            return self.answer_question(question, profile, roadmap)
