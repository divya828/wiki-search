from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    anthropic_api_key: str
    database_url: str
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
