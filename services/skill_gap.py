from __future__ import annotations

from models.skill import SkillGapReport


class SkillGapAnalyzer:
    """Calculate gap between current and required skills for a target role."""

    def analyze(self, current_skills: dict[str, int], required_skills: dict[str, int]) -> dict:
        gaps: dict[str, int] = {}
        critical: list[str] = []
        moderate: list[str] = []
        low: list[str] = []
        mastered: list[str] = []

        all_skills = sorted(set(current_skills) | set(required_skills))
        for skill in all_skills:
            required_level = required_skills.get(skill, 0)
            current_level = current_skills.get(skill, 0)
            gap = max(required_level - current_level, 0)
            gaps[skill] = gap

            if gap >= 3:
                critical.append(skill)
            elif gap == 2:
                moderate.append(skill)
            elif gap == 1:
                low.append(skill)
            elif required_level > 0 and current_level >= required_level:
                mastered.append(skill)

        report = SkillGapReport(
            required_skills=required_skills,
            current_skills=current_skills,
            gaps=gaps,
            critical_gaps=critical,
            moderate_gaps=moderate,
            low_gaps=low,
            mastered_skills=mastered,
            summary=f"Critical gaps: {len(critical)}; moderate: {len(moderate)}; low: {len(low)}",
        )
        return report.model_dump()
