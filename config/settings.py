import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

load_dotenv()


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    llm_api_key: str = (
        os.getenv("LLM_API_KEY")
        or os.getenv("GROK_API_KEY")
        or os.getenv("OPENAI_API_KEY", "")
    )
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_base_url: str = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    mock_mode: bool = str(os.getenv("MOCK_MODE", "true")).lower() == "true"
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "learning_recommender")
    chroma_path: str = os.getenv("CHROMA_PATH", "./storage/chroma")
    email_mode: str = os.getenv("EMAIL_MODE", "console").lower()
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "465"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_sender: str = os.getenv("SMTP_SENDER", "")
    recommendation_weights: dict[str, float] = {
        "semantic": 0.35,
        "skill_gap": 0.25,
        "prerequisite": 0.15,
        "difficulty": 0.10,
        "time": 0.10,
        "interest": 0.05,
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
