from __future__ import annotations

import networkx as nx


class PrerequisiteGraph:
    """Directed acyclic graph describing skill prerequisites."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_default_graph()

    def _build_default_graph(self):
        edges = [
            ("Python", "NumPy"),
            ("Python", "Pandas"),
            ("Python", "Programming Fundamentals"),
            ("Programming Fundamentals", "Machine Learning"),
            ("Statistics", "Machine Learning"),
            ("NumPy", "Data Cleaning"),
            ("Pandas", "Data Cleaning"),
            ("Data Cleaning", "Feature Engineering"),
            ("Machine Learning", "Model Evaluation"),
            ("Model Evaluation", "Deep Learning"),
            ("Deep Learning", "PyTorch"),
            ("PyTorch", "Transformers"),
            ("Machine Learning", "NLP"),
            ("Model Evaluation", "Hyperparameter Tuning"),
            ("Machine Learning", "Feature Engineering"),
            ("Model Deployment", "Docker"),
            ("Docker", "MLOps"),
            ("REST APIs", "Model Deployment"),
            ("Machine Learning", "Model Deployment"),
        ]
        for source, target in edges:
            self.graph.add_edge(source, target)

    def add_edge(self, source: str, target: str):
        self.graph.add_edge(source, target)

    def get_prerequisites(self, skill: str) -> list[str]:
        return list(self.graph.predecessors(skill))

    def is_prerequisite_satisfied(self, skill: str, learner: dict[str, int]) -> bool:
        prereqs = self.get_prerequisites(skill)
        if not prereqs:
            return True

        for prereq in prereqs:
            if learner.get(prereq, 0) >= 2 and self.is_prerequisite_satisfied(prereq, learner):
                return True

        return False

    def get_learning_order(self, skills: list[str]) -> list[str]:
        ordered = []
        for skill in nx.topological_sort(self.graph.subgraph(skills)):
            ordered.append(skill)
        return ordered
