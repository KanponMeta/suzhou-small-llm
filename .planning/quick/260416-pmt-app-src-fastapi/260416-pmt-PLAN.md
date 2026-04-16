---
phase: quick
plan: 260416-pmt
type: execute
wave: 1
depends_on: []
files_modified:
  - src/config.py
  - src/embeddings.py
  - src/vectorstore.py
  - src/main.py
  - app/api/health.py
  - app/api/documents.py
  - app/services/vector_store.py
  - app/services/embeddings.py
  - Dockerfile
autonomous: true
must_haves:
  truths:
    - "GET /health returns service status with chromadb and dashscope checks"
    - "POST /documents/upload accepts file and indexes into ChromaDB"
    - "GET /documents lists all indexed documents"
    - "POST /v1/chat/completions returns RAG-powered response (existing functionality preserved)"
    - "POST /dataset/generate returns evaluation dataset ZIP (existing functionality preserved)"
    - "Single uvicorn process serves all five endpoints"
  artifacts:
    - path: "src/main.py"
      provides: "Unified FastAPI app with all routers"
    - path: "src/config.py"
      provides: "Canonical config with all settings from both app/ and src/"
    - path: "src/embeddings.py"
      provides: "Unified DashScope embeddings with text_type support"
    - path: "src/vectorstore.py"
      provides: "Unified ChromaDB vectorstore using HttpClient for Docker"
    - path: "Dockerfile"
      provides: "Updated CMD pointing to src.main:app"
  key_links:
    - from: "app/api/health.py"
      to: "src/config.py"
      via: "import get_settings"
      pattern: "from src.config import"
    - from: "app/api/documents.py"
      to: "src/config.py"
      via: "import get_settings"
      pattern: "from src.config import"
    - from: "app/services/vector_store.py"
      to: "src/embeddings.py"
      via: "import get_embeddings"
      pattern: "from src.embeddings import"
    - from: "src/main.py"
      to: "all routers"
      via: "include_router"
      pattern: "app.include_router"
---

<objective>
Consolidate the two separate FastAPI applications (app/ for Phase 1 ingestion, src/ for Phase 2/3 RAG+dataset) into a single unified service running from src/main.py.

Purpose: Currently the Dockerfile starts `app.main:app` which only exposes Phase 1 routes (health, documents). The Phase 2/3 routes (chat, dataset) live in `src/main.py` and are not served. Both apps need to run together as one service.

Output: A single FastAPI app at `src/main.py` serving all endpoints: GET /health, POST /documents/upload, GET /documents, POST /v1/chat/completions, POST /dataset/generate.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/main.py
@app/main.py
@src/config.py
@app/config.py
@src/embeddings.py
@app/services/embeddings.py
@src/vectorstore.py
@app/services/vector_store.py
@app/api/health.py
@app/api/documents.py
@src/api/chat.py
@src/api/routes/dataset.py
@app/models/document.py
@app/services/document_parser.py
@app/services/text_splitter.py
@Dockerfile
@docker-compose.yml

<interfaces>
<!-- Current state: two config systems, two embeddings, two vectorstores -->

From src/config.py (Phase 2/3 config - UPPERCASE fields):
```python
class Settings(BaseSettings):
    API_KEY: str = "test-api-key"
    DASHSCOPE_API_KEY: str = ""
    GENERATION_MODEL: str = "qwen-plus"
    EMBEDDING_MODEL: str = "text-embedding-v3"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    COLLECTION_NAME: str = "enterprise-knowledge"
    IS_PERSISTENT: bool = True
    RETRIEVAL_TOP_K: int = 4

settings = get_settings()  # module-level singleton
```

From app/config.py (Phase 1 config - lowercase fields):
```python
class Settings(BaseSettings):
    dashscope_api_key: str = ""
    llm_model_name: str = "qwen-plus"
    embedding_model_name: str = "text-embedding-v3"
    embedding_dimension: int = 1024
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    chroma_collection_name: str = "enterprise_kb"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    upload_dir: str = "/app/uploads"
```

Key differences to resolve:
- CHROMA_HOST default: "localhost" (src) vs "chromadb" (app) -- "chromadb" is correct for Docker
- COLLECTION_NAME: "enterprise-knowledge" (src) vs "enterprise_kb" (app) -- must unify to ONE name
- app/ has: embedding_dimension, upload_dir, api_host, api_port -- missing from src/
- app/services/embeddings.py: custom DashScopeTextEmbeddings with text_type (document/query) -- more correct
- src/embeddings.py: plain DashScopeEmbeddings from langchain-community -- simpler but no text_type
- app/services/vector_store.py: HttpClient to ChromaDB container -- correct for Docker
- src/vectorstore.py: local persistent directory -- only works without Docker ChromaDB service
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Unify config and shared services (config, embeddings, vectorstore)</name>
  <files>src/config.py, src/embeddings.py, src/vectorstore.py</files>
  <action>
**src/config.py** -- Merge all fields from app/config.py into src/config.py. Keep src/config.py's UPPERCASE naming convention (it is already used by src/api/chat.py, src/api/routes/dataset.py, src/rag/* modules). Add the missing fields:

```python
# Add these fields to the existing Settings class:
EMBEDDING_DIMENSION: int = 1024
UPLOAD_DIR: str = "/app/uploads"
API_HOST: str = "0.0.0.0"
API_PORT: int = 8000
```

CRITICAL changes to existing defaults:
- Change `CHROMA_HOST` default from `"localhost"` to `"chromadb"` (the Docker Compose service name -- this is the correct default for production; developers running locally can override via .env)
- Change `COLLECTION_NAME` default from `"enterprise-knowledge"` to `"enterprise_kb"` (must match the collection name already used by Phase 1 ingestion, since documents are already indexed under this name)

Keep `case_sensitive=True` in model_config. Keep the module-level `settings = get_settings()` export.

**src/embeddings.py** -- Replace the current `DashScopeEmbeddings` from langchain-community with the custom `DashScopeTextEmbeddings` class from `app/services/embeddings.py`. This class calls the DashScope SDK directly and supports asymmetric embeddings via `text_type` parameter ("document" for indexing, "query" for retrieval). This is important for embedding quality.

Change the imports to use `src.config` instead of `app.config`:
```python
from src.config import get_settings
```

Keep both factory functions:
- `get_embeddings()` -- returns instance with text_type="document" (for indexing)
- `get_query_embeddings()` -- returns instance with text_type="query" (for retrieval)

Use settings fields: `settings.EMBEDDING_MODEL` (not `settings.embedding_model_name`), `settings.DASHSCOPE_API_KEY` (not `settings.dashscope_api_key`), `settings.EMBEDDING_DIMENSION` (new field).

**src/vectorstore.py** -- Replace the current local-persistent-directory implementation with the HttpClient-based implementation from `app/services/vector_store.py`. The current src version uses `persist_directory="./chroma_data"` which does not work with Docker Compose (ChromaDB runs as a separate container).

Change imports to use `src.config` and `src.embeddings`:
```python
from src.config import get_settings
from src.embeddings import get_embeddings
```

Port over the singleton pattern, `add_documents()` function (with DashScope batch limit of 10), and `get_all_document_metadata()` function from `app/services/vector_store.py`. Also keep the existing `get_vectorstore()` function name (used by src/api/routes/dataset.py and src/rag/graph.py).

Use settings fields: `settings.CHROMA_HOST` (not `settings.chroma_host`), `settings.CHROMA_PORT`, `settings.COLLECTION_NAME` (not `settings.chroma_collection_name`).

Make sure `get_vectorstore()` returns the singleton Chroma instance (same as `get_vector_store()` did in app/), and also export the `add_documents()` and `get_all_document_metadata()` functions that the documents router needs.
  </action>
  <verify>
    <automated>cd /home/developer/.kanpon/code/suzhou-small-llm && python -c "from src.config import settings, get_settings; s = get_settings(); assert s.CHROMA_HOST == 'chromadb'; assert s.COLLECTION_NAME == 'enterprise_kb'; assert s.EMBEDDING_DIMENSION == 1024; assert s.UPLOAD_DIR == '/app/uploads'; print('Config OK')" && python -c "from src.embeddings import get_embeddings, get_query_embeddings; e = get_embeddings(); assert e._text_type == 'document'; q = get_query_embeddings(); assert q._text_type == 'query'; print('Embeddings OK')" && python -c "import src.vectorstore as vs; assert hasattr(vs, 'get_vectorstore'); assert hasattr(vs, 'add_documents'); assert hasattr(vs, 'get_all_document_metadata'); print('Vectorstore OK')"</automated>
  </verify>
  <done>src/config.py contains all settings from both modules with correct defaults. src/embeddings.py uses the custom DashScopeTextEmbeddings with text_type support. src/vectorstore.py uses HttpClient for Docker ChromaDB and exposes get_vectorstore(), add_documents(), get_all_document_metadata().</done>
</task>

<task type="auto">
  <name>Task 2: Rewire app/ modules to import from src/ and merge routers into src/main.py</name>
  <files>app/api/health.py, app/api/documents.py, app/services/vector_store.py, app/services/embeddings.py, src/main.py</files>
  <action>
**app/api/health.py** -- Change the import from `app.config` to `src.config`:
```python
from src.config import get_settings
```
The `check_chromadb()` function uses `settings.chroma_host` and `settings.chroma_port` (lowercase). Change these to `settings.CHROMA_HOST` and `settings.CHROMA_PORT` to match src/config.py's UPPERCASE convention. Similarly change `settings.dashscope_api_key` to `settings.DASHSCOPE_API_KEY` in `check_dashscope_config()`.

**app/api/documents.py** -- Change config import:
```python
from src.config import get_settings
```
Change `settings.upload_dir` to `settings.UPLOAD_DIR`.

Change vector_store import to use the consolidated src module:
```python
from src.vectorstore import add_documents, get_all_document_metadata
```

Keep the imports from `app.models.document`, `app.services.document_parser`, and `app.services.text_splitter` unchanged (these are app/-only modules with no src/ equivalent and no config dependency).

**app/services/vector_store.py** -- This file is now superseded by src/vectorstore.py. Make it a thin re-export so any stale imports don't break:
```python
"""Deprecated: use src.vectorstore instead."""
from src.vectorstore import get_vectorstore as get_vector_store, add_documents, get_all_document_metadata
```

**app/services/embeddings.py** -- Same approach, thin re-export:
```python
"""Deprecated: use src.embeddings instead."""
from src.embeddings import get_embeddings, get_query_embeddings
```

**src/main.py** -- Add the health and documents routers from app/:
```python
from fastapi import FastAPI
from src.api.chat import router as chat_router
from src.api.routes.dataset import router as dataset_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router

app = FastAPI(
    title="Enterprise Knowledge Base RAG System",
    description="OpenAI-compatible RAG API for enterprise document Q&A",
    version="1.0.0",
)

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(dataset_router)


@app.get("/")
async def root():
    return {"message": "Enterprise Knowledge Base RAG System", "version": "1.0.0"}
```

Keep all existing routers (chat_router, dataset_router). Add health_router and documents_router. Add the root `/` endpoint from app/main.py.
  </action>
  <verify>
    <automated>cd /home/developer/.kanpon/code/suzhou-small-llm && python -c "
from src.main import app
routes = [r.path for r in app.routes]
assert '/health' in routes, f'Missing /health, got {routes}'
assert '/documents/upload' in routes, f'Missing /documents/upload, got {routes}'
assert '/documents' in routes, f'Missing /documents, got {routes}'
assert '/v1/chat/completions' in routes, f'Missing /v1/chat/completions, got {routes}'
assert '/dataset/generate' in routes, f'Missing /dataset/generate, got {routes}'
assert '/' in routes, f'Missing /, got {routes}'
print(f'All routes registered: {sorted(routes)}')
"</automated>
  </verify>
  <done>All five endpoints (health, documents/upload, documents, v1/chat/completions, dataset/generate) plus root are registered on the single FastAPI app in src/main.py. app/ modules rewired to import from src/ for config, embeddings, and vectorstore.</done>
</task>

<task type="auto">
  <name>Task 3: Update Dockerfile entrypoint to src.main:app</name>
  <files>Dockerfile</files>
  <action>
Change the CMD in Dockerfile from:
```
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
to:
```
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

This is the only change needed in the Dockerfile. Everything else (WORKDIR, COPY, requirements, uploads dir) stays the same.

Do NOT delete or modify docker-compose.yml -- it already maps port 8000 correctly and passes CHROMA_HOST=chromadb via environment.
  </action>
  <verify>
    <automated>cd /home/developer/.kanpon/code/suzhou-small-llm && grep -q 'src.main:app' Dockerfile && echo "Dockerfile CMD OK" || echo "FAIL: Dockerfile still points to app.main"</automated>
  </verify>
  <done>Dockerfile CMD points to src.main:app. Docker Compose will start the unified service with all endpoints.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client -> API | Untrusted HTTP requests from users |
| API -> ChromaDB | Internal Docker network, trusted |
| API -> DashScope | Outbound API calls with API key |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-quick-01 | S (Spoofing) | /v1/chat/completions | mitigate | Existing Bearer token auth in src/api/chat.py is preserved; no change needed |
| T-quick-02 | I (Info Disclosure) | /documents/upload | accept | Upload endpoint has no auth gate currently (Phase 1 design); this merge does not change that. Low risk for internal enterprise deployment. |
| T-quick-03 | T (Tampering) | Config unification | mitigate | Using env vars for secrets (DASHSCOPE_API_KEY), not hardcoded. Default API_KEY="test-api-key" only applies if env var not set. |
</threat_model>

<verification>
After all three tasks complete:

1. `python -c "from src.main import app; routes = [r.path for r in app.routes]; print(routes)"` shows all 6 routes
2. `grep 'src.main:app' Dockerfile` confirms updated entrypoint
3. `python -c "from src.config import settings; print(settings.CHROMA_HOST, settings.COLLECTION_NAME, settings.UPLOAD_DIR)"` shows `chromadb enterprise_kb /app/uploads`
4. No import errors when loading `src.main`
</verification>

<success_criteria>
- Single FastAPI application in src/main.py serves all endpoints from both Phase 1 and Phase 2/3
- Config is unified in src/config.py with all necessary fields
- Embeddings use the better custom DashScopeTextEmbeddings with text_type support
- Vectorstore uses HttpClient for Docker ChromaDB (not local persistent directory)
- Dockerfile CMD updated to src.main:app
- All app/ modules that were rewired still function correctly (no import errors)
- app/ directory is NOT deleted (still contains models, services, parsers used by documents router)
</success_criteria>

<output>
After completion, create `.planning/quick/260416-pmt-app-src-fastapi/260416-pmt-SUMMARY.md`
</output>
