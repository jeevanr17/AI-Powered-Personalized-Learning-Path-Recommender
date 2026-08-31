from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError

from config.settings import get_settings


class Database:
    """MongoDB persistence for application data."""

    def __init__(self, database_uri: str | None = None, database_name: str | None = None):
        settings = get_settings()
        uri = database_uri or settings.mongodb_uri
        try:
            self.client = MongoClient(
                uri, serverSelectionTimeoutMS=1_000
            )
            self.database = self.client[database_name or settings.mongodb_database]
            self.client.admin.command("ping")
        except Exception:
            import mongomock
            self.client = mongomock.MongoClient()
            self.database = self.client[database_name or settings.mongodb_database]
        self._initialize()

    def _initialize(self) -> None:
        self.database.users.create_index("username", unique=True)
        self.database.users.create_index("email", unique=True, sparse=True)
        self.database.learners.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        self.database.resources.create_index("resource_id", unique=True)
        self.database.learning_paths.create_index("learner_id")
        self.database.learning_paths.create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)])
        self.database.path_items.create_index("learning_path_id")
        self.database.assessment_results.create_index("learner_id")
        self.database.feedback.create_index("learner_id")
        self.database.conversations.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
        self.database.password_reset_tokens.create_index("token_hash", unique=True)
        self.database.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _document(document: dict[str, Any] | None) -> dict[str, Any] | None:
        if document is None:
            return None
        document = dict(document)
        document["id"] = str(document.pop("_id"))
        return document

    def close(self) -> None:
        self.client.close()

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
        return f"pbkdf2_sha256$600000${salt}${digest.hex()}"

    @staticmethod
    def verify_password(stored_password: str, password: str) -> bool:
        """Validate new PBKDF2 hashes and allow legacy accounts to sign in once."""
        if not stored_password.startswith("pbkdf2_sha256$"):
            return hmac.compare_digest(stored_password, password)
        try:
            algorithm, iterations, salt, expected = stored_password.split("$", 3)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
            return algorithm == "pbkdf2_sha256" and hmac.compare_digest(actual, expected)
        except (TypeError, ValueError):
            return False

    def create_user(self, username: str, email: str, password: str) -> str:
        result = self.database.users.insert_one(
            {
                "username": username.strip(), "email": email.strip().lower(),
                "password": self._hash_password(password), "created_at": self._now(),
            }
        )
        return str(result.inserted_id)

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        return self._document(self.database.users.find_one({"username": username.strip()}))

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self._document(self.database.users.find_one({"email": email.strip().lower()}))

    def get_user_by_login(self, username_or_email: str) -> dict[str, Any] | None:
        value = username_or_email.strip()
        return self._document(self.database.users.find_one({"$or": [{"username": value}, {"email": value.lower()}]}))

    def set_user_email(self, user_id: str, email: str) -> None:
        self.database.users.update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"email": email.strip().lower()}}
        )

    def create_password_reset_token(self, email: str) -> str | None:
        user = self.get_user_by_email(email)
        if user is None:
            return None
        token = secrets.token_urlsafe(24)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.database.password_reset_tokens.delete_many({"user_id": user["id"]})
        self.database.password_reset_tokens.insert_one(
            {"user_id": user["id"], "token_hash": token_hash, "expires_at": self._now() + timedelta(minutes=15)}
        )
        return token

    def reset_password(self, token: str, new_password: str) -> bool:
        token_hash = hashlib.sha256(token.strip().encode()).hexdigest()
        reset = self.database.password_reset_tokens.find_one(
            {"token_hash": token_hash, "expires_at": {"$gt": self._now()}}
        )
        if reset is None:
            return False
        self.database.users.update_one(
            {"_id": ObjectId(reset["user_id"])}, {"$set": {"password": self._hash_password(new_password)}}
        )
        self.database.password_reset_tokens.delete_one({"_id": reset["_id"]})
        return True

    def save_learner(self, learner_data: dict[str, Any], user_id: str | None = None) -> str:
        document = {
            "user_id": user_id,
            "goal": learner_data.get("goal"),
            "experience_level": learner_data.get("experience_level"),
            "current_skills": learner_data.get("current_skills", {}),
            "interests": learner_data.get("interests", []),
            "weekly_hours": learner_data.get("weekly_hours"),
            "deadline_months": learner_data.get("deadline_months"),
            "learning_history": learner_data.get("learning_history", []),
            "completed_courses": learner_data.get("completed_courses", []),
            "preferred_learning_style": learner_data.get("preferred_learning_style"),
            "created_at": self._now(),
        }
        return str(self.database.learners.insert_one(document).inserted_id)

    def get_profile_for_user(self, user_id: str) -> dict[str, Any] | None:
        profile = self.database.learners.find_one(
            {"user_id": user_id}, sort=[("created_at", DESCENDING)]
        )
        return self._document(profile)

    def save_user_profile(self, user_id: str, profile: dict[str, Any]) -> str:
        profile_data = {
            "goal": profile.get("goal"),
            "experience_level": profile.get("experience_level"),
            "current_skills": profile.get("current_skills", {}),
            "interests": profile.get("interests", []),
            "weekly_hours": profile.get("weekly_hours"),
            "deadline_months": profile.get("deadline_months"),
            "learning_history": profile.get("learning_history", []),
            "completed_courses": profile.get("completed_courses", []),
            "preferred_learning_style": profile.get("preferred_learning_style"),
            "updated_at": self._now(),
        }
        existing = self.database.learners.find_one({"user_id": user_id})
        if existing:
            self.database.learners.update_one({"_id": existing["_id"]}, {"$set": profile_data})
            return str(existing["_id"])
        return self.save_learner(profile_data, user_id=user_id)

    def save_resources(self, resources: list[dict[str, Any]]) -> None:
        for resource in resources:
            document = dict(resource)
            document["resource_id"] = document.pop("id")
            self.database.resources.replace_one(
                {"resource_id": document["resource_id"]}, document, upsert=True
            )

    def get_resources(self) -> list[dict[str, Any]]:
        resources = []
        for resource in self.database.resources.find():
            resource = self._document(resource)
            resource["id"] = resource.pop("resource_id")
            resources.append(resource)
        return resources

    def save_path(self, learner_id: str, title: str, total_hours: int, feasibility: dict[str, Any]) -> str:
        result = self.database.learning_paths.insert_one(
            {
                "learner_id": learner_id,
                "title": title,
                "total_hours": total_hours,
                "feasibility": feasibility,
                "created_at": self._now(),
            }
        )
        return str(result.inserted_id)

    def save_path_items(self, path_id: str, items: list[dict[str, Any]]) -> None:
        documents = [
            {
                "learning_path_id": path_id,
                "resource_id": item.get("resource_id"),
                "title": item.get("title"),
                "type": item.get("type"),
                "difficulty": item.get("difficulty"),
                "estimated_hours": item.get("estimated_hours"),
                "skills": item.get("skills", []),
                "score": item.get("score"),
                "explanation": item.get("explanation"),
                "completed": bool(item.get("completed", False)),
                "phase": item.get("phase"),
            }
            for item in items
        ]
        if documents:
            self.database.path_items.insert_many(documents)

    def save_assessment_result(
        self, learner_id: str, assessment_id: str, overall_score: float,
        skill_scores: dict[str, Any], responses: dict[str, Any],
    ) -> None:
        self.database.assessment_results.insert_one(
            {
                "learner_id": learner_id,
                "assessment_id": assessment_id,
                "overall_score": overall_score,
                "skill_scores": skill_scores,
                "response_data": responses,
                "taken_at": self._now(),
            }
        )

    def save_feedback(self, learner_id: str, question: str, answer: str) -> None:
        self.database.feedback.insert_one(
            {"learner_id": learner_id, "question": question, "answer": answer, "created_at": self._now()}
        )

    def get_feedback_for_user(self, user_id: str) -> list[dict[str, Any]]:
        return [
            self._document(item)
            for item in self.database.feedback.find({"learner_id": user_id}).sort("created_at", DESCENDING)
        ]

    def save_learning_path(self, user_id: str, path: dict[str, Any]) -> str:
        """Store a full roadmap so progress survives browser and app restarts."""
        result = self.database.learning_paths.insert_one(
            {"user_id": user_id, "path": path, "created_at": self._now(), "updated_at": self._now()}
        )
        return str(result.inserted_id)

    def get_latest_learning_path(self, user_id: str) -> dict[str, Any] | None:
        document = self.database.learning_paths.find_one(
            {"user_id": user_id}, sort=[("updated_at", DESCENDING)]
        )
        return self._document(document)

    def update_learning_path(self, path_id: str, path: dict[str, Any]) -> None:
        from bson import ObjectId

        self.database.learning_paths.update_one(
            {"_id": ObjectId(path_id)}, {"$set": {"path": path, "updated_at": self._now()}}
        )

    def save_conversation_message(self, user_id: str, role: str, content: str) -> None:
        self.database.conversations.insert_one(
            {"user_id": user_id, "role": role, "content": content, "created_at": self._now()}
        )

    def get_conversation(self, user_id: str, limit: int = 30) -> list[dict[str, Any]]:
        messages = list(
            self.database.conversations.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return [self._document(item) for item in reversed(messages)]
