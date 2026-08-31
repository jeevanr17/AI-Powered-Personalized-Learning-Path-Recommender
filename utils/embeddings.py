import hashlib
import json
from typing import Any


def simple_embedding(text: str) -> list[float]:
    text = text.lower().strip()
    if not text:
        return [0.0] * 8
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    values: list[float] = []
    for idx in range(0, 64, 8):
        chunk = digest[idx:idx + 8]
        total = 0
        for char in chunk:
            total += ord(char)
        values.append((total % 1000) / 1000.0)
    return values


def embedding_payload(resource: dict[str, Any]) -> dict[str, Any]:
    text = " ".join([
        str(resource.get("title", "")),
        str(resource.get("description", "")),
        " ".join(str(skill) for skill in resource.get("skills_covered", [])),
        " ".join(str(outcome) for outcome in resource.get("learning_outcomes", [])),
        str(resource.get("domain", "")),
    ])
    return {
        "id": resource.get("id"),
        "embedding": simple_embedding(text),
        "metadata": {
            "resource_id": resource.get("id"),
            "type": resource.get("type"),
            "difficulty": resource.get("difficulty"),
            "skills": ", ".join(resource.get("skills_covered", [])),
            "estimated_hours": resource.get("estimated_hours"),
            "domain": resource.get("domain"),
            "title": resource.get("title"),
        },
        "document": text,
    }
