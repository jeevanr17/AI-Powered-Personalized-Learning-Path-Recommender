class AdaptiveEngine:
    """Adjust the roadmap and remediations based on assessment weaknesses."""

    def build_remediation(self, learner_skills: dict[str, int], weak_skills: list[str]) -> dict:
        skills = []
        for skill in weak_skills:
            score = learner_skills.get(skill, 0)
            skills.append({"skill": skill, "score": score, "priority": "high" if score < 3 else "medium"})

        return {
            "remediation_needed": bool(weak_skills),
            "skills": weak_skills,
            "strategy": "Insert targeted remediation modules before advanced topics.",
            "recommendations": skills,
        }
