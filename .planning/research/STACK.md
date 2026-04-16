# Technology Stack

**Project:** 企业知识库 RAG 系统
**Researched:** 2026-04-16
**Confidence:** HIGH (all versions verified against PyPI as of research date)

---

## Recommended Stack

### LLM Orchestration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `langgraph` | 1.1.6 | RAG graph orchestration (retrieve → grade → generate) | Mandated by project. LangGraph 1.0 went GA in early 2026; StateGraph API is stable. Provides stateful, conditional node-edge graphs ideal for agentic RAG with retry/grading loops. |
| `langchain-core` | 1.2.30 | Base primitives (Runnable, BaseMessage, etc.) | Required transitive dependency of LangGraph; provides the LCEL interface used by all nodes. |
| `langchain` | 1.2.15 | Chain utilities, retriever wrappers | Thin orchestration glue between retrievers, prompts, and LangGraph nodes. Do not use for LLM calls directly — use `langchain-qwq` instead. |
| `langchain-text-splitters` | 1.1.1 | Document chunking | Dedicated package for `RecursiveCharacterTextSplitter` with Chinese-aware separators (`。`, `，`, `\n`). Separated from `langchain-community` to reduce dependency surface. |

### LLM Provider (DashScope / Qwen)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `langchain-qwq` | 0.3.4 | `ChatQwen` LLM class for LangGraph nodes | **This is the correct 2025/2026 package for Qwen+LangChain.** Replaces the older `ChatTongyi` from `langchain-community`. Provides `ChatQwen` (Qwen3, qwen-plus, qwen-max, qwen-long) with tool calling, structured output, and async support. Maintained by Alibaba Cloud's Qwen team directly. |
| `dashscope` | 1.25.17 | DashScope Python SDK (embedding calls) | Required by `langchain-community`'s `DashScopeEmbeddings`. The `text-embedding-v3` model is accessed through this SDK. Install alongside `langchain-community` for embedding support. |
| `langchain-community` | 0.4.1 | `DashScopeEmbeddings` class | The embedding integration (`DashScopeEmbeddings`) still lives in `langchain-community` as of April 2026. Use only for embeddings — not for chat model calls (use `langchain-qwq` for that). |

**Model recommendations:**

| Use Case | Model | Rationale |
|----------|-------|-----------|
| RAG generation (answer synthesis) | `qwen-plus` | Good balance of quality and cost for Chinese enterprise Q&A; 128K context window handles large retrieved chunks |
| Long-document ingestion / dataset generation | `qwen-long` | Optimized for long-context document processing; cheapest option per token for feeding document content |
| Embeddings | `text-embedding-v3` | 8,192-token input limit, 50+ languages including Chinese, 1,024-dim default vectors. Preferred over v1/v2 for Chinese semantic accuracy. Set dimension=1024 for balanced performance. |

### Vector Database

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `chromadb` | 1.5.7 | Persistent vector store for document chunks | Embedded mode — zero external service dependency, runs as a Docker volume mount with `chromadb/chroma` image or embedded in-process. The 2025 Rust rewrite delivers 4x perf vs older Python versions. Supports `langchain-chroma` integration. Ideal for MVP scale (sub-10M vectors). |

**Why not Qdrant:** Qdrant requires a separate sidecar container and gRPC configuration. Adds complexity for no measurable benefit at enterprise-internal (100–100K document) scale. Revisit if corpus exceeds 5M chunks.

**Why not Milvus:** Milvus requires a distributed backing store (etcd, MinIO). Heavyweight for Docker Compose MVP.

**Why not pgvector:** Requires PostgreSQL sidecar, adds migration tooling, and the vector search UX in SQL is worse than native vector DB APIs.

### API Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `fastapi` | 0.135.3 | OpenAI-compatible REST API (`/v1/chat/completions`) | De facto standard for Python AI APIs in 2025. Native Pydantic v2 support (v0.100+). Async-first, matches LangGraph's async execution model. Route definitions are trivial for the `choices[0].message.content` response shape. |
| `uvicorn` | 0.44.0 | ASGI server | Standard uvicorn for single-container Docker; no need for Gunicorn workers for an internal single-tenant deployment. Use `uvicorn[standard]` for libuv event loop. |
| `pydantic` | 2.13.1 | Request/response models, structured output | Required by FastAPI 0.126+. Use for OpenAI-compatible request/response schemas. LangChain >=0.2.23 supports Pydantic v2 natively. |
| `python-multipart` | 0.0.26 | Multipart file upload (document ingestion endpoint) | Required by FastAPI for `UploadFile` file upload handling. |

### Document Parsing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `PyMuPDF` | 1.27.2.2 | PDF parsing | Top-ranked PDF extractor for RAG in 2025. Preserves Chinese character layout better than pypdf. Fast, handles scanned PDFs (with OCR), and produces clean text per page. Use via `langchain_community.document_loaders.PyMuPDFLoader`. |
| `pypdf` | 6.10.2 | PDF fallback / metadata extraction | Pure-Python fallback. Useful when PyMuPDF encounters DRM or unusual encoding. |
| `python-docx` | 1.2.0 | .docx Word document parsing | Standard library for Microsoft Word. Use via `langchain_community.document_loaders.Docx2txtLoader` or directly with `python_docx.Document()`. Handles Chinese text in docx natively (UTF-8 XML internally). |
| `docx2txt` | latest | .docx text extraction helper | Required by `Docx2txtLoader`. Simpler than `UnstructuredWordDocumentLoader` (which needs LibreOffice — not suitable for Docker MVP). |

**Markdown/plain text:** No extra library needed. Use `langchain_community.document_loaders.TextLoader` with `encoding="utf-8"`.

### Supporting Utilities

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain-chroma` | latest | LangChain ↔ ChromaDB integration | Use `langchain_chroma.Chroma` as the vector store class instead of calling ChromaDB directly — provides clean `as_retriever()` interface for LangGraph nodes. |
| `python-dotenv` | latest | `.env` file loading for DASHSCOPE_API_KEY | Standard approach for secret management in Docker Compose (`env_file:` directive). |
| `httpx` | latest | Async HTTP client | Used internally by `langchain-qwq` for DashScope calls; may also be used for health check endpoints. |
| `tiktoken` | latest | Token counting | Useful for chunking strategy validation and ensuring chunks stay within embedding model's 8,192-token limit. |

---

## What NOT to Use

| Package | Why Avoid |
|---------|-----------|
| `openai` (SDK directly) | Project constraint: all LLM calls go through DashScope. The `openai` SDK can technically point at DashScope's compatible endpoint, but using `langchain-qwq`'s `ChatQwen` is cleaner, integrates with LangGraph's tool-calling interface, and avoids accidental calls to OpenAI's actual servers if the base URL is misconfigured. |
| `langchain-openai` | Same reason as above. Do not install — it brings in the `openai` SDK and creates ambiguity about which provider is being called. |
| `ChatTongyi` (from `langchain-community`) | Superseded by `ChatQwen` from `langchain-qwq` for Qwen3 and newer models. `ChatTongyi` lacks first-class support for Qwen3's thinking mode, structured output improvements, and the newer model IDs. Use `langchain-community` only for `DashScopeEmbeddings`. |
| `langchain_dashscope` (0.1.8) | Stale — last released July 2024. Only supports `text-embedding-v1/v2` and older Qwen 1.5 models. Superseded by `langchain-qwq` + `langchain-community`. |
| `unstructured` (full package) | Pulls in 20+ heavy dependencies including LibreOffice, Tesseract, and torch. Overkill for MVP with only PDF/DOCX/MD support. PyMuPDF + python-docx handles the same formats with a fraction of the Docker image size. |
| `langserve` | For exposing LangGraph graphs as APIs, LangServe adds complexity and its OpenAPI generation had Pydantic v2 issues (fixed only in >=0.3.0). A direct FastAPI route calling LangGraph's `graph.invoke()` is simpler and more predictable for the OpenAI-compatible format requirement. |
| `ragas` | RAGAS is a full evaluation framework. For this project's requirement (generate `evaluation_data.json` Q&A pairs), a purpose-built LangGraph subgraph calling `qwen-long` is lighter and produces output in the project's exact `chat:text` format. RAGAS generates its own opinionated schema. |
| `Milvus` / `Weaviate` / `Qdrant` | Overpowered for enterprise-internal MVP. All require dedicated service containers with their own storage backends. ChromaDB embedded mode is sufficient. |

---

## DashScope + LangGraph Integration Pattern

The key integration points are:

**1. Chat model (LangGraph nodes):**
```python
# pip install langchain-qwq
from langchain_qwq import ChatQwen

llm = ChatQwen(
    model="qwen-plus",           # or qwen-long for dataset generation
    # DASHSCOPE_API_KEY from env
    # For mainland China endpoint:
    # api_base="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
```

`ChatQwen` is a standard `BaseChatModel` — drop it directly into any LangGraph node via `llm.invoke(messages)` or bind tools with `llm.bind_tools(tools)`.

**2. Embeddings:**
```python
# pip install langchain-community dashscope
from langchain_community.embeddings import DashScopeEmbeddings

embeddings = DashScopeEmbeddings(
    model="text-embedding-v3",
    dashscope_api_key=os.environ["DASHSCOPE_API_KEY"],
)
```

Note: The LangChain docs page still shows `text-embedding-v1` as default. Override explicitly with `text-embedding-v3` for better Chinese semantic quality.

**3. Vector store:**
```python
# pip install langchain-chroma chromadb
from langchain_chroma import Chroma

vectorstore = Chroma(
    collection_name="knowledge_base",
    embedding_function=embeddings,
    persist_directory="/data/chroma",  # mounted Docker volume
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
```

**4. LangGraph RAG graph skeleton:**
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from langchain_core.documents import Document

class RAGState(TypedDict):
    question: str
    documents: List[Document]
    answer: str

def retrieve(state: RAGState) -> RAGState: ...
def generate(state: RAGState) -> RAGState: ...

graph = StateGraph(RAGState)
graph.add_node("retrieve", retrieve)
graph.add_node("generate", generate)
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "generate")
graph.add_edge("generate", END)
rag_app = graph.compile()
```

---

## API Endpoint (OpenAI-Compatible)

The `接口规范.md` requires `choices[0].message.content` format. Implement as:

```python
# FastAPI + Pydantic v2
from fastapi import FastAPI
from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]

class ChatResponse(BaseModel):
    choices: list[dict]

app = FastAPI()

@app.post("/v1/chat/completions")
async def chat(req: ChatRequest) -> ChatResponse:
    result = await rag_app.ainvoke({"question": req.messages[-1].content})
    return ChatResponse(choices=[{"message": {"role": "assistant", "content": result["answer"]}}])
```

---

## Python Version

**Require Python 3.11.** All packages support 3.10–3.13, but 3.11 is the stable, widely-available version in Docker's `python:3.11-slim` base image. Avoid 3.12/3.13 until dependency ecosystem fully stabilizes.

---

## Docker Compose Service Layout

```
services:
  api:        # FastAPI + LangGraph app
  chroma:     # chromadb/chroma:latest  (optional: use embedded mode instead)
```

For MVP, ChromaDB in **embedded mode** (in-process, persisted volume) avoids needing the `chroma` service at all. The separate `chroma` Docker service is only needed if you want HTTP API access from other tools.

---

## Installation

```bash
# Core LLM + orchestration
pip install langgraph==1.1.6 langchain==1.2.15 langchain-core==1.2.30 langchain-text-splitters==1.1.1

# Qwen / DashScope integration
pip install langchain-qwq==0.3.4 dashscope==1.25.17 langchain-community==0.4.1

# Vector store
pip install chromadb==1.5.7 langchain-chroma

# API layer
pip install "fastapi==0.135.3" "uvicorn[standard]==0.44.0" pydantic==2.13.1 python-multipart==0.0.26

# Document parsing
pip install PyMuPDF==1.27.2.2 pypdf==6.10.2 python-docx==1.2.0 docx2txt

# Utilities
pip install python-dotenv httpx tiktoken
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| LLM integration | `langchain-qwq` 0.3.4 | `ChatTongyi` (langchain-community) | Superseded; lacks Qwen3 structured output and tool calling improvements |
| LLM integration | `langchain-qwq` 0.3.4 | `langchain-openai` pointing at DashScope | Creates OpenAI SDK dependency; risk of accidental routing to OpenAI |
| PDF parsing | PyMuPDF 1.27 | `unstructured` | 20+ heavy transitive deps; requires LibreOffice in Docker |
| PDF parsing | PyMuPDF 1.27 | pypdfium2 | Less community support; PyMuPDF covers same use cases |
| Vector DB | ChromaDB 1.5.7 | Qdrant | Requires sidecar container; no benefit at MVP scale |
| API framework | FastAPI 0.135 | Flask / Django | Async-first; Pydantic v2 native; smaller footprint |
| Embedding model | `text-embedding-v3` | `text-embedding-v1` | v1 is legacy; v3 has 8K token window vs 2K for v1 and better Chinese semantic coverage |
| Eval generation | Custom LangGraph subgraph | `ragas` | RAGAS output schema doesn't match `chat:text` `evaluation_data.json` format; custom generation is 50 lines of code |

---

## Sources

- LangGraph 1.1.6 on PyPI: https://pypi.org/project/langgraph/
- LangGraph 1.0 GA announcement: https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available
- langchain-qwq 0.3.4 on PyPI: https://pypi.org/project/langchain-qwq/
- ChatQwen integration docs: https://docs.langchain.com/oss/python/integrations/chat/qwen
- ChatTongyi integration docs (for DashScopeEmbeddings context): https://docs.langchain.com/oss/python/integrations/chat/tongyi
- DashScope embeddings in LangChain: https://docs.langchain.com/oss/python/integrations/embeddings/dashscope
- DashScope text embedding API: https://www.alibabacloud.com/help/en/model-studio/text-embedding-synchronous-api
- DashScope OpenAI-compatible endpoint: https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope
- ChromaDB Docker docs: https://docs.trychroma.com/guides/deploy/docker
- ChromaDB 1.5.7 on PyPI: https://pypi.org/project/chromadb/
- FastAPI 0.135.3 on PyPI: https://pypi.org/project/fastapi/
- PyMuPDF 1.27.2.2 on PyPI: https://pypi.org/project/pymupdf/
- DashScope SDK 1.25.17 on PyPI: https://pypi.org/project/dashscope/
- Pydantic 2.13.1 on PyPI: https://pypi.org/project/pydantic/
- LangChain Pydantic v2 compatibility: https://python.langchain.com/docs/how_to/pydantic_compatibility/
