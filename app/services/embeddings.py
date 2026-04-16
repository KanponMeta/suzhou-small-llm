"""DashScope embedding service using text-embedding-v3.

langchain_community.DashScopeEmbeddings (0.4.1) does not expose text_type,
so we call the DashScope SDK directly and implement the LangChain Embeddings
interface ourselves.
"""
from typing import List
import dashscope
from langchain_core.embeddings import Embeddings
from app.config import get_settings


class DashScopeTextEmbeddings(Embeddings):
    """LangChain-compatible embeddings using DashScope text-embedding-v3.

    Supports asymmetric embeddings via text_type:
    - "document" for indexing chunks
    - "query"    for retrieval queries
    """

    def __init__(self, text_type: str = "document"):
        self._text_type = text_type

    def _embed(self, texts: List[str]) -> List[List[float]]:
        settings = get_settings()
        resp = dashscope.TextEmbedding.call(
            model=settings.embedding_model_name,
            input=texts,
            text_type=self._text_type,
            api_key=settings.dashscope_api_key,
            dimension=settings.embedding_dimension,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"DashScope embedding failed: {resp.status_code} {resp.message}"
            )
        embeddings = sorted(resp.output["embeddings"], key=lambda x: x["text_index"])
        return [e["embedding"] for e in embeddings]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]


def get_embeddings() -> DashScopeTextEmbeddings:
    """Embedding instance for indexing (text_type=document)."""
    return DashScopeTextEmbeddings(text_type="document")


def get_query_embeddings() -> DashScopeTextEmbeddings:
    """Embedding instance for retrieval (text_type=query)."""
    return DashScopeTextEmbeddings(text_type="query")
