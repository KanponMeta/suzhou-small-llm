"""ChromaDB vector store service for document chunk storage and retrieval."""
import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument
from src.config import get_settings
from src.embeddings import get_embeddings


_vectorstore: Chroma | None = None


def get_vectorstore() -> Chroma:
    """Get or create the ChromaDB vector store instance.

    Connects to the ChromaDB HTTP server defined in settings.
    Uses langchain-chroma integration for clean retriever interface.
    """
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    settings = get_settings()

    chroma_client = chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
    )

    _vectorstore = Chroma(
        client=chroma_client,
        collection_name=settings.COLLECTION_NAME,
        embedding_function=get_embeddings(),
    )

    return _vectorstore


def add_documents(
    chunks: list[str],
    doc_id: str,
    filename: str,
    file_type: str,
) -> int:
    """Add document chunks to the vector store with metadata.

    DashScope embedding has a batch limit of 10 items per API call.
    This function handles batching automatically.

    Args:
        chunks: List of text chunks from the splitter.
        doc_id: Unique document identifier.
        filename: Original filename.
        file_type: File type (pdf, md, txt).

    Returns:
        Number of chunks successfully added.
    """
    store = get_vectorstore()
    BATCH_SIZE = 10  # DashScope embedding batch limit

    lc_documents = []
    for i, chunk in enumerate(chunks):
        lc_documents.append(
            LCDocument(
                page_content=chunk,
                metadata={
                    "doc_id": doc_id,
                    "filename": filename,
                    "file_type": file_type,
                    "chunk_index": i,
                },
            )
        )

    # Add in batches of 10 to respect DashScope API limit
    for batch_start in range(0, len(lc_documents), BATCH_SIZE):
        batch = lc_documents[batch_start : batch_start + BATCH_SIZE]
        store.add_documents(batch)

    return len(lc_documents)


def get_all_document_metadata() -> list[dict]:
    """Retrieve unique document metadata from the vector store.

    Queries ChromaDB for all stored chunks, extracts unique doc_ids,
    and returns deduplicated document metadata.

    Returns:
        List of dicts with keys: doc_id, filename, file_type, chunk_count.
    """
    store = get_vectorstore()

    # Get all documents from the collection
    collection = store._collection
    results = collection.get(include=["metadatas"])

    if not results or not results["metadatas"]:
        return []

    # Deduplicate by doc_id
    docs: dict[str, dict] = {}
    for meta in results["metadatas"]:
        doc_id = meta.get("doc_id", "unknown")
        if doc_id not in docs:
            docs[doc_id] = {
                "doc_id": doc_id,
                "filename": meta.get("filename", "unknown"),
                "file_type": meta.get("file_type", "unknown"),
                "chunk_count": 0,
            }
        docs[doc_id]["chunk_count"] += 1

    return list(docs.values())
