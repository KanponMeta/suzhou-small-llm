"""LangGraph RAG state schema definition."""
from typing import TypedDict

from langchain_core.documents import Document


class RAGState(TypedDict):
    """State schema for the RAG graph.

    Fields:
        query: User's question extracted from messages
        documents: Raw retrieved chunks from ChromaDB
        filtered_documents: Chunks that passed relevance grading
        generation: Final generated answer text
        has_relevant_docs: Whether any chunks passed grading
    """
    query: str
    documents: list[Document]
    filtered_documents: list[Document]
    generation: str
    has_relevant_docs: bool
