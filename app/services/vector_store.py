"""Deprecated: use src.vectorstore instead."""
from src.vectorstore import get_vectorstore as get_vector_store, add_documents, get_all_document_metadata

__all__ = ["get_vector_store", "add_documents", "get_all_document_metadata"]
