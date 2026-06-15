from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Known placeholder/default secrets that must never be used in production.
_WEAK_SECRETS = {
    "changeme", "change-me", "secret", "secret_key", "dev",
    "change-me-in-prod-0123456789abcdef", "test-secret-key-for-testing-only-0123456789",
}


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

    # LLM — multi-agent router: a cheap model triages every turn; complex/multimodal
    # turns escalate to the heavy model.
    llm_model: str = "claude-haiku-4-5"          # default / simple turns
    llm_model_heavy: str = "claude-sonnet-4-6"   # complex multi-step + multimodal turns
    llm_router_model: str = "claude-haiku-4-5"   # the cheap classifier
    model_router_enabled: bool = True            # toggle the Haiku→Sonnet router
    rerank_enabled: bool = True                  # re-rank KB retrieval (cross-encoder/feature)
    visual_search_enabled: bool = True           # CLIP visual arm in product search (no-op without torch)
    llm_max_tokens: int = 400
    # Catalog scale + product imagery
    catalog_target: int | None = None            # None = curated ~1.2k; e.g. 10000 for the big catalog
    image_provider: Literal["placeholder", "unsplash", "pexels"] = "placeholder"
    use_placeholder_images: bool = True           # render category SVG tiles (vs committed licensed photos)
    unsplash_access_key: SecretStr | None = None
    pexels_api_key: SecretStr | None = None
    # Voice: optional speech-to-text provider for /media/transcribe
    stt_provider: Literal["", "openai", "groq"] = ""
    stt_api_key: SecretStr | None = None
    stt_model: str = ""  # blank = per-provider default (groq: whisper-large-v3)
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

    @model_validator(mode="after")
    def _validate_production_secret(self):
        """Refuse to boot in production with a weak or default SECRET_KEY."""
        if self.environment == "production":
            sk = self.secret_key.get_secret_value()
            if len(sk) < 32 or sk.lower() in _WEAK_SECRETS:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters and not a default/placeholder "
                    "value when ENVIRONMENT=production."
                )
        return self

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

    @property
    def cookie_samesite(self) -> str:
        # In production (HTTPS) use SameSite=None so cookies survive when the app
        # is embedded in an iframe (e.g. a Hugging Face Space). None REQUIRES Secure,
        # which cookie_secure provides. Dev/test stay on Lax (http can't use None).
        return "none" if self.cookie_secure else "lax"


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
