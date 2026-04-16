"""Tests for RAG graph compilation and structure."""
import pytest


def test_graph_compiles():
    """Graph compiles without error and is invokable."""
    from src.rag.graph import build_rag_graph
    graph = build_rag_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_graph_has_expected_nodes():
    """Graph contains retrieve, grade_documents, generate nodes."""
    from src.rag.graph import build_rag_graph
    graph = build_rag_graph()
    # LangGraph compiled graphs expose nodes via .get_graph().nodes
    graph_def = graph.get_graph()
    node_ids = [n.id for n in graph_def.nodes if n.id not in ("__start__", "__end__")]
    assert "retrieve" in node_ids
    assert "grade_documents" in node_ids
    assert "generate" in node_ids
    assert len(node_ids) == 3


def test_rag_state_schema():
    """RAGState has all required fields."""
    from src.rag.state import RAGState
    annotations = RAGState.__annotations__
    assert "query" in annotations
    assert "documents" in annotations
    assert "filtered_documents" in annotations
    assert "generation" in annotations
    assert "has_relevant_docs" in annotations


def test_fallback_response_is_chinese():
    """Fallback response is a non-empty Chinese string."""
    from src.rag.prompts import FALLBACK_RESPONSE
    assert len(FALLBACK_RESPONSE) > 10
    assert "抱歉" in FALLBACK_RESPONSE
