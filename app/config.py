from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # DashScope
    dashscope_api_key: str = ""

    # LLM Models
    llm_model_name: str = "qwen-plus"
    embedding_model_name: str = "text-embedding-v3"
    embedding_dimension: int = 1024

    # ChromaDB
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    chroma_collection_name: str = "enterprise_kb"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Upload
    upload_dir: str = "/app/uploads"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
