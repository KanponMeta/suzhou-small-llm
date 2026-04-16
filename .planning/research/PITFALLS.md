# Domain Pitfalls

**Domain:** Enterprise RAG system — LangGraph + DashScope (Qwen) + ChromaDB + Chinese documents
**Researched:** 2026-04-16

---

## Critical Pitfalls

Mistakes that cause rewrites or significant data loss.

---

### Pitfall 1: ChromaDB Silently Loses All Data on Container Restart

**What goes wrong:** The ChromaDB Docker image defaults to in-memory mode (`IS_PERSISTENT=FALSE`) even when a bind-mount volume is configured. The container starts without errors, writes appear to succeed via the API, but no `chroma.sqlite3` file is ever written to disk. Every container restart wipes the entire vector store. There are no warnings in the logs.

**Why it happens:** `IS_PERSISTENT` defaults to `False` in the Docker image. A bind-mount alone does not activate persistence — the environment variable must be explicitly set. A second variant: if you mount a `config.yaml` that only overrides port settings, it implicitly changes the data path from `/data` to `/chroma`, making the volume mount point to the wrong directory.

**Consequences:** The entire index must be rebuilt from scratch on every restart. In a Docker Compose deployment this goes undetected during development (containers rarely restart) and surfaces catastrophically in production.

**Prevention:**
- Always set `IS_PERSISTENT=TRUE` as an environment variable in `docker-compose.yml`
- Pin the data path explicitly: `PERSIST_DIRECTORY=/chroma/data`
- Mount the volume to the exact same path: `./chroma_data:/chroma/data`
- Add a startup health check that verifies `chroma.sqlite3` exists before serving traffic
- Never rely on config file mounting for persistence settings

**Detection:** After a compose restart, query any collection — if it returns 0 documents when documents were ingested before, persistence is broken.

**Phase:** Address in Phase 1 (infrastructure setup) before any ingestion code is written.

---

### Pitfall 2: DashScope Embedding Batch Size Hard Limit (10 items)

**What goes wrong:** `text-embedding-v3` (and `text-embedding-v4`) enforce a maximum batch size of 10 texts per API call. Sending 11+ items returns an error: `"batch size is invalid, it should not be larger than 10"`. This is not a soft warning — the entire batch fails and no embeddings are returned.

**Why it happens:** DashScope's embedding API enforces server-side batch limits that are stricter than most other embedding providers (OpenAI allows 2048 items per batch). The limit is not prominently documented.

**Consequences:** Naive implementations that pass a full document's chunks to the embedding API in one call will fail at ingestion time. If the error is swallowed silently (e.g., in a try/except that logs but continues), chunks will be missing from the index without obvious symptoms — retrieval just degrades quietly.

**Prevention:**
- Always chunk embedding calls into batches of at most 10 before any API call
- Implement a wrapper: `embed_in_batches(texts, batch_size=10)`
- Add an assertion/test: verify `len(embedded_results) == len(input_texts)` after every ingestion
- Log batch count and total embedding count at INFO level

**Detection:** API returns HTTP 400 with "batch size is invalid" message. Or: document count in ChromaDB is lower than expected chunk count.

**Phase:** Address in Phase 1 (document ingestion pipeline).

---

### Pitfall 3: Query vs. Document `text_type` Mismatch in DashScope Embeddings

**What goes wrong:** DashScope's `text-embedding-v3` supports asymmetric embedding — documents should be embedded with `text_type=document` and queries with `text_type=query`. Using the same `text_type` for both (or omitting the parameter entirely) causes the query and document vectors to occupy misaligned semantic spaces, significantly degrading retrieval recall.

**Why it happens:** Asymmetric embedding models are trained with separate encoder paths for queries and passages. Calling the API without specifying `text_type` defaults to a symmetric mode that does not exploit this asymmetry. This is a silent bug — the system still returns results, but they are lower quality.

**Consequences:** Retrieval accuracy degrades by an unquantifiable but real margin. The system appears functional during development, but real-world queries that are phrased differently from document text return low-quality matches. Chinese queries ("这份合同的付款条款是什么") look nothing like document passages ("4.2 付款方式"), making asymmetry especially important for Chinese enterprise content.

**Prevention:**
- At document ingestion: `text_type="document"` (DashScope SDK parameter)
- At query time: `text_type="query"`
- Enforce this through typed wrapper functions: `embed_document(text)` and `embed_query(text)` that set the parameter internally

**Detection:** Run a benchmark: embed 10 Q&A pairs using the same `text_type` for both, then again with correct asymmetric types. Compare top-1 retrieval hit rate. A drop above 5-10% indicates the mismatch is real.

**Phase:** Address in Phase 1 (embedding pipeline). Add a regression test in Phase 2 (query interface).

---

### Pitfall 4: Fixed-Size Chunking Without Overlap Destroys Answers That Span Chunk Boundaries

**What goes wrong:** Splitting documents with a fixed character/token count and zero overlap means that answers which span two adjacent chunks are never fully retrieved. One chunk contains the question context, the adjacent chunk contains the answer — but only one is returned by semantic search.

**Why it happens:** Developers apply `RecursiveCharacterTextSplitter` with default parameters and no overlap, or worse, split naively on newlines. Chinese text has no whitespace between words, so character-count splits frequently cut through sentences mid-clause.

**Consequences:** Retrievals return chunks that contain partial information. The LLM either hallucinates a complete answer or states it cannot find the information — even though the document contains it.

**Prevention:**
- Use `RecursiveCharacterTextSplitter` with `chunk_size=400–512` tokens and `chunk_overlap=50–80` tokens (10-20% overlap)
- For Chinese text, use token-length as the chunk metric, not character count — a single Chinese character is typically 1 token in Qwen tokenizers, but punctuation and mixed CJK/Latin text can vary
- Use sentence-boundary-aware splitting for Chinese: split on `。！？\n` before truncating at character/token limits
- Never use `\n\n` as the only separator for Chinese documents — paragraph breaks are inconsistent

**Detection:** Build a small test set of 10-20 questions whose answers span document sections. Measure exact-match retrieval. Any score below 60% on this set indicates chunking is inadequate.

**Phase:** Address in Phase 1 (document ingestion). Tune in Phase 2 after baseline retrieval metrics are established.

---

### Pitfall 5: PDF Tables and Multi-Column Layouts Produce Garbled Text

**What goes wrong:** PyMuPDF (fitz) and pdfplumber extract PDF text by position. Multi-column layouts cause text from the right column to be interleaved with text from the left column. Tables are extracted as flat text runs with no row/column structure. Enterprise Chinese documents (contracts, specs, financial reports) frequently use both.

**Why it happens:** PDF is a visual format — it describes where glyphs are placed on a page, not what the document structure is. Text extraction libraries reconstruct "reading order" heuristically, and these heuristics fail on complex layouts. Chinese documents add complexity because vertical text, half-width/full-width character mixing, and dense tables are common.

**Consequences:** Chunks contain scrambled text that is semantically incoherent. Embeddings of nonsense text produce vectors that match nothing at query time. The model either returns wrong information or hallucinates.

**Prevention:**
- Use `pymupdf4llm` (PyMuPDF's LLM-optimized wrapper) rather than raw `fitz` — it produces Markdown output with better structure preservation
- For scanned PDFs, add a detection step: if `page.get_text()` returns < 10 characters on a text-heavy page, treat it as scanned and invoke PaddleOCR (strong on Chinese)
- Log a warning for any chunk whose character-to-token ratio is anomalous (indicates garbled extraction)
- Store `source_file`, `page_number`, and `parse_method` as chunk metadata for debugging

**Detection:** Sample 5-10 extracted chunks per document type. Read them manually. Garbled table extractions are immediately obvious as strings of numbers with no separators.

**Phase:** Address in Phase 1 (document parsing). Do not proceed to embedding until parse quality is verified manually.

---

### Pitfall 6: LangGraph State Mutation Bypasses the Reducer and Causes Silent State Loss

**What goes wrong:** Directly mutating the state dict inside a node — e.g., `state["retrieved_docs"].append(doc)` or `state["context"] += " " + new_text` — bypasses LangGraph's reducer mechanism. The node's changes appear to work locally but are not reflected in subsequent nodes or in graph execution history.

**Why it happens:** Python dicts are mutable. LangGraph nodes receive the current state as input, but state updates must be returned as the node's output dict, not applied in-place. The mutation modifies the local reference but LangGraph's execution engine discards it.

**Consequences:** Downstream nodes receive stale state. In the RAG pipeline, the generator node may receive an empty `context` field even though the retriever node populated it. Debugging is difficult because adding print statements inside the node shows the mutation "worked."

**Prevention:**
- All nodes must return a dict of changed fields: `return {"retrieved_docs": new_docs, "context": formatted_context}`
- Never mutate `state` in-place — treat it as read-only input
- Use `Annotated[list, operator.add]` for fields that need accumulation (e.g., message history), not manual appending
- Use `add_messages` from `langgraph.graph.message` for conversation history fields
- Add a TypedDict state schema at graph definition time — type errors surface earlier

**Detection:** Add `print(state)` at the start of each node to observe what each node actually receives. If a field is empty when it should have been populated by a prior node, state mutation is the likely cause.

**Phase:** Address in Phase 2 (LangGraph workflow). Define the full state schema before writing any node logic.

---

### Pitfall 7: DashScope API 429 Rate Limit During Bulk Ingestion

**What goes wrong:** During document ingestion (embedding all chunks), and during evaluation dataset generation (calling the LLM for each Q&A pair), the system fires many API calls in rapid succession. DashScope enforces dual limits: RPM (requests per minute) and TPM (tokens per minute). Hitting either fires HTTP 429. New accounts have lower limits. The embedding API has a separate rate limit from the generation API.

**Why it happens:** Sequential ingestion of a 50-page document may generate 100+ chunk embedding requests. At 10 items per batch, that is 10+ API calls in seconds. Evaluation dataset generation calls the LLM once per chunk — a 200-chunk document generates 200 LLM calls.

**Consequences:** Ingestion fails partway through, leaving an incomplete index. If errors are not handled with retry logic, the user sees a generic error with no indication of which chunks were indexed.

**Prevention:**
- Implement exponential backoff with jitter for all DashScope API calls: `wait = (2 ** attempt) + random.uniform(0, 1)`, up to 5 retries
- Add a configurable `DASHSCOPE_REQUEST_DELAY_MS` environment variable (default: 100ms between embedding batches)
- For evaluation dataset generation, process chunks in batches with a delay, not in parallel
- Log every API call with model name, token count, attempt number, and latency
- Store ingestion progress persistently so partial ingestion can be resumed without re-embedding already-processed chunks

**Detection:** HTTP 429 responses in logs. Chunk count in ChromaDB after ingestion is lower than total chunk count from parsing.

**Phase:** Address in Phase 1 (ingestion) and Phase 3 (dataset generation). Build retry logic as a shared utility from the start.

---

## Moderate Pitfalls

---

### Pitfall 8: Scanned Chinese PDFs Return Empty Text Without OCR Fallback

**What goes wrong:** Many enterprise Chinese documents (scanned contracts, stamped approvals, physical-to-digital conversions) are image-based PDFs. PyMuPDF returns empty strings for these pages. Without a detection + OCR fallback, these documents are silently skipped or indexed as empty.

**Prevention:**
- Detect scanned pages: if `len(page.get_text().strip()) < 20` for a page with area > 0, flag as image-based
- For Chinese scanned PDFs, use PaddleOCR (best Chinese character recognition among open-source tools)
- Log a `WARN: scanned_page_detected, applying OCR` message per page so operators know OCR was invoked
- Store `parse_method: "ocr"` vs `"text"` in chunk metadata

**Phase:** Address in Phase 1 (document parsing). Treat as a must-have for Chinese enterprise document support.

---

### Pitfall 9: python-docx Loses Document Reading Order (Paragraphs, Tables, Images Interleaved)

**What goes wrong:** `python-docx`'s `.paragraphs` property returns all paragraphs including those inside tables as a flat list. Its `.tables` property is separate. If a Word document has text, then a table, then more text, iterating `.paragraphs` gives all paragraph text but skips over the table content's position in the document flow. The table's text appears (if accessed via `.tables`) but out of order relative to surrounding paragraphs.

**Prevention:**
- Iterate `doc.element.body` directly to process body elements in document order
- Use `docx2python` as an alternative — it extracts paragraphs, tables, and headers in document order into a structured format
- For tables: concatenate cell content with `" | "` separators to preserve row/column semantics in the extracted text

**Phase:** Address in Phase 1 (document parsing).

---

### Pitfall 10: "Lost in the Middle" Degrades Answers When Many Chunks Are Passed to the LLM

**What goes wrong:** When the RAG pipeline retrieves 5+ chunks and concatenates them into the LLM prompt, the model pays strong attention to the first and last chunks and weak attention to middle chunks. If the most relevant chunk happens to be in the middle of the context, the LLM ignores it and either hallucinates or says it cannot find the information.

**Why it happens:** Transformer attention with RoPE positional encoding creates a U-shaped attention pattern — positions near the start and end of the context receive disproportionately high attention. This is well-documented in research and confirmed at ICLR 2025 to persist in modern models.

**Prevention:**
- Limit retrieved chunks to 3–5 (not 10+) for the prompt context
- Order chunks by relevance score: highest score first, second-highest last, middle chunks in between (positions of maximum attention)
- Implement a reranking step (using a cross-encoder or asking the LLM to self-rank) before final context construction
- Use the `qwen-long` model's file-based context API for long documents instead of concatenating raw text into the prompt

**Phase:** Address in Phase 2 (query and generation). Can be deferred to Phase 2 refinement after baseline quality is measured.

---

### Pitfall 11: Auto-Generated Evaluation Q&A Pairs Contain Hallucinated Answers

**What goes wrong:** When using a Qwen model to generate question-answer pairs from document chunks for the evaluation dataset, the model sometimes "completes" answers based on its training data rather than the provided chunk text. The generated answer sounds plausible but is not grounded in the document. These hallucinated Q&A pairs corrupt the evaluation dataset and cause misleading benchmark results.

**Why it happens:** LLMs are trained to produce helpful, complete-sounding answers. When the chunk provides only partial information, the model fills gaps from its parametric knowledge rather than stating the limitation.

**Consequences:** Evaluation scores become unreliable. A model that retrieves correctly but the ground-truth answer is wrong (hallucinated at generation time) will score poorly even if it is functioning correctly.

**Prevention:**
- Include an explicit instruction in the generation prompt: "The answer MUST be a verbatim or near-verbatim quote from the provided text. Do not add any information not present in the text."
- After generation, run a verification step: use another LLM call to check if the answer is entailed by the source chunk
- Filter out any Q&A pair where the answer contains named entities, numbers, or dates not present in the source chunk
- Prefer generating questions that have clear, short factual answers from the chunk (avoids open-ended generation)
- Store `source_chunk_id` alongside each Q&A pair to enable post-hoc verification

**Detection:** Manually review 10% of generated Q&A pairs. Flag those where the answer contains information not obviously present in the paired chunk.

**Phase:** Address in Phase 3 (evaluation dataset generation).

---

### Pitfall 12: OpenAI-Compatible Interface vs. Native DashScope SDK Incompatibility

**What goes wrong:** DashScope supports two access methods: the native DashScope Python SDK and an OpenAI-compatible REST endpoint. They are not fully interchangeable. Some parameters (e.g., `text_type` for embeddings, certain `enable_search` flags for generation, file upload for `qwen-long`) are only available through the native DashScope SDK and are silently ignored or cause errors when sent via the OpenAI-compatible interface.

**Prevention:**
- Use the native `dashscope` Python SDK for all calls, not `openai` SDK pointed at DashScope's compatibility endpoint
- The outbound API that this system exposes (the OpenAI-compatible query interface) is about the contract with callers — internally, always call DashScope natively
- Test each API feature against official DashScope documentation, not OpenAI documentation

**Phase:** Address in Phase 1 (API client setup). Lock down the internal client layer before any feature work.

---

## Minor Pitfalls

---

### Pitfall 13: Mixed Simplified/Traditional Chinese and Half-Width/Full-Width Characters in Chunks

**What goes wrong:** Enterprise Chinese documents may contain a mix of Simplified Chinese, Traditional Chinese (in product names or quoted text), full-width Latin characters (`Ａ`, `１`), and half-width equivalents (`A`, `1`). Chunking and keyword search treat these as different characters. A query using `A` will not match a chunk containing `Ａ`.

**Prevention:**
- Normalize all text to Simplified Chinese + half-width characters after extraction using `unicodedata.normalize('NFKC', text)` — this converts full-width to half-width and normalizes Unicode compatibility characters
- Apply normalization at ingestion time (before chunking) and at query time (before embedding)

**Phase:** Address in Phase 1 (text preprocessing). A single utility function applied consistently.

---

### Pitfall 14: LangGraph `InvalidUpdateError` When Parallelizing Nodes Without List Reducers

**What goes wrong:** When two LangGraph nodes run in parallel (e.g., two retrieval nodes searching different collections) and both write to the same state field, LangGraph raises `InvalidUpdateError` unless the field is configured with a list-accumulating reducer.

**Prevention:**
- For any state field that can be written by multiple parallel nodes, annotate it: `retrieved_docs: Annotated[list, operator.add]`
- For fields written by only one node, no reducer annotation is needed
- Design the graph so parallel nodes write to separate state fields, then a merge node combines them

**Phase:** Address in Phase 2 (LangGraph workflow) if parallelism is introduced.

---

### Pitfall 15: Evaluation Dataset ZIP Structure Must Match Platform Schema Exactly

**What goes wrong:** The `数据集提交指南.md` specifies an exact ZIP structure: `evaluation_data.json` at the root plus an `attachments/` directory. Deviations — extra nesting, wrong filenames, missing fields in the JSON — cause silent rejection by the evaluation platform with no useful error message.

**Prevention:**
- Write a validation function that checks the ZIP contents and JSON schema before export
- Validate against the spec file at test time, not just at generation time
- Include the spec file path as a test fixture so it is always compared against the current version

**Phase:** Address in Phase 3 (dataset generation and export).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Phase 1: ChromaDB setup | Silent data loss on restart (Pitfall 1) | Set `IS_PERSISTENT=TRUE` + named volume before writing any ingestion code |
| Phase 1: DashScope embedding | Batch size limit of 10 (Pitfall 2) | Wrap all embedding calls in a batching utility from day one |
| Phase 1: DashScope embedding | text_type asymmetry (Pitfall 3) | Separate `embed_document()` and `embed_query()` functions |
| Phase 1: PDF parsing | Garbled tables/columns (Pitfall 5) | Use `pymupdf4llm`; manually verify extracted text before indexing |
| Phase 1: PDF parsing | Scanned pages silently empty (Pitfall 8) | Add OCR detection + PaddleOCR fallback |
| Phase 1: Word parsing | Reading order lost (Pitfall 9) | Use `docx2python` or iterate `doc.element.body` |
| Phase 1: Text preprocessing | Full-width character mismatch (Pitfall 13) | Apply NFKC normalization at ingest and query time |
| Phase 1: API client | DashScope vs. OpenAI SDK (Pitfall 12) | Use native `dashscope` SDK internally; never `openai` SDK for DashScope calls |
| Phase 1: Ingestion | Rate limits during bulk embed (Pitfall 7) | Exponential backoff utility before any large ingestion test |
| Phase 2: LangGraph | State mutation bypasses reducer (Pitfall 6) | Define full TypedDict schema before writing nodes; return dicts, never mutate |
| Phase 2: LangGraph | Parallel node write conflicts (Pitfall 14) | Use `Annotated[list, operator.add]` for shared fields |
| Phase 2: RAG quality | Lost in the middle (Pitfall 10) | Limit to 3-5 chunks; order by relevance at context construction |
| Phase 2: Chunking | Answers span chunk boundaries (Pitfall 4) | 10-20% overlap; sentence-boundary-aware splitting for Chinese |
| Phase 3: Dataset generation | Hallucinated Q&A answers (Pitfall 11) | Verbatim-grounding prompt instruction + post-hoc verification step |
| Phase 3: Export | ZIP structure mismatch (Pitfall 15) | Validate against spec before any export attempt |

---

## Sources

- ChromaDB persistence bug (silent data loss): https://github.com/chroma-core/chroma/issues/6654
- ChromaDB config.yaml path conflict: https://github.com/chroma-core/chroma/issues/4330
- DashScope embedding batch limit (10 items): https://www.alibabacloud.com/help/en/model-studio/embedding
- DashScope error codes and rate limits: https://www.alibabacloud.com/help/en/model-studio/error-code
- DashScope rate limit retry patterns: https://theneuralbase.com/qwen/qna/fix-qwen-rate-limit-error/
- Query-document embedding asymmetry: https://community.fabric.microsoft.com/t5/Data-Science-Community-Blog/When-Document-and-Query-Embeddings-Don-t-Match-A-Practical-Guide/ba-p/4993140
- RAG embedding asymmetry pitfall: https://medium.com/data-science-collective/rag-pitfall-embeddings-retrieve-similar-text-not-answers-d1afc48882e2
- Chunking strategy mistakes: https://weaviate.io/blog/chunking-strategies-for-rag
- Chunking benchmark (2026): https://blog.premai.io/rag-chunking-strategies-the-2026-benchmark-guide/
- Chinese tokenization pitfalls: https://digitalorientalist.com/2025/02/04/to-merge-or-not-to-merge-the-pitfalls-of-chinese-tokenization-in-general-purpose-llms/
- CJK text in AI pipelines: https://tonybaloney.github.io/posts/cjk-chinese-japanese-korean-llm-ai-best-practices.html
- PDF parsing benchmark: https://arxiv.org/abs/2410.09871
- pymupdf4llm for RAG: https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/
- OCR impact on RAG (ICCV 2025): https://openaccess.thecvf.com/content/ICCV2025/papers/Zhang_OCR_Hinders_RAG_Evaluating_the_Cascading_Impact_of_OCR_on_ICCV2025_paper.pdf
- python-docx reading order problem: https://github.com/kmrambo/Python-docx-Reading-paragraphs-tables-and-images-in-document-order-
- LangGraph state management best practices: https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025
- LangGraph state reducers guide: https://medium.com/data-science-collective/mastering-state-reducers-in-langgraph-a-complete-guide-b049af272817
- Lost in the middle — ICLR 2025: https://proceedings.iclr.cc/paper_files/paper/2025/file/ce186a37e63b37638ecd06dee6b9a355-Paper-Conference.pdf
- Solving lost in the middle: https://www.getmaxim.ai/articles/solving-the-lost-in-the-middle-problem-advanced-rag-techniques-for-long-context-llms/
- RAG evaluation dataset quality: https://www.getmaxim.ai/articles/rag-evaluation-a-complete-guide-for-2025/
- RAGAS hallucination detection issues: https://cleanlab.ai/blog/rag-tlm-hallucination-benchmarking/
- DashScope OpenAI compatibility limitations: https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope
- DashScope LlamaIndex embeddings (text_type usage): https://docs.llamaindex.ai/en/stable/examples/embeddings/dashscope_embeddings/
