from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class DocumentMetadata(BaseModel):
    """Metadata for an ingested document."""
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str  # "pdf", "md", "txt"
    file_size: int  # bytes
    chunk_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class UploadResponse(BaseModel):
    """Response after successful document upload."""
    doc_id: str
    filename: str
    file_type: str
    chunk_count: int
    message: str


class DocumentListItem(BaseModel):
    """Single document in the list response."""
    doc_id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    created_at: str


class DocumentListResponse(BaseModel):
    """Response for GET /documents."""
    total: int
    documents: list[DocumentListItem]
