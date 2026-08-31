class ExplanationEngine:
    """Generate explanations for each recommended resource based on learner context."""

    def explain(self, resource: dict, learner_profile: dict, skill_gap: dict) -> str:
        missing = [skill for skill, gap in skill_gap.get("gaps", {}).items() if gap > 0][:3]
        interests = learner_profile.get("interests", [])
        interest_text = ", ".join(interests) if interests else "your chosen domain"
        missing_text = ", ".join(missing) if missing else "core ML concepts"
        return (
            f"This resource was recommended because it targets {missing_text} and aligns with your interest in {interest_text}. "
            f"It is suitable for a learner with {learner_profile.get('experience_level', 'beginner_intermediate')} experience and "
            f"fits within the available time budget of {learner_profile.get('weekly_hours', 10)} hours per week."
        )
