from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required — app will refuse to start without this
    anthropic_api_key: SecretStr
    secret_key: SecretStr

    # Database
    database_url: str = f"sqlite:///{BASE_DIR / 'cutdry.db'}"

    # Auth
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # CORS — comma-separated origins
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Environment
    environment: Literal["development", "production", "test"] = "development"

    # Admin seed credentials (required for seed script)
    admin_email: str = "admin@cutdry.example.com"
    admin_password: SecretStr = SecretStr("changeme")

    # Rate limits
    rate_limit_storage: str = "memory://"
    chat_rate_limit: str = "20/minute"
    auth_rate_limit: str = "10/minute"

    # LLM
    llm_model: str = "claude-haiku-4-5"
    llm_max_tokens: int = 400
    llm_temperature: float = 0.0
    max_tokens_per_conversation: int = 50_000
    max_messages_per_conversation: int = 100

    # Moderation toggle
    enable_moderation: bool = False

    # Embeddings
    embedding_provider: str = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    rag_top_k: int = 12
    kb_top_k: int = 4
    rrf_k: int = 60

    # Stripe
    stripe_secret_key: SecretStr = SecretStr("")
    stripe_publishable_key: str = ""
    stripe_webhook_secret: SecretStr = SecretStr("")
    stripe_currency: str = "cad"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.environment == "development"

    @property
    def cookie_secure(self) -> bool:
        # Secure cookies only over HTTPS (production). Dev/test use http.
        return self.environment == "production"


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
