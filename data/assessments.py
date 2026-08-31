import json
from pathlib import Path


def load_assessments():
    file_path = Path(__file__).with_name("assessments.json")
    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
