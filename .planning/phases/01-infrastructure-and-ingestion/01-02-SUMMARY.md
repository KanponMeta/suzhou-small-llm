---
phase: "01"
plan: "01-02"
subsystem: "Infrastructure"
tags: ["document-ingestion", "embeddings", "chromadb", "dashscope", "fastapi"]
dependency_graph:
  requires: ["app/config.py", "app/main.py"]
  provides: ["app/models/document.py", "app/services/document_parser.py", "app/services/text_splitter.py", "app/services/embeddings.py", "app/services/vector_store.py", "app/api/documents.py"]
  affects: ["02-01", "02-02"]
tech_stack:
  added:
    - pymupdf: "1.27.2.2"
    - langchain-text-splitters: "1.1.1"
    - langchain-community: "0.4.1"
    - langchain-chroma: "latest"
    - dashscope: "1.25.17"
  patterns:
    - "Chinese-aware text splitting with punctuation separators"
    - "DashScope batch limit handling (10 items per call)"
    - "Asymmetric embeddings: text_type=document for indexing, text_type=query for retrieval"
    - "LangChain Document metadata with doc_id tracking"
key_files:
  created:
    - app/models/document.py
    - app/services/document_parser.py
    - app/services/text_splitter.py
    - app/services/embeddings.py
    - app/services/vector_store.py
    - app/api/documents.py
  modified:
    - app/main.py
      change: "Added documents router import and app.include_router()"
decisions:
  - "Used PyMuPDF (fitz) for PDF parsing with Chinese layout preservation"
  - "Chinese-aware separators prioritized: 。、！？；， before English equivalents"
  - "DashScope embedding batch limit of 10 enforced via BATCH_SIZE constant in add_documents()"
  - "Separate get_embeddings() and get_query_embeddings() to handle asymmetric text_type"
  - "Document chunks stored with metadata: doc_id, filename, file_type, chunk_index"
metrics:
  duration_minutes: 18
  completed_date: "2026-04-16"
---

# Phase 01 Plan 01-02: Document Ingestion Pipeline Summary

## One-Liner
Built complete document ingestion pipeline: parse PDF/Markdown/TXT, split with Chinese-aware chunking, embed via DashScope text-embedding-v3, and store in ChromaDB with source metadata.

## What Was Built

### Document Models (app/models/document.py)
- **DocumentMetadata**: Pydantic model for ingested document metadata with auto-generated doc_id
- **UploadResponse**: Response schema for successful upload with chunk_count
- **DocumentListItem** / **DocumentListResponse**: Schemas for document listing endpoints

### Document Parsing (app/services/document_parser.py)
- **parse_pdf()**: Extracts text using PyMuPDF (fitz), handles multi-page documents
- **parse_markdown()** / **parse_text()**: UTF-8 text file readers
- **get_file_type()**: Extension-based file type detection (supports .pdf, .md, .markdown, .txt)
- **parse_document()**: Unified entry point with validation

### Text Splitting (app/services/text_splitter.py)
- **get_text_splitter()**: Creates RecursiveCharacterTextSplitter with Chinese-aware separators
- **split_text()**: Main entry point, default chunk_size=500, chunk_overlap=100
- **Separators prioritized**: `\n\n` > `\n` > `。` > `！` > `？` > `；` > `，` > `. ` > ` ` > `""`

### Embedding Service (app/services/embeddings.py)
- **get_embeddings()**: For indexing, uses `text_type="document"`
- **get_query_embeddings()**: For retrieval, uses `text_type="query"`
- **Model**: text-embedding-v3 (1024 dimensions per CLAUDE.md)
- Reads DASHSCOPE_API_KEY from environment via pydantic Settings

### Vector Store (app/services/vector_store.py)
- **get_vector_store()**: Singleton pattern, connects to ChromaDB HTTP client
- **add_documents()**: Batches chunks in groups of 10 (DashScope limit)
- **get_all_document_metadata()**: Deduplicates chunks by doc_id for listing
- Metadata stored: `doc_id`, `filename`, `file_type`, `chunk_index`

### Upload Endpoint (app/api/documents.py)
- **POST /documents/upload**: Accepts UploadFile, validates extension
- Flow: save to disk -> parse -> split -> embed -> store -> return doc_id + chunk_count
- Error handling: 400 for unsupported types/empty content, 500 for processing errors
- Streaming file save via shutil.copyfileobj (memory efficient)

## Key Implementation Details

| Aspect | Implementation |
|--------|----------------|
| PDF Parsing | PyMuPDF 1.27.2.2 (fitz) |
| Chunking | RecursiveCharacterTextSplitter with Chinese separators |
| Chunk defaults | 500 chars size, 100 chars overlap |
| Embedding model | text-embedding-v3 via DashScopeEmbeddings |
| Embedding dimension | 1024 |
| Batch limit | 10 chunks per API call (DashScope constraint) |
| Vector store | ChromaDB via langchain-chroma |
| Metadata tracking | doc_id, filename, file_type, chunk_index |

## Threat Model Compliance

| Threat ID | Status | Mitigation Applied |
|-----------|--------|-------------------|
| T-02-01 | Mitigated | File type validation via get_file_type(); UUID prefix prevents path traversal |
| T-02-02 | Mitigated | FastAPI UploadFile streams to disk; bounded Docker volume |
| T-02-03 | Mitigated | API key via pydantic Settings; never logged; .env excluded from git |
| T-02-04 | Accepted | PyMuPDF actively maintained; enterprise internal with trusted sources |
| T-02-05 | Mitigated | Generic error messages; no stack traces in HTTP responses |

## Verification Results

All acceptance criteria verified:
- [x] app/models/document.py contains all 4 Pydantic model classes
- [x] app/services/document_parser.py contains parse_pdf, parse_markdown, parse_text, parse_document
- [x] app/services/text_splitter.py uses langchain_text_splitters with Chinese separators
- [x] app/services/embeddings.py uses DashScopeEmbeddings with text_type="document"
- [x] app/services/embeddings.py has get_query_embeddings() with text_type="query"
- [x] app/services/vector_store.py batches embeddings with BATCH_SIZE = 10
- [x] app/services/vector_store.py stores metadata with doc_id
- [x] app/api/documents.py exposes POST /documents/upload endpoint
- [x] app/main.py includes documents router
- [x] No banned packages (openai, langchain-openai, ChatTongyi, langchain-dashscope)

## Deviations from Plan

None - plan executed exactly as written.

## Commits

- df8a3dd: Task 1 - Document models, parser, and Chinese-aware text splitter
- d39adce: Task 2 - Embedding service, vector store, and upload endpoint

## Self-Check: PASSED

- All created files exist: VERIFIED
- All Python syntax validates: VERIFIED
- No banned packages imported: VERIFIED
- Batch limit (10) implemented: VERIFIED
- Chinese separators present: VERIFIED
- Router wired into main.py: VERIFIED
