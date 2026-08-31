from __future__ import annotations

from config.settings import get_settings


class RecommenderEngine:
    """Hybrid ranking engine combining semantic relevance, gap coverage, and feasibility."""

    def __init__(self):
        self.weights = get_settings().recommendation_weights

    def score_resource(self, resource: dict, missing_skills: dict[str, int], current_skills: dict[str, int], learner_interests: dict[str, int], weekly_hours: int, adaptation: dict | None = None):
        resource_skills = set(resource.get("skills_covered", []))
        gap_coverage = self._coverage_score(resource_skills, missing_skills)
        semantic = self._semantic_relevance(resource, missing_skills, learner_interests)
        prerequisite = self._prerequisite_fit(resource, current_skills)
        difficulty = self._difficulty_fit(resource, current_skills)
        time_fit = self._time_fit(resource.get("estimated_hours", 0), weekly_hours)
        interest = self._interest_fit(resource, learner_interests)

        final_score = (
            self.weights["semantic"] * semantic
            + self.weights["skill_gap"] * gap_coverage
            + self.weights["prerequisite"] * prerequisite
            + self.weights["difficulty"] * difficulty
            + self.weights["time"] * time_fit
            + self.weights["interest"] * interest
        )

        adaptation_bonus = self._adaptation_bonus(resource, adaptation or {})
        return {
            "final_score": max(0.0, min(1.0, final_score + adaptation_bonus)),
            "semantic_relevance": semantic,
            "skill_gap_coverage": gap_coverage,
            "prerequisite_fit": prerequisite,
            "difficulty_fit": difficulty,
            "time_fit": time_fit,
            "interest_fit": interest,
        }

    def _adaptation_bonus(self, resource: dict, adaptation: dict) -> float:
        """Apply a small, explainable adjustment from stored learner feedback."""
        bonus = 0.0
        difficulty = resource.get("difficulty", "").lower()
        resource_type = resource.get("type", "").lower()
        if adaptation.get("prefer_easier"):
            bonus += 0.15 if difficulty == "beginner" else -0.08 if difficulty == "advanced" else 0.0
        if adaptation.get("prefer_practical") and resource_type == "project":
            bonus += 0.12
        if adaptation.get("prefer_shorter"):
            bonus += max(-0.10, 0.10 - resource.get("estimated_hours", 0) / 200)
        return bonus

    def _coverage_score(self, resource_skills: set[str], missing_skills: dict[str, int]) -> float:
        if not missing_skills:
            return 0.0
        matched = sum(1 for skill in resource_skills if missing_skills.get(skill, 0) > 0)
        return min(1.0, matched / max(1, len(missing_skills)))

    def _semantic_relevance(self, resource: dict, missing_skills: dict[str, int], learner_interests: dict[str, int]) -> float:
        relevance = 0.0
        resource_text = " ".join([resource.get("title", ""), resource.get("description", ""), " ".join(resource.get("skills_covered", [])), " ".join(resource.get("learning_outcomes", []))]).lower()
        for skill in missing_skills:
            if skill.lower() in resource_text:
                relevance += 0.2
        for interest in learner_interests:
            if interest.lower() in resource_text:
                relevance += 0.3
        return min(1.0, relevance)

    def _prerequisite_fit(self, resource: dict, current_skills: dict[str, int]) -> float:
        if not resource.get("prerequisites"):
            return 1.0
        satisfied = sum(1 for prereq in resource.get("prerequisites", []) if current_skills.get(prereq, 0) >= 2)
        return satisfied / len(resource.get("prerequisites", []))

    def _difficulty_fit(self, resource: dict, current_skills: dict[str, int]) -> float:
        avg = sum(current_skills.values()) / max(1, len(current_skills)) if current_skills else 0.0
        difficulty_map = {"beginner": 1.0, "intermediate": 0.75, "advanced": 0.5}
        goal = difficulty_map.get(resource.get("difficulty", "beginner"), 0.5)
        return min(1.0, max(0.0, 1.0 - abs(avg - goal)))

    def _time_fit(self, estimated_hours: int, weekly_hours: int) -> float:
        if weekly_hours <= 0:
            return 0.5
        return min(1.0, max(0.0, weekly_hours / max(1, estimated_hours)))

    def _interest_fit(self, resource: dict, learner_interests: dict[str, int]) -> float:
        if not learner_interests:
            return 1.0
        tags = {tag.lower() for tag in resource.get("interest_tags", [])}
        matching = sum(1 for interest in learner_interests if interest.lower() in tags)
        return min(1.0, matching / max(1, len(learner_interests)))

    def rank(self, candidates: list[dict], missing_skills: dict[str, int], current_skills: dict[str, int], learner_interests: dict[str, int], weekly_hours: int, adaptation: dict | None = None):
        ranked = []
        for candidate in candidates:
            resource = candidate.get("resource")
            score = self.score_resource(resource, missing_skills, current_skills, learner_interests, weekly_hours, adaptation)
            ranked.append({**score, "resource": resource, "resource_id": resource.get("id")})
        ranked.sort(key=lambda item: item["final_score"], reverse=True)
        return ranked
