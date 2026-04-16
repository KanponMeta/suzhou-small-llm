"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Allow extra fields from .env
    )

    # API
    API_KEY: str = "test-api-key"

    # DashScope
    DASHSCOPE_API_KEY: str = ""
    GENERATION_MODEL: str = "qwen-plus"
    EMBEDDING_MODEL: str = "text-embedding-v3"

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    COLLECTION_NAME: str = "enterprise-knowledge"
    IS_PERSISTENT: bool = True

    # Retrieval
    RETRIEVAL_TOP_K: int = 4


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
