# Architecture Patterns

**Domain:** Enterprise RAG system — document ingestion, knowledge-base Q&A, evaluation dataset generation
**Researched:** 2026-04-16

---

## Recommended Architecture

The system consists of three independently invokable pipelines sharing a common vector store and LLM client layer.

```
┌────────────────────────────────────────────────────────────────────────┐
│                         REST API (FastAPI)                             │
│                                                                        │
│  POST /v1/ingest          POST /v1/chat/completions   POST /v1/dataset │
│         │                          │                        │          │
│         ▼                          ▼                        ▼          │
│  IngestOrchestrator         RAGGraph (LangGraph)    DatasetGenerator   │
│         │                  (StateGraph)                     │          │
│         │                          │                        │          │
└─────────┼──────────────────────────┼────────────────────────┼──────────┘
          │                          │                        │
          ▼                          ▼                        ▼
┌─────────────────┐       ┌─────────────────┐     ┌──────────────────┐
│  DocumentLoader │       │  VectorRetriever │     │  ChunkIterator   │
│  + Chunker      │       │  (ChromaDB)      │     │  + QA Prompter   │
└────────┬────────┘       └────────┬────────┘     └──────────┬───────┘
         │                         │                          │
         ▼                         ▼                          ▼
┌─────────────────┐       ┌─────────────────────────────────────────┐
│  EmbeddingClient│       │          LLMClient                      │
│  (DashScope     │       │  (ChatOpenAI → DashScope OpenAI-compat) │
│  text-embed-v3) │       │  model: qwen-long / qwen-plus           │
└────────┬────────┘       └─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│    ChromaDB     │
│  (Docker vol)   │
└─────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **FastAPI router** | HTTP request/response, input validation (Pydantic), OpenAI-compatible schema | IngestOrchestrator, RAGGraph, DatasetGenerator |
| **IngestOrchestrator** | Drive the ingestion pipeline: load → chunk → embed → store | DocumentLoader, Chunker, EmbeddingClient, ChromaDB |
| **DocumentLoader** | Parse PDF/DOCX/MD/TXT to raw text; normalise metadata (filename, page) | PyPDF2 / python-docx / markdown / plain text |
| **Chunker** | RecursiveCharacterTextSplitter; produce chunks with overlap | LangChain text_splitter |
| **EmbeddingClient** | Wrap DashScope text-embedding-v3; batch embed lists of strings | DashScope HTTP API (via `langchain-community DashScopeEmbeddings`) |
| **ChromaDB** | Persist vectors + metadata; answer similarity queries | EmbeddingClient (at index time), VectorRetriever (at query time) |
| **RAGGraph** | LangGraph StateGraph implementing retrieve → grade → generate (or rewrite → retrieve loop) | VectorRetriever, LLMClient |
| **VectorRetriever** | Wrap Chroma `.as_retriever()`; return top-k Document objects | ChromaDB, RAGGraph |
| **LLMClient** | Thin wrapper around `ChatOpenAI` pointed at DashScope OpenAI-compatible endpoint | DashScope HTTP API |
| **DatasetGenerator** | Iterate chunks, call LLM with QA-generation prompt, collect structured pairs | ChunkIterator (ChromaDB scan), LLMClient |
| **DatasetExporter** | Serialise QA pairs to `evaluation_data.json`; zip with `attachments/` directory | filesystem |

---

## Data Flow: Pipeline 1 — Document Ingestion

```
HTTP POST /v1/ingest  (multipart file upload)
         │
         ▼
    FastAPI router
         │  validate file type, size
         ▼
    DocumentLoader
         │  PyPDF2 / python-docx / markdown read
         │  output: List[str] pages or paragraphs
         ▼
    Chunker  (RecursiveCharacterTextSplitter)
         │  chunk_size=1000, chunk_overlap=100
         │  output: List[Document]  (text + metadata: source, page, chunk_id)
         ▼
    EmbeddingClient  (DashScopeEmbeddings, model="text-embedding-v3")
         │  batch embed; output: List[List[float]]
         ▼
    ChromaDB  .add_documents()
         │  persist to /chroma/data volume
         ▼
    Return:  { "status": "ok", "chunks_indexed": N }
```

Key decisions:
- Ingestion is synchronous for MVP (file sizes are bounded enterprise docs). Background queue can be added later if throughput demands it.
- Metadata stored per chunk: `source_file`, `page_number`, `chunk_index`, `ingest_timestamp`. This metadata surfaces in dataset generation.
- Chunking happens before embedding, not after — avoids embedding oversized pages.

---

## Data Flow: Pipeline 2 — RAG Query

```
HTTP POST /v1/chat/completions  { "model": "...", "messages": [...] }
         │
         ▼
    FastAPI router
         │  extract last user message as query
         ▼
    RAGGraph.invoke(state)          ← LangGraph StateGraph entry point
         │
         ├─► [Node: retrieve]
         │       VectorRetriever.get_relevant_documents(question)
         │       top_k=5 from ChromaDB
         │       state.documents updated
         │
         ├─► [Node: grade_documents]   (conditional — can be disabled for simple mode)
         │       LLMClient structured-output call
         │       grades each doc "relevant" / "not relevant"
         │       state.documents filtered
         │
         ├─► [Conditional edge]
         │       if len(relevant_docs) > 0  → generate
         │       elif retry_count < 1       → rewrite_query
         │       else                        → generate (with whatever is available)
         │
         ├─► [Node: rewrite_query]  (optional loop)
         │       LLMClient rewrites question for better retrieval
         │       retry_count += 1
         │       loop back to retrieve
         │
         └─► [Node: generate]
                 LLMClient: system prompt + context chunks + user question
                 state.generation = answer string
                 → END
         │
         ▼
    FastAPI router  wraps in OpenAI response schema:
         {
           "id": "chatcmpl-...",
           "choices": [{ "message": { "role": "assistant", "content": state.generation } }],
           "model": model_name
         }
```

---

## Data Flow: Pipeline 3 — Dataset Generation

```
HTTP POST /v1/dataset/generate  { "collection": "default", "max_chunks": 200 }
         │
         ▼
    FastAPI router
         │
         ▼
    DatasetGenerator
         │
         ├─► ChromaDB .get(limit=max_chunks)   — iterate all stored chunks
         │
         └─► For each chunk:
                 LLMClient call with QA-generation prompt:
                   "根据以下文本，生成一个中文问题和对应答案，以JSON格式返回
                    {'question': ..., 'answer': ...}"
                 Retry if JSON parse fails (up to 3 times)
                 Accumulate QAPair objects
         │
         ▼
    DatasetExporter
         │  Build evaluation_data.json:
         │  {
         │    "type": "chat:text",
         │    "data": [
         │      { "messages": [
         │          { "role": "user",    "content": question },
         │          { "role": "assistant", "content": answer }
         │        ]
         │      }, ...
         │    ]
         │  }
         │
         ├─► Write evaluation_data.json
         ├─► Collect source files into attachments/
         └─► zip → dataset_YYYYMMDD.zip
         │
         ▼
    Return:  file download or { "path": "...", "pairs_generated": N }
```

Note: dataset generation is NOT a LangGraph graph — it is a simple sequential loop.
LangGraph overhead (state machine, checkpointing) adds complexity without benefit for a
batch map-over-items job. Use plain Python async iteration.

---

## LangGraph State Graph Design

### State Schema

```python
from typing import TypedDict, List, Annotated
from langgraph.graph.message import add_messages
from langchain_core.documents import Document

class RAGState(TypedDict):
    question: str                          # original user question
    rewritten_question: str                # after rewrite_query node (may equal question)
    documents: List[Document]              # retrieved and graded context chunks
    generation: str                        # final LLM answer
    retry_count: int                       # prevents infinite rewrite loops
```

### Graph Topology

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(RAGState)

# nodes
graph.add_node("retrieve",       retrieve_node)
graph.add_node("grade_docs",     grade_documents_node)
graph.add_node("rewrite_query",  rewrite_query_node)
graph.add_node("generate",       generate_node)

# edges
graph.set_entry_point("retrieve")

graph.add_edge("retrieve", "grade_docs")

graph.add_conditional_edges(
    "grade_docs",
    decide_after_grading,           # returns "generate" | "rewrite_query"
    {"generate": "generate", "rewrite_query": "rewrite_query"}
)

graph.add_edge("rewrite_query", "retrieve")   # loop back
graph.add_edge("generate", END)

rag_app = graph.compile()
```

### Routing Function

```python
def decide_after_grading(state: RAGState) -> str:
    if len(state["documents"]) > 0:
        return "generate"
    elif state["retry_count"] < 1:
        return "rewrite_query"
    else:
        return "generate"   # generate with empty context rather than infinite loop
```

### Node Signatures (key interfaces)

```python
def retrieve_node(state: RAGState) -> dict:
    docs = retriever.invoke(state.get("rewritten_question") or state["question"])
    return {"documents": docs, "retry_count": state.get("retry_count", 0)}

def grade_documents_node(state: RAGState) -> dict:
    # LLM structured output: GradeDocuments(binary_score="yes"|"no")
    relevant = [d for d in state["documents"] if grade_doc(state["question"], d) == "yes"]
    return {"documents": relevant}

def rewrite_query_node(state: RAGState) -> dict:
    new_q = llm.invoke(rewrite_prompt.format(question=state["question"]))
    return {"rewritten_question": new_q.content, "retry_count": state["retry_count"] + 1}

def generate_node(state: RAGState) -> dict:
    context = "\n\n".join(d.page_content for d in state["documents"])
    answer = llm.invoke(rag_prompt.format(context=context, question=state["question"]))
    return {"generation": answer.content}
```

---

## Recommended Project Directory Structure

```
suzhou-small-llm/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory, lifespan, CORS
│   ├── config.py                   # pydantic-settings: DASHSCOPE_API_KEY, CHROMA_HOST, etc.
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ingest.py               # POST /v1/ingest
│   │   ├── chat.py                 # POST /v1/chat/completions
│   │   └── dataset.py              # POST /v1/dataset/generate + GET /v1/dataset/{id}/download
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chat.py                 # OpenAI-compatible ChatRequest, ChatResponse, Choice, Message
│   │   ├── ingest.py               # IngestRequest, IngestResponse
│   │   └── dataset.py              # DatasetRequest, DatasetResponse, QAPair
│   │
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── ingest.py               # IngestOrchestrator: load → chunk → embed → store
│   │   ├── rag_graph.py            # LangGraph StateGraph definition and compile()
│   │   └── dataset_generator.py    # DatasetGenerator + DatasetExporter
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_loader.py      # PDF / DOCX / MD / TXT loaders, returns List[Document]
│   │   ├── chunker.py              # RecursiveCharacterTextSplitter wrapper
│   │   ├── embedding_client.py     # DashScopeEmbeddings wrapper
│   │   ├── llm_client.py           # ChatOpenAI → DashScope endpoint factory
│   │   └── vector_store.py         # ChromaDB client init, collection management
│   │
│   └── utils/
│       ├── __init__.py
│       └── file_utils.py           # tmp file handling, zip creation
│
├── data/
│   └── .gitkeep                    # local dev: uploaded docs land here temporarily
│
├── tests/
│   ├── test_ingest.py
│   ├── test_rag_graph.py
│   └── test_dataset.py
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── 数据集提交指南.md               # external constraint doc (read-only reference)
    接口规范.md                     # external constraint doc (read-only reference)
```

---

## Docker Compose Service Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     docker-compose.yml                       │
│                                                             │
│  ┌──────────────────┐         ┌──────────────────────────┐  │
│  │   api (FastAPI)  │─────────│   chromadb               │  │
│  │   port: 8000     │  HTTP   │   port: 8001 (internal)  │  │
│  │   depends_on:    │         │   volume: chroma_data     │  │
│  │     chromadb     │         └──────────────────────────┘  │
│  └──────────────────┘                                        │
│                                                             │
│  External:  DashScope API (HTTPS, internet)                  │
└─────────────────────────────────────────────────────────────┘

Volumes:
  chroma_data:   persistent ChromaDB storage
  upload_tmp:    ephemeral file upload staging (optional tmpfs)
```

### Canonical docker-compose.yml Structure

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
    depends_on:
      chromadb:
        condition: service_healthy
    volumes:
      - ./data:/app/data

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
    volumes:
      - chroma_data:/chroma/chroma
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v2/heartbeat"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  chroma_data:
```

Note: The `api` container accesses ChromaDB via HTTP client (`chromadb.HttpClient(host="chromadb", port=8000)`), NOT the embedded in-process client. This is the correct mode for Docker Compose; the embedded client is only for single-process local dev.

---

## Interface Definitions (Key Contracts)

### OpenAI-Compatible Chat Endpoint

```
POST /v1/chat/completions
Content-Type: application/json

Request:
{
  "model": "qwen-long",
  "messages": [
    {"role": "user", "content": "什么是...?"}
  ]
}

Response:
{
  "id": "chatcmpl-<uuid>",
  "object": "chat.completion",
  "model": "qwen-long",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "..."},
    "finish_reason": "stop"
  }]
}
```

### Ingest Endpoint

```
POST /v1/ingest
Content-Type: multipart/form-data

Fields:
  file:        (binary) — PDF, DOCX, MD, or TXT
  collection:  (string, optional, default="default")

Response:
{
  "status": "ok",
  "source": "filename.pdf",
  "chunks_indexed": 42
}
```

### Dataset Generation Endpoint

```
POST /v1/dataset/generate
Content-Type: application/json

Request:
{
  "collection": "default",
  "max_chunks": 100
}

Response:
{
  "status": "ok",
  "pairs_generated": 87,
  "download_url": "/v1/dataset/abc123/download"
}

GET /v1/dataset/{id}/download
→ application/zip  (evaluation_data.json + attachments/)
```

---

## Suggested Build Order

Dependencies determine this order. Each item must be complete before the next can be validated end-to-end.

```
Phase 1 — Foundation (no LLM calls needed to verify)
  1. Project skeleton:   directory structure, config.py, .env.example
  2. ChromaDB service:   Docker Compose up, HttpClient connection test
  3. EmbeddingClient:    DashScopeEmbeddings wrapper + smoke test against API

Phase 2 — Ingestion Pipeline (unblocks query pipeline)
  4. DocumentLoader:     PDF + DOCX + MD loaders, returns List[Document]
  5. Chunker:            RecursiveCharacterTextSplitter configured for Chinese text
  6. IngestOrchestrator: wire load → chunk → embed → chroma.add()
  7. POST /v1/ingest:    FastAPI route, multipart upload, returns chunk count

Phase 3 — Query Pipeline (requires Phase 2 data in ChromaDB)
  8. LLMClient:          ChatOpenAI → DashScope base_url, model=qwen-long
  9. RAGGraph:           LangGraph StateGraph: retrieve → grade → generate nodes
  10. POST /v1/chat/completions: FastAPI route, OpenAI-schema request/response

Phase 4 — Dataset Generation (requires Phases 2 + 3)
  11. DatasetGenerator:  chunk iterator + QA-generation prompt loop
  12. DatasetExporter:   evaluation_data.json serialisation + zip packaging
  13. POST /v1/dataset/generate + GET download: FastAPI routes

Phase 5 — Hardening
  14. Docker Compose full stack test (api + chromadb)
  15. Error handling: malformed files, empty retrieval, DashScope rate limits
  16. Dockerfile optimisation (multi-stage, non-root user)
```

Rationale for this ordering:
- ChromaDB must be running before any embed/index/query work is possible.
- Embedding client is validated in isolation before it is embedded in the ingestion pipeline — a DashScope API key misconfiguration is the most likely early failure.
- Ingestion must produce indexed data before the query graph has anything to retrieve.
- Dataset generation depends on both stored chunks (ingestion) and a working LLM call (query pipeline's LLMClient) — it comes last.
- The LangGraph graph (step 9) is built after the individual node functions are independently testable (steps 8, VectorRetriever already works from step 7).

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: ChromaDB embedded (in-process) client in Docker
**What:** Using `chromadb.Client()` instead of `chromadb.HttpClient()` inside the API container.
**Why bad:** In-process client creates a local SQLite database inside the container's ephemeral filesystem — data is lost on container restart, and it cannot be shared across container replicas.
**Instead:** Always use `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)` in the API container. Run ChromaDB as a separate service with a named volume.

### Anti-Pattern 2: Single LangGraph graph handling ingestion
**What:** Putting document loading, chunking, and embedding inside a LangGraph StateGraph.
**Why bad:** LangGraph adds checkpointing, state serialisation, and retry machinery. Ingestion is a deterministic sequential pipeline — the overhead is pure cost, not benefit.
**Instead:** Use a plain Python class (IngestOrchestrator) for ingestion. Reserve LangGraph for the query pipeline where conditional routing (grade → rewrite loop) provides real value.

### Anti-Pattern 3: Rebuilding embeddings on every API call
**What:** Embedding the user query using an async call buried inside the RAGGraph retrieve node without caching.
**Why bad:** Query embeddings are cheap and fast but should not be awaited inside synchronous code paths without proper async handling.
**Instead:** All DashScope calls must be async (`ainvoke` / `aembed_query`). FastAPI endpoint must be `async def`. LangGraph graph must be compiled and invoked with `await rag_app.ainvoke(state)`.

### Anti-Pattern 4: Hardcoding model names in multiple places
**What:** Scattering `"qwen-long"` and `"text-embedding-v3"` literals across files.
**Why bad:** Model upgrades require hunting across the codebase.
**Instead:** Centralise all model names in `config.py` as `Settings` fields with defaults. A single `.env` change updates the whole system.

---

## Scalability Considerations

| Concern | At MVP / < 100 docs | At 1K–10K docs | At 100K+ docs |
|---------|---------------------|----------------|---------------|
| ChromaDB | Single container, named volume | Same, increase `n_results` tuning | Consider Milvus or Qdrant with sharding |
| Ingestion | Synchronous, single request | Background task queue (Celery or asyncio queue) | Distributed worker pool |
| Query latency | ~2–4s (1 LLM call + embed) | Same unless grading adds calls | Consider caching frequent queries |
| Dataset generation | Sequential loop, minutes acceptable | Same | Async batch with LLM concurrency limit |
| DashScope rate limits | Not a concern | Add retry with exponential backoff | Implement token-bucket rate limiter |

---

## Sources

- LangGraph Agentic RAG docs: https://docs.langchain.com/oss/python/langgraph/agentic-rag
- LangGraph StateGraph reference: https://reference.langchain.com/python/langgraph/graph/state/StateGraph
- LangGraph self-reflective RAG blog: https://blog.langchain.com/agentic-rag-with-langgraph/
- DashScope LangChain chat integration (ChatTongyi): https://api.python.langchain.com/en/latest/community/chat_models/langchain_community.chat_models.tongyi.ChatTongyi.html
- DashScope embeddings reference: https://python.langchain.com/api_reference/community/embeddings/langchain_community.embeddings.dashscope.DashScopeEmbeddings.html
- DashScope OpenAI-compatible endpoint: https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope
- langchain-qwq ChatQwen (newer Qwen3 series): https://pypi.org/project/langchain-qwq/
- ChromaDB Docker deployment guide: https://docs.trychroma.com/guides/deploy/docker
- FastAPI + LangGraph production template: https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template
- Synthetic dataset generation with RAG: https://langchain-opentutorial.gitbook.io/langchain-opentutorial/19-cookbook/08-syntheticdataset/13-syntheticdatasetgenerationusingrag
