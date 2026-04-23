# app/settings.py
from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "sports-tracker"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql://postgres:postgres@127.0.0.1:5432/training"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Ejemplo en .env:
    # CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
    CORS_ORIGINS: list[str] = Field(default_factory=list)

    # Celery / Redis (Celery espera strings tipo URL)
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    @field_validator("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND")
    @classmethod
    def _validate_redis_url(cls, v: str) -> str:
        # Simple y suficiente: evita que alguien meta http:// por error
        if not (v.startswith("redis://") or v.startswith("rediss://")):
            raise ValueError("Must start with redis:// or rediss://")
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _cors_origins_from_env(cls, v: Any) -> list[str]:
        # Permite que venga como JSON string desde env o ya como lista
        # Pydantic normalmente ya lo hace bien, pero esto evita casos raros.
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        return v


settings = Settings()
