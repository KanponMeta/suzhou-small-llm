"""DashScope embedding service using text-embedding-v3."""
import os
from langchain_community.embeddings import DashScopeEmbeddings
from app.config import get_settings


def get_embeddings() -> DashScopeEmbeddings:
    """Create a DashScope embedding instance.

    Uses text-embedding-v3 with 1024 dimensions.
    IMPORTANT: Set DASHSCOPE_API_KEY env var before calling.
    The DashScopeEmbeddings class reads DASHSCOPE_API_KEY from
    the environment automatically.
    """
    settings = get_settings()
    # Ensure the env var is set for the SDK
    os.environ.setdefault("DASHSCOPE_API_KEY", settings.dashscope_api_key)

    return DashScopeEmbeddings(
        model=settings.embedding_model_name,
        text_type="document",  # For indexing; use "query" at retrieval time
    )


def get_query_embeddings() -> DashScopeEmbeddings:
    """Create a DashScope embedding instance for query-time use.

    Uses text_type='query' which is REQUIRED for proper asymmetric
    embedding search with DashScope. Using 'document' at query time
    silently degrades retrieval quality.
    """
    settings = get_settings()
    os.environ.setdefault("DASHSCOPE_API_KEY", settings.dashscope_api_key)

    return DashScopeEmbeddings(
        model=settings.embedding_model_name,
        text_type="query",
    )
