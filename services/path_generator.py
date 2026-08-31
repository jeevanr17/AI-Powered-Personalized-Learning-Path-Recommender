from __future__ import annotations

from models.learning_path import LearningPath, Phase, PathItem


class LearningPathGenerator:
    """Generate a personalized learning roadmap from ranked resources and prerequisites."""

    def _phase_plan_for_goal(self, goal: str) -> list[dict]:
        goal_text = (goal or "Machine Learning Engineer").lower()

        if "data scientist" in goal_text:
            return [
                {
                    "name": "Phase 1 — Data Science Foundations",
                    "objectives": ["Strengthen Python, SQL, and statistics for analysis"],
                    "skills": ["Python", "Statistics", "SQL", "Data Cleaning"],
                    "milestone": "Clean and analyze a dataset from scratch",
                    "assessment": "Data Science Foundations Assessment",
                },
                {
                    "name": "Phase 2 — Data Science Exploratory Analysis",
                    "objectives": ["Explore patterns, relationships, and visual insights"],
                    "skills": ["Data Visualization", "Feature Engineering", "Model Evaluation"],
                    "milestone": "Produce a dashboard and analytical summary",
                    "assessment": "Exploration and modeling assessment",
                },
                {
                    "name": "Phase 3 — Data Science Modeling",
                    "objectives": ["Train supervised and unsupervised models"],
                    "skills": ["Machine Learning", "Supervised Learning", "Unsupervised Learning"],
                    "milestone": "Build and compare multiple models",
                    "assessment": "Machine Learning Fundamentals Assessment",
                },
                {
                    "name": "Phase 4 — Data Science Specialization",
                    "objectives": ["Apply modeling to stakeholder-driven product questions"],
                    "skills": ["NLP", "Deep Learning", "Feature Engineering"],
                    "milestone": "Create a domain-specific data science project",
                    "assessment": "Specialization assessment",
                },
                {
                    "name": "Phase 5 — Data Science Deployment & Communication",
                    "objectives": ["Package findings into a reusable workflow"],
                    "skills": ["Model Deployment", "REST APIs", "Data Visualization"],
                    "milestone": "Share an end-to-end data product and recommendations",
                    "assessment": "Communication and deployment review",
                },
            ]

        if "software engineer" in goal_text or "software engineering" in goal_text or "software developer" in goal_text:
            return [
                {
                    "name": "Phase 1 — Programming Foundations",
                    "objectives": ["Write clear code and use Git effectively"],
                    "skills": ["Programming Fundamentals", "Python", "Git"],
                    "milestone": "Build and version-control a command-line application",
                    "assessment": "Software Engineering Foundations Assessment",
                },
                {
                    "name": "Phase 2 — Problem Solving",
                    "objectives": ["Apply data structures and algorithms to practical problems"],
                    "skills": ["Data Structures", "Algorithms", "Object-Oriented Programming"],
                    "milestone": "Solve and explain a set of algorithmic challenges",
                    "assessment": "Data structures checkpoint",
                },
                {
                    "name": "Phase 3 — Backend Development",
                    "objectives": ["Design databases and build REST APIs"],
                    "skills": ["Databases", "SQL", "REST APIs", "Testing"],
                    "milestone": "Deliver a tested CRUD API",
                    "assessment": "Backend implementation review",
                },
                {
                    "name": "Phase 4 — Delivery and Design",
                    "objectives": ["Deploy reliable services and reason about system trade-offs"],
                    "skills": ["Docker", "CI/CD", "Cloud Fundamentals", "System Design"],
                    "milestone": "Deploy a documented service with a CI pipeline",
                    "assessment": "System design review",
                },
            ]

        return [
            {
                "name": "Phase 1 — FOUNDATIONS",
                "objectives": ["Strengthen Python, statistics, and data basics"],
                "skills": ["Python", "Statistics", "NumPy", "Pandas"],
                "milestone": "Data handling and analysis baseline",
                "assessment": "Foundations checkpoint",
            },
            {
                "name": "Phase 2 — MACHINE LEARNING",
                "objectives": ["Understand supervised learning and evaluation"],
                "skills": ["Machine Learning", "Feature Engineering", "Model Evaluation"],
                "milestone": "Build and evaluate a supervised ML model",
                "assessment": "Machine Learning Fundamentals Assessment",
            },
            {
                "name": "Phase 3 — DEEP LEARNING",
                "objectives": ["Learn neural networks and Python deep learning stacks"],
                "skills": ["Deep Learning", "Neural Networks", "PyTorch"],
                "milestone": "Train a deep learning model",
                "assessment": "Deep Learning Knowledge Check",
            },
            {
                "name": "Phase 4 — SPECIALIZATION",
                "objectives": ["Focus on NLP or computer vision depending on learner interests"],
                "skills": ["NLP", "Transformers", "Computer Vision"],
                "milestone": "Complete a domain-specific project",
                "assessment": "Specialization assessment",
            },
            {
                "name": "Phase 5 — DEPLOYMENT",
                "objectives": ["Expose the model via APIs and containerize services"],
                "skills": ["Model Deployment", "REST APIs", "Docker"],
                "milestone": "Deploy an ML API",
                "assessment": "Deployment readiness",
            },
            {
                "name": "Phase 6 — MLOPS",
                "objectives": ["Track, monitor, and operate ML systems at scale"],
                "skills": ["MLOps", "Experiment Tracking", "Model Monitoring"],
                "milestone": "Review system lifecycle and monitoring strategy",
                "assessment": "MLOps knowledge check",
            },
            {
                "name": "Phase 7 — CAPSTONE",
                "objectives": ["Deliver an end-to-end ML solution and present it"],
                "skills": ["ML System Design", "CI/CD", "Project Delivery"],
                "milestone": "Complete capstone and final presentation",
                "assessment": "Capstone review",
            },
        ]

    def generate(self, ranked_resources: list[dict], learner_profile: dict, skill_gap: dict, feasibility: dict) -> LearningPath:
        phases = self._phase_plan_for_goal(learner_profile.get("goal", "Machine Learning Engineer"))

        path_items: list[PathItem] = []
        for candidate in ranked_resources[:8]:
            resource = candidate.get("resource")
            phase_index = next(
                (
                    index
                    for index, phase in enumerate(phases)
                    if set(resource.get("skills_covered", [])) & set(phase["skills"])
                ),
                len(phases) - 1,
            )
            path_items.append(
                PathItem(
                    resource_id=resource.get("id"),
                    title=resource.get("title"),
                    type=resource.get("type"),
                    difficulty=resource.get("difficulty"),
                    estimated_hours=resource.get("estimated_hours", 0),
                    skills=resource.get("skills_covered", []),
                    score=candidate.get("final_score", 0.0),
                    explanation=f"Recommended to address {', '.join(resource.get('skills_covered', []))} for your goal.",
                    completed=False,
                    phase=phases[phase_index]["name"],
                )
            )

        generated_phases = []
        for phase in phases:
            phase_resources = [item for item in path_items if item.phase == phase["name"]]
            generated_phases.append(
                Phase(
                    name=phase["name"],
                    objectives=phase["objectives"],
                    skills=phase["skills"],
                    resources=phase_resources,
                    milestone=phase["milestone"],
                    assessment=phase["assessment"],
                    completion_status=0.0,
                )
            )

        total_hours = sum(item.estimated_hours for item in path_items)
        return LearningPath(
            title=f"{learner_profile.get('goal', 'Machine Learning Engineer')} roadmap",
            phases=generated_phases,
            total_hours=total_hours,
            feasibility=feasibility,
            recommendations=[candidate for candidate in ranked_resources[:5]],
        )
