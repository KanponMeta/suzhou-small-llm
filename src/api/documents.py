"""Document upload and listing API endpoints."""
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from src.config import get_settings
from src.models.document import (
    DocumentMetadata,
    UploadResponse,
    DocumentListItem,
    DocumentListResponse,
)
from src.services.document_parser import parse_document, get_file_type
from src.services.text_splitter import split_text
from src.vectorstore import add_documents, get_all_document_metadata

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document file for parsing, chunking, and indexing.

    Supported formats: PDF (.pdf), Markdown (.md, .markdown), Plain text (.txt)

    The document will be:
    1. Saved to the upload directory
    2. Parsed to extract text content
    3. Split into chunks using Chinese-aware separators
    4. Embedded via DashScope text-embedding-v3
    5. Stored in ChromaDB with source metadata
    """
    # Validate file type
    file_type = get_file_type(file.filename or "unknown")
    if file_type is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: pdf, md, txt. Got: {file.filename}",
        )

    settings = get_settings()
    doc_id = str(uuid.uuid4())

    # Save uploaded file to disk
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{doc_id}_{file.filename}"

    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        file_size = os.path.getsize(file_path)

        # Parse document
        text = parse_document(str(file_path), file_type)
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Document contains no extractable text content.",
            )

        # Split into chunks
        chunks = split_text(text)
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="Document produced no chunks after splitting.",
            )

        # Embed and store in vector database
        chunk_count = add_documents(
            chunks=chunks,
            doc_id=doc_id,
            filename=file.filename or "unknown",
            file_type=file_type,
        )

        return UploadResponse(
            doc_id=doc_id,
            filename=file.filename or "unknown",
            file_type=file_type,
            chunk_count=chunk_count,
            message=f"Document uploaded and indexed successfully. {chunk_count} chunks created.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}",
        )


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """List all indexed documents with their metadata.

    Returns a list of all documents that have been uploaded and indexed,
    including doc_id, filename, file_type, and chunk_count for each.
    """
    try:
        docs_meta = get_all_document_metadata()

        documents = [
            DocumentListItem(
                doc_id=meta["doc_id"],
                filename=meta["filename"],
                file_type=meta["file_type"],
                file_size=0,
                chunk_count=meta["chunk_count"],
                created_at="",
            )
            for meta in docs_meta
        ]

        return DocumentListResponse(
            total=len(documents),
            documents=documents,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve document list: {str(e)}",
        )
