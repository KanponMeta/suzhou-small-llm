# Feature Landscape

**Domain:** Enterprise internal knowledge base RAG system (Chinese-primary, API-only, no web UI)
**Researched:** 2026-04-16
**Confidence:** HIGH for document ingestion and API features (well-established patterns); MEDIUM for dataset generation specifics (newer area, less standardized)

---

## Table Stakes

Features that users expect. Missing = system is not useful.

### Document Ingestion

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| PDF parsing | Primary enterprise document format | Medium | Use `pypdf` or `unstructured` — both handle Chinese text. `unstructured` preserves layout (tables, headers) at cost of heavier dependency. |
| Word (.docx) parsing | Standard office format in Chinese enterprises | Low | `python-docx` is the standard; handles both `.doc` (via conversion) and `.docx` natively |
| Markdown parsing | Developer and knowledge-base-native format | Low | LangChain's `MarkdownHeaderTextSplitter` preserves heading hierarchy, which improves chunk coherence |
| Plain text (.txt) parsing | Fallback and simplest case | Low | Required to handle any text-based document |
| Text chunking with overlap | Retrieval cannot work without it | Low | Default: 512 tokens, 10-20% overlap. Use `RecursiveCharacterTextSplitter` for mixed Chinese/English content |
| Chinese-aware tokenization in chunking | Token counts differ significantly between CJK and Latin | Medium | Standard character splitters under-count Chinese tokens. Must use token-length-based splitting (not character count) for chunk size accuracy. DashScope `text-embedding-v3` has 8,192 token input limit. |
| Embedding generation | Core of semantic search | Low | DashScope `text-embedding-v3` — 1,024 dimensions, strong Chinese support, 8,192 token limit per chunk |
| Vector store persistence | Without it, re-embed on every restart | Low | ChromaDB persisted to disk via Docker volume — already decided |
| Duplicate / re-upload handling | Documents get updated; re-processing must not create duplicate vectors | Medium | Track document hashes; delete-then-reinsert on re-upload |

### RAG Query API

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| OpenAI-compatible POST endpoint | Required by `接口规范.md` — `model` + `messages` format | Low | Response must match `choices[0].message.content` structure exactly |
| Bearer token authentication | Required by `接口规范.md` | Low | Simple API key check in middleware |
| Semantic vector retrieval | Core function — find relevant chunks by meaning | Low | Top-K cosine similarity search in ChromaDB |
| Prompt augmentation (context injection) | Turns retrieved chunks into grounded answers | Low | Inject retrieved text into system prompt before LLM call |
| LLM answer generation via DashScope | Required by project constraint | Low | `qwen-long` or `qwen-plus` via DashScope API |
| `usage` token count in response | Required by `接口规范.md` — platform evaluates token consumption | Medium | Must track and return `prompt_tokens`, `completion_tokens`, `total_tokens` |
| Graceful "no relevant context" handling | Without it, LLM hallucinates without any knowledge base grounding | Low | Detect empty or low-score retrieval; respond with fallback message |

### Dataset Generation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Generate Q&A pairs from document chunks | Core feature — the entire point of the dataset generation pipeline | High | LLM reads each chunk and generates a `user_prompt` + `correct_answer` pair |
| Output `evaluation_data.json` in correct schema | Required by `数据集提交指南.md` — hard format constraint | Medium | Every test case needs: `id`, `task_type: "chat:text"`, `category`, `user_prompt`, `answer_type`, `correct_answer`. `options` and `attachments` null for free-form text |
| Support both `free_form` and `multiple_choice` answer types | Both are supported by the spec and together increase evaluation depth | High | `multiple_choice` requires generating distractor options — significantly harder than free-form |
| ZIP export of `evaluation_data.json` + empty `attachments/` | Required by `数据集提交指南.md` submission format | Low | For `chat:text`, `attachments/` folder is present but empty |
| Minimum 300 test cases | Spec recommends "at least 300" for text modality | Medium | Requires sufficient document corpus and batched generation |
| Category assignment per test case | `category` field in schema — used by platform for result analysis | Low | Derive from document filename, folder, or section heading |

---

## Differentiators

Features that set this system apart for its specific use case. Not universally expected but high value here.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Source document attribution in answers | Employees can verify which document the answer came from — builds trust, aids compliance | Medium | Return source filename and chunk metadata in the response (can be included in `choices[0].message.content` as a citation footnote or in a non-standard field) |
| LangGraph stateful pipeline orchestration | Enables conditional routing: if retrieval scores are low, reroute or refuse rather than hallucinate. Reusable node graph for both query and dataset generation | High | Already mandated by constraint; the differentiator is using it for conditional logic (retrieval quality gate) rather than as a simple sequential chain |
| Configurable document categories for dataset generation | Lets operators control which document subset feeds into test case generation, enabling domain-targeted evaluation datasets | Medium | Pass a category filter to the generation pipeline |
| Deduplicated and quality-filtered Q&A generation | Use a second LLM pass to filter low-quality or trivially obvious test cases before outputting the JSON | High | Prevents evaluation dataset noise; uses LLM-as-judge pattern |
| Chunk-level provenance in vector store metadata | Store `source_file`, `page_number`, `section_heading` with each vector — enables citation without extra retrieval pass | Low | Set at ingestion time; zero runtime cost |

---

## Anti-Features

Features to explicitly NOT build in MVP.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Web management UI | Out of scope per PROJECT.md; adds frontend complexity with no core value for API consumers | Use CLI scripts for admin operations (upload, trigger generation) |
| Multi-tenant / per-user access control | Single-tenant internal deployment — no user model needed | Single shared API key via environment variable |
| Streaming (SSE) responses | `接口规范.md` requires standard JSON only; streaming adds protocol complexity | Return full JSON response synchronously |
| Document version history / change tracking | Overwrites on re-upload are sufficient for MVP | Delete-and-reinsert on upload; no versioning table |
| Hybrid search (BM25 + vector) | Valuable in production but adds infrastructure complexity; pure vector search on a well-embedded Chinese corpus is sufficient for MVP | Add BM25 reranking in a post-MVP phase if precision is insufficient |
| Cross-encoder reranking | Adds latency and another model dependency. Only worth it when retrieval precision is already failing | Profile retrieval quality first; add if Top-K precision is demonstrably poor |
| Knowledge graph / entity extraction | Advanced feature; far beyond MVP scope | --  |
| Multimodal document ingestion (images inside PDFs, scanned docs) | OCR and layout analysis adds significant complexity; out of scope per PROJECT.md | Extract plain text only from PDFs; skip image-heavy documents for MVP |
| Multiple LLM providers / fallback routing | Single provider (DashScope) is a hard constraint | -- |
| Self-RAG / reflection loops in query pipeline | LangGraph makes this possible but it adds latency and prompt cost; baseline retrieval quality likely sufficient for internal use | Evaluate after MVP; add correction loop only if hallucination rate is unacceptable |
| Evaluation dataset for non-`chat:text` modalities | Explicitly out of scope per PROJECT.md | Only produce `task_type: "chat:text"` records; `attachments/` folder stays empty |

---

## Feature Dependencies

```
Document parsing
  -> Text chunking (Chinese-aware, token-based)
     -> Embedding generation (DashScope text-embedding-v3)
        -> Vector store persistence (ChromaDB)
           -> Semantic retrieval (query pipeline)
              -> Prompt augmentation + LLM generation (DashScope qwen)
                 -> OpenAI-compatible query API

Document parsing
  -> Text chunking
     -> Q&A pair generation (LLM per chunk)
        -> Schema validation (evaluation_data.json format)
           -> ZIP export (evaluation_data.json + attachments/)

LangGraph orchestration layer wraps both pipelines (query + generation)
```

Key constraint: the `接口规范.md` API format is a hard dependency for the query endpoint. Zero deviation allowed.
Key constraint: the `数据集提交指南.md` JSON schema is a hard dependency for dataset generation output. All 5 required fields must be present on every test case.

---

## MVP Recommendation

**Prioritize (must ship for system to be useful):**

1. Document ingestion pipeline — PDF, Word, Markdown, txt. Token-based Chinese chunking. DashScope embedding. ChromaDB persistence. Duplicate detection by file hash.
2. OpenAI-compatible query API — POST endpoint, Bearer auth, `choices[0].message.content` response, `usage` fields, graceful no-context fallback. LangGraph as the orchestrator node graph.
3. Free-form `chat:text` dataset generation — LLM per chunk generates one `user_prompt` + `correct_answer` pair. Writes valid `evaluation_data.json`. Exports as `.zip`.

**Defer (phase 2 or later):**

- `multiple_choice` answer type generation — significant extra complexity (distractor generation); free-form test cases are valid and sufficient for initial evaluation
- Source citation in query responses — valuable but not required by `接口规范.md`; add once core pipeline is stable
- Q&A quality filtering pass — adds LLM cost; implement after measuring initial dataset quality
- Configurable category filtering for generation — add once the basic generation pipeline works end-to-end
- Hybrid search / reranking — profile retrieval quality first; Chinese vector embeddings from `text-embedding-v3` are strong enough for MVP

---

## Sources

- Enterprise RAG patterns: https://towardsdatascience.com/grounding-your-llm-a-practical-guide-to-rag-for-enterprise-knowledge-bases/
- Chunking strategies (2025): https://weaviate.io/blog/chunking-strategies-for-rag
- Chinese/CJK text splitting: https://tonybaloney.github.io/posts/cjk-chinese-japanese-korean-llm-ai-best-practices.html
- DashScope text-embedding-v3: https://www.alibabacloud.com/help/en/model-studio/embedding
- RAG evaluation dataset generation: https://docs.ragas.io/en/v0.1.21/getstarted/prepare_data.html
- Synthetic dataset best practices: https://www.evidentlyai.com/llm-guide/rag-evaluation
- RAGEval framework: https://aclanthology.org/2025.acl-long.418/
- `数据集提交指南.md` and `接口规范.md` — authoritative project constraints (on-disk, highest priority)
