---
phase: quick
plan: 260416-pmt
subsystem: api
tags: [fastapi, consolidation, config, embeddings, vectorstore, docker]
dependency_graph:
  requires: []
  provides: [unified-fastapi-app, unified-config, docker-entrypoint]
  affects: [src/main.py, src/config.py, src/embeddings.py, src/vectorstore.py, app/api/health.py, app/api/documents.py, Dockerfile]
tech_stack:
  added: []
  patterns: [thin-re-export, singleton-vectorstore, asymmetric-embeddings]
key_files:
  created: []
  modified:
    - src/config.py
    - src/embeddings.py
    - src/vectorstore.py
    - src/main.py
    - app/api/health.py
    - app/api/documents.py
    - app/services/vector_store.py
    - app/services/embeddings.py
    - Dockerfile
decisions:
  - "Unified collection name to enterprise_kb (matching Phase 1 ingestion data already stored under this name)"
  - "CHROMA_HOST default changed to chromadb (Docker Compose service name) — local overrides via .env"
  - "app/services/*.py kept as thin re-exports rather than deleted to avoid breaking any future callers"
metrics:
  duration: ~10 minutes
  completed_date: "2026-04-16"
  tasks_completed: 3
  files_modified: 9
---

# Quick Task 260416-pmt: Consolidate app/ and src/ into single FastAPI service

**One-liner:** Unified two separate FastAPI apps into a single service at src/main.py by merging configs, replacing embeddings with text_type-aware DashScopeTextEmbeddings, switching vectorstore to HttpClient for Docker, rewiring app/ imports to src/, and updating the Dockerfile entrypoint.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Unify config, embeddings, vectorstore in src/ | dfe360f | src/config.py, src/embeddings.py, src/vectorstore.py |
| 2 | Rewire app/ to src/ and merge routers into src/main.py | e3bc4a2 | app/api/health.py, app/api/documents.py, app/services/*, src/main.py |
| 3 | Update Dockerfile entrypoint to src.main:app | d7f9400 | Dockerfile |

## What Changed

### src/config.py
- Added `EMBEDDING_DIMENSION=1024`, `UPLOAD_DIR="/app/uploads"`, `API_HOST="0.0.0.0"`, `API_PORT=8000`
- Changed `CHROMA_HOST` default from `"localhost"` to `"chromadb"` (Docker Compose service name)
- Changed `COLLECTION_NAME` default from `"enterprise-knowledge"` to `"enterprise_kb"` (matches Phase 1 data)

### src/embeddings.py
- Replaced `DashScopeEmbeddings` (langchain-community) with custom `DashScopeTextEmbeddings`
- Supports asymmetric embeddings: `text_type="document"` for indexing, `text_type="query"` for retrieval
- Added `get_query_embeddings()` factory function

### src/vectorstore.py
- Replaced local `persist_directory="./chroma_data"` with `chromadb.HttpClient` pointing at Docker ChromaDB container
- Added `add_documents()` with DashScope batch limit (10 items per call)
- Added `get_all_document_metadata()` for document listing

### src/main.py
- Added `health_router` (GET /health) and `documents_router` (POST /documents/upload, GET /documents)
- Added root `/` endpoint
- All five endpoints now served from single FastAPI app

### app/ modules
- `app/api/health.py`: imports from `src.config`, uses UPPERCASE field names
- `app/api/documents.py`: imports from `src.config` and `src.vectorstore`, uses `UPLOAD_DIR`
- `app/services/vector_store.py`: thin re-export from `src.vectorstore`
- `app/services/embeddings.py`: thin re-export from `src.embeddings`

### Dockerfile
- CMD changed from `app.main:app` to `src.main:app`

## Verification Results

```
All routes registered: ['/', '/dataset/generate', '/docs', '/docs/oauth2-redirect',
  '/documents', '/documents/upload', '/health', '/openapi.json', '/redoc', '/v1/chat/completions']
Config: chromadb enterprise_kb /app/uploads
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all endpoints are fully wired. No placeholder data flows to UI rendering.

## Self-Check: PASSED

- src/config.py: present and verified (CHROMA_HOST=chromadb, COLLECTION_NAME=enterprise_kb)
- src/embeddings.py: present and verified (text_type=document/query)
- src/vectorstore.py: present and verified (get_vectorstore, add_documents, get_all_document_metadata exported)
- src/main.py: all 6 routes registered
- Dockerfile: src.main:app confirmed
- Commits: dfe360f, e3bc4a2, d7f9400 all present
