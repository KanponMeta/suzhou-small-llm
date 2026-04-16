<!-- GSD:project-start source:PROJECT.md -->
## Project

**企业知识库 RAG 系统**

面向企业内部的文档知识库问答系统。支持上传 PDF、Word、Markdown 等中文文档，通过 RAG（检索增强生成）技术构建知识索引，对外提供 OpenAI 兼容的文本对话查询接口，并能从知识库内容自动生成符合平台规范的 `chat:text` 评测数据集，用于小语言模型的效果评测。

**Core Value:** 用户上传企业文档后，能通过标准 API 接口准确得到基于知识库内容的中文回答。

### Constraints

- **Tech Stack**: LangGraph 作为 LLM 编排框架 — 用户明确要求
- **LLM Provider**: 阿里云百炼 DashScope API — 统一使用，不引入 OpenAI 或其他境外服务
- **Deployment**: Docker Compose — 便于在企业内网环境快速部署
- **Language**: 中文优先 — embedding 模型和生成模型均须原生支持中文
- **API Compatibility**: 查询接口须 100% 符合 `接口规范.md` 定义的格式
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
| Use Case | Model | Rationale |
|----------|-------|-----------|
| RAG generation (answer synthesis) | `qwen-plus` | Good balance of quality and cost for Chinese enterprise Q&A; 128K context window handles large retrieved chunks |
| Long-document ingestion / dataset generation | `qwen-long` | Optimized for long-context document processing; cheapest option per token for feeding document content |
| Embeddings | `text-embedding-v3` | 8,192-token input limit, 50+ languages including Chinese, 1,024-dim default vectors. Preferred over v1/v2 for Chinese semantic accuracy. Set dimension=1024 for balanced performance. |
### Vector Database
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `chromadb` | 1.5.7 | Persistent vector store for document chunks | Embedded mode — zero external service dependency, runs as a Docker volume mount with `chromadb/chroma` image or embedded in-process. The 2025 Rust rewrite delivers 4x perf vs older Python versions. Supports `langchain-chroma` integration. Ideal for MVP scale (sub-10M vectors). |
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
### Supporting Utilities
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain-chroma` | latest | LangChain ↔ ChromaDB integration | Use `langchain_chroma.Chroma` as the vector store class instead of calling ChromaDB directly — provides clean `as_retriever()` interface for LangGraph nodes. |
| `python-dotenv` | latest | `.env` file loading for DASHSCOPE_API_KEY | Standard approach for secret management in Docker Compose (`env_file:` directive). |
| `httpx` | latest | Async HTTP client | Used internally by `langchain-qwq` for DashScope calls; may also be used for health check endpoints. |
| `tiktoken` | latest | Token counting | Useful for chunking strategy validation and ensuring chunks stay within embedding model's 8,192-token limit. |
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
## DashScope + LangGraph Integration Pattern
# pip install langchain-qwq
# pip install langchain-community dashscope
# pip install langchain-chroma chromadb
## API Endpoint (OpenAI-Compatible)
# FastAPI + Pydantic v2
## Python Version
## Docker Compose Service Layout
## Installation
# Core LLM + orchestration
# Qwen / DashScope integration
# Vector store
# API layer
# Document parsing
# Utilities
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
