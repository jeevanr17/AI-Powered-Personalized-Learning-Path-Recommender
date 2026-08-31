import pytest

from services.profiler import LearnerProfiler
from services.skill_gap import SkillGapAnalyzer
from services.prerequisite import PrerequisiteGraph
from services.recommender import RecommenderEngine
from services.feasibility import FeasibilityEngine
from services.assessment import AssessmentService
from services.adaptive_engine import AdaptiveEngine
from services.path_generator import LearningPathGenerator
from database.db import Database
from services.llm import LLMClient


def test_profile_from_natural_language():
    profiler = LearnerProfiler()
    text = (
        "I know basic Python and some statistics. "
        "I want to become a Machine Learning Engineer within 6 months. "
        "I can study 10 hours per week. "
        "I am interested in NLP and deep learning."
    )
    profile = profiler.from_natural_language(text)
    assert profile.goal == "Machine Learning Engineer"
    assert profile.weekly_hours == 10
    assert profile.deadline_months == 6
    assert profile.current_skills["Python"] >= 1
    assert "NLP" in profile.interests


def test_password_hashing_does_not_store_plaintext():
    stored = Database._hash_password("safe-password")
    assert stored != "safe-password"
    assert Database.verify_password(stored, "safe-password") is True
    assert Database.verify_password(stored, "incorrect") is False


def test_skill_gap_calculation():
    analyzer = SkillGapAnalyzer()
    report = analyzer.analyze({"Python": 2, "Statistics": 2}, {"Python": 4, "Statistics": 4})
    assert report["gaps"]["Python"] == 2
    assert report["gaps"]["Statistics"] == 2


def test_prerequisite_logic():
    graph = PrerequisiteGraph()
    graph.add_edge("Python", "NumPy")
    graph.add_edge("NumPy", "Machine Learning")
    learner = {"Python": 4, "NumPy": 3, "Machine Learning": 1}
    assert graph.is_prerequisite_satisfied("Machine Learning", learner) is True
    assert graph.is_prerequisite_satisfied("NumPy", learner) is True


def test_recommendation_uses_gap_and_scores():
    engine = RecommenderEngine()
    resource = {
        "id": "r1",
        "title": "ML Fundamentals",
        "skills_covered": ["Machine Learning", "Model Evaluation"],
        "type": "course",
        "difficulty": "intermediate",
        "estimated_hours": 12,
        "domain": "ml",
        "description": "Learn ML fundamentals and evaluation.",
        "learning_outcomes": ["Model evaluation", "feature engineering"],
        "prerequisites": ["Python", "Statistics"],
        "url": "https://example.com/ml-fundamentals",
        "interest_tags": ["deep learning", "NLP"],
    }
    score = engine.score_resource(resource, {"Machine Learning": 1, "Model Evaluation": 1}, {"Python": 3, "Statistics": 2}, {"NLP": 2}, 10)
    assert 0 <= score["final_score"] <= 1
    assert score["skill_gap_coverage"] >= 0


def test_recommendation_adapts_to_feedback_preferences():
    engine = RecommenderEngine()
    base = {
        "id": "r2",
        "title": "Starter Project",
        "skills_covered": ["Python"],
        "type": "project",
        "difficulty": "beginner",
        "estimated_hours": 4,
        "description": "Build a practical Python project.",
        "learning_outcomes": ["Python"],
        "prerequisites": [],
        "interest_tags": [],
    }
    normal = engine.score_resource(base, {"Python": 1}, {}, {}, 5)
    adapted = engine.score_resource(
        base, {"Python": 1}, {}, {}, 5,
        {"prefer_easier": True, "prefer_practical": True, "prefer_shorter": True},
    )
    assert adapted["final_score"] > normal["final_score"]


def test_feasibility_calculation():
    engine = FeasibilityEngine()
    result = engine.calculate_feasibility(260, 200)
    assert result["utilization"] == pytest.approx(0.7692307692)
    assert result["feasible"] is True


def test_assessment_scoring_updates_skills():
    service = AssessmentService()
    assessment = service.get_assessment("ml-foundations")
    assert assessment is not None
    score = service.score_assessment(assessment, {"q1": "B", "q2": "A", "q3": "B", "q4": "C"})
    assert 0 <= score["overall_score"] <= 100
    assert "Machine Learning" in score["skill_scores"]


def test_assessment_accepts_streamlit_option_text():
    service = AssessmentService()
    assessment = service.get_assessment("software-engineering-foundations")
    assert assessment is not None
    responses = {question.id: question.options[ord(question.answer) - ord("A")] for question in assessment.questions}
    result = service.score_assessment(assessment, responses)
    assert result["overall_score"] == 100


def test_adaptive_engine_recommends_remediation():
    engine = AdaptiveEngine()
    learner = {"Machine Learning": 3, "Deep Learning": 2, "Model Evaluation": 2}
    weak_skills = ["Model Evaluation"]
    plan = engine.build_remediation(learner, weak_skills)
    assert plan["remediation_needed"] is True
    assert "Model Evaluation" in plan["skills"]


def test_learning_path_generator_is_role_aware():
    generator = LearningPathGenerator()
    path = generator.generate([], {"goal": "Data Scientist"}, {"gaps": {"Python": 1}}, {"feasible": True})
    assert any("Data Science" in phase.name for phase in path.phases)


def test_software_engineering_profile_and_path_are_role_aware():
    profile = LearnerProfiler().from_natural_language(
        "I want to work in software engineering and can study 8 hours per week for 6 months."
    )
    assert profile.goal == "Software Engineer"
    path = LearningPathGenerator().generate([], profile.model_dump(), {"gaps": {}}, {"feasible": True})
    assert any("Backend Development" in phase.name for phase in path.phases)


def test_resources_are_assigned_to_a_matching_roadmap_phase():
    generator = LearningPathGenerator()
    candidates = [
        {"resource": {"id": "dsa", "title": "DSA", "type": "course", "difficulty": "intermediate", "estimated_hours": 8, "skills_covered": ["Data Structures", "Algorithms"]}, "final_score": 1.0},
        {"resource": {"id": "api", "title": "API", "type": "course", "difficulty": "intermediate", "estimated_hours": 8, "skills_covered": ["REST APIs", "SQL"]}, "final_score": 1.0},
    ]
    path = generator.generate(candidates, {"goal": "Software Engineer"}, {"gaps": {}}, {"feasible": True})
    by_name = {phase.name: phase for phase in path.phases}
    assert by_name["Phase 2 — Problem Solving"].resources[0].title == "DSA"
    assert by_name["Phase 3 — Backend Development"].resources[0].title == "API"


def test_mock_assistant_answers_stack_and_roadmap_duration():
    assistant = LLMClient()
    assistant.mock_mode = True
    profile = {"goal": "Software Engineer", "weekly_hours": 10}
    roadmap = {"total_hours": 150, "phases": []}
    assert "last-in, first-out" in assistant.answer_question("How does a stack work?", profile, roadmap)
    assert "10.0 weeks" in assistant.answer_question("How many days at 15 hours per week?", profile, roadmap)


def test_phase_assessment_uses_the_phase_skills():
    service = AssessmentService()
    assessment = service.get_phase_assessment(2, "Problem Solving", ["Data Structures", "Algorithms"])
    assert assessment.title == "Problem Solving Assessment"
    assert {question.skill for question in assessment.questions} == {"Data Structures", "Algorithms"}
    responses = {question.id: question.options[ord(question.answer) - ord("A")] for question in assessment.questions}
    assert service.score_assessment(assessment, responses)["overall_score"] == 100
