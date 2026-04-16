"""RAG graph node functions implementing retrieve-grade-generate flow."""
from langchain_qwq import ChatQwen
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document

from src.rag.state import RAGState
from src.rag.prompts import (
    GRADER_SYSTEM_PROMPT,
    GRADER_HUMAN_PROMPT,
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_HUMAN_PROMPT,
    FALLBACK_RESPONSE,
)
from src.vectorstore import get_vectorstore
from src.config import settings


def retrieve(state: RAGState) -> dict:
    """Retrieve documents from vector store based on query.

    Args:
        state: Current RAG state containing the query.

    Returns:
        Dict with 'documents' key containing retrieved Document objects.
    """
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": settings.RETRIEVAL_TOP_K}
    )
    docs = retriever.invoke(state["query"])
    return {"documents": docs}


def grade_documents(state: RAGState) -> dict:
    """Grade retrieved documents for relevance to the query.

    Uses ChatQwen to determine if each document is relevant to the query.
    Returns only documents that pass the relevance check.

    Args:
        state: Current RAG state with query and retrieved documents.

    Returns:
        Dict with 'filtered_documents' and 'has_relevant_docs' keys.
    """
    llm = ChatQwen(model="qwen-plus", temperature=0)

    filtered_docs: list[Document] = []

    for doc in state.get("documents", []):
        # Skip documents with empty content
        if not doc.page_content or not doc.page_content.strip():
            continue

        # Format the grader prompt
        formatted_prompt = GRADER_HUMAN_PROMPT.format(
            query=state.get("query", ""),
            document_content=doc.page_content
        )

        # Send to LLM for grading
        messages = [
            SystemMessage(content=GRADER_SYSTEM_PROMPT),
            HumanMessage(content=formatted_prompt)
        ]
        response = llm.invoke(messages)

        # Check if document is relevant (response contains "yes")
        if "yes" in response.content.lower():
            filtered_docs.append(doc)

    return {
        "filtered_documents": filtered_docs,
        "has_relevant_docs": len(filtered_docs) > 0
    }


def generate(state: RAGState) -> dict:
    """Generate answer based on filtered documents.

    If no relevant documents are found, returns a fallback response.
    Otherwise, generates an answer using the retrieved context.

    Args:
        state: Current RAG state with query and filtered documents.

    Returns:
        Dict with 'generation' key containing the generated answer.
    """
    # Return fallback if no relevant documents
    if not state["has_relevant_docs"]:
        return {"generation": FALLBACK_RESPONSE}

    # Concatenate document contents for context
    context = "\n\n".join(
        doc.page_content for doc in state["filtered_documents"]
    )

    # Format generator prompt with context
    formatted_system = GENERATOR_SYSTEM_PROMPT.format(context=context)
    formatted_human = GENERATOR_HUMAN_PROMPT.format(query=state["query"])

    # Initialize LLM for generation
    llm = ChatQwen(model="qwen-plus", temperature=0.3)

    # Generate answer
    messages = [
        SystemMessage(content=formatted_system),
        HumanMessage(content=formatted_human)
    ]
    response = llm.invoke(messages)

    return {"generation": response.content}
