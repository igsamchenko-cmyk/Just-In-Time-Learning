import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Генератор інтерактивного навчання"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./learning_mvp.db")
    session_secret: str = os.getenv("SESSION_SECRET", "dev-session-secret")
    ai_provider: str = os.getenv("AI_PROVIDER", "mock").lower()
    ai_fallback_to_mock: bool = os.getenv("AI_FALLBACK_TO_MOCK", "true").lower() == "true"
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret: str | None = os.getenv("GOOGLE_CLIENT_SECRET")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    claude_api_key: str | None = os.getenv("CLAUDE_API_KEY")


settings = Settings()
