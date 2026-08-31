from __future__ import annotations

from services.assessment import AssessmentService


class AssessmentEngine:
    def __init__(self):
        self.service = AssessmentService()

    def run(self, assessment_id: str, responses: dict[str, str]):
        assessment = self.service.get_assessment(assessment_id)
        if assessment is None:
            raise ValueError(f"Assessment {assessment_id} not found.")
        return self.service.score_assessment(assessment, responses)
