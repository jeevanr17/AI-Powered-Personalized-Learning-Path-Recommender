from __future__ import annotations

import json
from pathlib import Path

from config.settings import get_settings
from utils.embeddings import embedding_payload
from utils.helpers import load_json_file


class ResourceRetrieval:
    """Simple Chroma-compatible retrieval layer with a deterministic local fallback."""

    def __init__(self, data_path: str | Path | None = None):
        self.settings = get_settings()
        self.data_path = Path(data_path or "data/resources.json")
        self.resources = self._load_resources()
        self._index = []
        self._build_index()

    def _load_resources(self):
        data = load_json_file(self.data_path)
        return data if isinstance(data, list) else []

    def _build_index(self):
        for resource in self.resources:
            self._index.append(embedding_payload(resource))

    def query(self, learner_goal: str, missing_skills: list[str], interests: list[str], experience: str, limit: int = 10):
        combined = " ".join([
            learner_goal,
            " ".join(missing_skills),
            " ".join(interests),
            experience,
        ]).lower()

        scored = []
        for item in self._index:
            text = item["document"].lower()
            score = 0
            for token in combined.split():
                if token in text:
                    score += 1
            for skill in missing_skills:
                if skill.lower() in text:
                    score += 2
            for interest in interests:
                if interest.lower() in text:
                    score += 1
            scored.append({"resource_id": item["id"], "score": score, "meta": item["metadata"]})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def get_by_id(self, resource_id: str):
        for resource in self.resources:
            if resource.get("id") == resource_id:
                return resource
        return None
