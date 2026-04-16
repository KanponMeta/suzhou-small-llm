# Requirements: 企业知识库 RAG 系统

**Defined:** 2026-04-16
**Core Value:** 用户上传企业文档后，能通过标准 API 接口准确得到基于知识库内容的中文回答。

## v1 Requirements

### Infrastructure (INFRA)

- [ ] **INFRA-01**: System starts with a single `docker compose up` command, no manual setup required
- [ ] **INFRA-02**: All configuration (API key, model names, ports) is provided via environment variables / `.env` file
- [ ] **INFRA-03**: System exposes a `GET /health` endpoint that returns HTTP 200 when all services are ready

### Document Ingestion (INGEST)

- [ ] **INGEST-01**: User can upload a PDF file via POST API and have its text content extracted and indexed
- [ ] **INGEST-02**: User can upload a Markdown or plain text file (.md, .txt) via POST API and have its content indexed
- [ ] **INGEST-03**: Uploaded documents are split into chunks using Chinese-aware separators and embedded via DashScope `text-embedding-v3`
- [ ] **INGEST-04**: Embedded chunks are stored in ChromaDB with document source metadata and persisted across container restarts
- [ ] **INGEST-05**: User can query a `GET /documents` endpoint to list all indexed documents with their IDs and metadata

### RAG Query (QUERY)

- [ ] **QUERY-01**: System exposes a `POST /v1/chat/completions` endpoint that accepts `{model, messages}` request body matching `接口规范.md`
- [ ] **QUERY-02**: Query triggers a LangGraph RAG flow: retrieve relevant chunks → assess relevance → generate answer using Qwen LLM
- [ ] **QUERY-03**: API response matches `接口规范.md` format exactly — `choices[0].message.content` with `usage` token counts
- [ ] **QUERY-04**: When no relevant documents are found, system returns a polite Chinese fallback response (no hallucination)

### Evaluation Dataset (DATASET)

- [ ] **DATASET-01**: System exposes a `POST /dataset/generate` endpoint that triggers auto-generation of Q&A pairs from all indexed documents
- [ ] **DATASET-02**: Generated Q&A pairs are `chat:text` / `free_form` type with all required fields: `id`, `task_type`, `category`, `user_prompt`, `answer_type`, `correct_answer`
- [ ] **DATASET-03**: Generated dataset is exported as a `.zip` file containing `evaluation_data.json` and an empty `attachments/` folder, matching `数据集提交指南.md` format
- [ ] **DATASET-04**: Each generated Q&A pair is grounded in the source document chunk (no hallucinated answers)

## v2 Requirements

### Document Ingestion

- **INGEST-V2-01**: Support Word (.docx) file upload and text extraction
- **INGEST-V2-02**: Support scanned PDF via OCR (PaddleOCR for Chinese characters)
- **INGEST-V2-03**: User can delete an indexed document by ID

### Evaluation Dataset

- **DATASET-V2-01**: Support `multiple_choice` type test case generation (with A/B/C/D distractors)
- **DATASET-V2-02**: Allow configuring number of Q&A pairs to generate per document

### Query API

- **QUERY-V2-01**: Support streaming responses (Server-Sent Events)
- **QUERY-V2-02**: Expose source document citations in response metadata

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web 管理界面 | MVP 以 API 和 CLI 为交互方式，降低前端复杂度 |
| 多模态数据集（图像/音频/视频） | MVP 仅覆盖 `chat:text` 类型 |
| 多租户 / 用户权限管理 | 单租户内部部署，无需复杂权限体系 |
| 文档版本控制 / 知识图谱 | 超出 MVP 范围 |
| OpenAI / 非 DashScope 模型后端 | 统一使用阿里云百炼，避免多供应商复杂性 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| INGEST-01 | Phase 1 | Pending |
| INGEST-02 | Phase 1 | Pending |
| INGEST-03 | Phase 1 | Pending |
| INGEST-04 | Phase 1 | Pending |
| INGEST-05 | Phase 1 | Pending |
| QUERY-01 | Phase 2 | Pending |
| QUERY-02 | Phase 2 | Pending |
| QUERY-03 | Phase 2 | Pending |
| QUERY-04 | Phase 2 | Pending |
| DATASET-01 | Phase 3 | Pending |
| DATASET-02 | Phase 3 | Pending |
| DATASET-03 | Phase 3 | Pending |
| DATASET-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 (full coverage)

---
*Requirements defined: 2026-04-16*
*Last updated: 2026-04-16 after roadmap creation*
