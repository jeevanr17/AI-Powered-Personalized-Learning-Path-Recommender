import json
from typing import Any

from data import assessments as assessment_data
from models.assessment import Assessment, AssessmentQuestion


PHASE_QUESTION_BANK = {
    "Programming Fundamentals": ("What is a function primarily used for?", ["To reuse a named block of code", "To store a database", "To deploy an API", "To create a Git branch"], "A", "Functions organize reusable behavior."),
    "Git": ("Which Git command records staged changes in the local repository?", ["git commit", "git clone", "git pull", "git status"], "A", "git commit creates a local commit from staged changes."),
    "Data Structures": ("Which data structure follows last-in, first-out order?", ["Queue", "Stack", "Hash map", "Tree"], "B", "A stack removes the most recently added item first."),
    "Algorithms": ("What does Big-O notation describe?", ["Program color", "Resource growth as input size grows", "A Git workflow", "Database schema"], "B", "Big-O describes how time or space requirements grow with input size."),
    "Object-Oriented Programming": ("What is encapsulation?", ["Hiding internal state behind a defined interface", "Sorting a list", "Deploying a container", "Writing SQL"], "A", "Encapsulation keeps implementation details behind an object's public behavior."),
    "Testing": ("What is the main purpose of a unit test?", ["Test one small behavior in isolation", "Deploy to production", "Replace code review", "Create a database"], "A", "Unit tests check focused behavior independently."),
    "SQL": ("Which SQL clause filters rows returned by a query?", ["WHERE", "ORDER BY", "GROUP BY", "JOIN"], "A", "WHERE selects rows that meet a condition."),
    "Databases": ("What is a database index mainly used for?", ["To speed up data retrieval", "To remove all duplicate data", "To replace tables", "To write API routes"], "A", "Indexes can speed up lookups at the cost of additional storage and write work."),
    "REST APIs": ("Which HTTP method conventionally creates a new resource?", ["GET", "POST", "DELETE", "PATCH"], "B", "POST is conventionally used to create a resource."),
    "Docker": ("What does a Docker image provide?", ["A reusable package for running an application", "A database query", "A Git branch", "A test assertion"], "A", "Images package an application and its dependencies."),
    "CI/CD": ("What is continuous integration intended to do?", ["Frequently merge and automatically validate changes", "Delete old code", "Replace testing", "Avoid deployments"], "A", "CI integrates changes often and validates them with automated checks."),
    "Cloud Fundamentals": ("What is a key benefit of cloud infrastructure?", ["Resources can scale on demand", "It eliminates all security work", "It removes the need for code", "It guarantees zero cost"], "A", "Cloud services can adjust capacity as demand changes."),
    "System Design": ("Why is caching commonly used in a service?", ["To reduce repeated work and improve response time", "To replace a database permanently", "To remove authentication", "To avoid testing"], "A", "Caching can reduce latency and load for frequently requested data."),
    "Machine Learning": ("What is supervised learning used for?", ["Predict a target from labeled examples", "Cluster only unlabeled data", "Deploy an API", "Create Docker images"], "A", "Supervised learning learns from labeled input-output examples."),
    "Statistics": ("What does the mean represent?", ["Arithmetic average", "Largest value", "Middle label", "Number of columns"], "A", "The mean is the arithmetic average of numeric values."),
    "Python": ("Which Python collection stores key-value pairs?", ["list", "tuple", "dict", "set"], "C", "A dictionary maps keys to values."),
}


class AssessmentService:
    """Deterministic assessment engine with skill mapping and scoring."""

    def __init__(self):
        self.assessments = self._load_assessments()

    def _load_assessments(self) -> dict[str, Assessment]:
        data = assessment_data.load_assessments()
        return {item["id"]: Assessment.from_dict(item) for item in data}

    def get_assessment(self, assessment_id: str) -> Assessment | None:
        return self.assessments.get(assessment_id)

    def get_phase_assessment(self, phase_number: int, phase_name: str, skills: list[str]) -> Assessment:
        """Build a focused assessment from the topics taught in one roadmap phase."""
        questions = []
        for skill in skills:
            item = PHASE_QUESTION_BANK.get(skill)
            if item is None:
                continue
            question, options, answer, explanation = item
            questions.append(
                AssessmentQuestion(
                    id=f"phase-{phase_number}-{len(questions) + 1}", skill=skill,
                    question=question, options=options, answer=answer, explanation=explanation,
                )
            )
        if not questions:
            questions.append(
                AssessmentQuestion(
                    id=f"phase-{phase_number}-1", skill="Phase completion",
                    question=f"Have you completed the learning objective for {phase_name}?",
                    options=["Yes, I can demonstrate the milestone", "Not yet"], answer="A",
                    explanation="Use the phase milestone as evidence before moving to the next phase.",
                )
            )
        return Assessment(
            id=f"phase-{phase_number}-{phase_name.lower().replace(' ', '-')}",
            title=f"{phase_name} Assessment",
            description="This checkpoint covers the skills and resources in this roadmap phase.",
            skills=skills,
            questions=questions[:4],
        )

    def score_assessment(self, assessment: Assessment, responses: dict[str, str]) -> dict[str, Any]:
        correct = 0
        skill_scores: dict[str, float] = {}
        per_skill = {}
        question_results = []
        for question in assessment.questions:
            expected_answer = question.answer
            if len(expected_answer) == 1 and "A" <= expected_answer.upper() <= "Z":
                option_index = ord(expected_answer.upper()) - ord("A")
                if option_index < len(question.options):
                    expected_answer = question.options[option_index]
            is_correct = responses.get(question.id) in {question.answer, expected_answer}
            if is_correct:
                correct += 1
            skill = question.skill
            per_skill.setdefault(skill, {"correct": 0, "total": 0})
            per_skill[skill]["total"] += 1
            if is_correct:
                per_skill[skill]["correct"] += 1
            question_results.append(
                {
                    "question": question.question,
                    "selected_answer": responses.get(question.id),
                    "correct_answer": expected_answer,
                    "is_correct": is_correct,
                    "explanation": question.explanation,
                }
            )

        for skill, counts in per_skill.items():
            ratio = (counts["correct"] / counts["total"]) * 100 if counts["total"] else 0.0
            skill_scores[skill] = round(ratio, 2)

        overall_score = round((correct / max(1, len(assessment.questions))) * 100, 2)
        return {
            "overall_score": overall_score,
            "skill_scores": skill_scores,
            "correct_answers": correct,
            "total_questions": len(assessment.questions),
            "question_results": question_results,
        }

    def update_skills(self, learner_skills: dict[str, int], assessment_result: dict[str, Any]) -> dict[str, int]:
        updated = dict(learner_skills)
        for skill, score in assessment_result.get("skill_scores", {}).items():
            current = updated.get(skill, 0)
            new_level = max(0, min(5, int(round(score / 20))))
            updated[skill] = max(current, new_level)
        return updated
