"""Compiled LangGraph RAG StateGraph."""
from langgraph.graph import StateGraph, START, END

from src.rag.state import RAGState
from src.rag.nodes import retrieve, grade_documents, generate


def build_rag_graph() -> StateGraph:
    """Build the RAG graph: retrieve -> grade_documents -> generate.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    graph = StateGraph(RAGState)

    # Add nodes
    graph.add_node("retrieve", retrieve)
    graph.add_node("grade_documents", grade_documents)
    graph.add_node("generate", generate)

    # Define edges: linear flow retrieve -> grade -> generate
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "grade_documents")
    graph.add_edge("grade_documents", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# Module-level compiled graph instance for import by FastAPI endpoint
rag_graph = build_rag_graph()
