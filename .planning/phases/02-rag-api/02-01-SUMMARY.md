---
phase: 02-rag-api
plan: 01
name: Build LangGraph RAG Orchestration Graph
duration: 20 minutes
deviations: 0
commit_count: 3
tags: [langgraph, rag, dashscope, qwen]
---

# Phase 02 Plan 01: Build LangGraph RAG Orchestration Graph

## One-Liner Summary
LangGraph RAG graph implementing retrieve-grade-generate flow with ChatQwen (qwen-plus) for relevance grading and answer generation, using ChromaDB for retrieval.

## Key Decisions

1. **Linear graph flow over conditional edges**: The grade_documents node already sets `has_relevant_docs` flag, and generate node checks this to return FALLBACK_RESPONSE. This simplifies the graph structure while correctly handling the no-relevant-docs case.

2. **ChatQwen from langchain-qwq**: Used as mandated by CLAUDE.md, NOT the deprecated ChatTongyi from langchain-community.

3. **Grading uses temperature=0**: Deterministic relevance scoring; generation uses temperature=0.3 for natural Chinese responses.

## What Was Built

### Files Created

| File | Purpose | Key Exports |
|------|---------|-------------|
| `src/rag/__init__.py` | Package init | (empty) |
| `src/rag/state.py` | RAG state schema | `RAGState` TypedDict |
| `src/rag/prompts.py` | Chinese prompt templates | `GRADER_*`, `GENERATOR_*`, `FALLBACK_RESPONSE` |
| `src/rag/nodes.py` | Node functions | `retrieve`, `grade_documents`, `generate` |
| `src/rag/graph.py` | Compiled graph | `build_rag_graph()`, `rag_graph` |
| `tests/test_rag_graph.py` | Unit tests | 4 test functions |

### RAGState Schema

```python
class RAGState(TypedDict):
    query: str                    # User question
    documents: list[Document]     # Raw retrieved chunks
    filtered_documents: list[Document]  # After grading
    generation: str               # Final answer
    has_relevant_docs: bool       # Grading result flag
```

### Graph Flow

```
START -> retrieve -> grade_documents -> generate -> END
```

- **retrieve**: Queries ChromaDB using `as_retriever(search_kwargs={"k": 4})`
- **grade_documents**: Calls ChatQwen for each document, keeps only "yes" responses
- **generate**: Returns FALLBACK_RESPONSE if no docs, else generates Chinese answer

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 2316851 | Define RAG state schema and prompt templates |
| 2 | 38bc93f | Implement RAG node functions (retrieve, grade, generate) |
| 3 | 0b51d3f | Build and compile LangGraph RAG StateGraph |

## Threat Model Compliance

All dispositions from plan's threat model have been addressed:

| Threat ID | Status | Implementation |
|-----------|--------|----------------|
| T-02-01 (Injection via prompts) | Mitigated | Uses structured prompt templates with `{query}` placeholder, not f-string concatenation |
| T-02-02 (Document content injection) | Mitigated | Grading filters chunks; system prompt instructs "only answer based on documents" |
| T-02-03 (Information disclosure) | Mitigated | Relevance grading + FALLBACK_RESPONSE when no relevant docs |
| T-02-04 (DoS via multiple LLM calls) | Accepted | 5 LLM calls per query (4 grading + 1 generation) acceptable for internal MVP |
| T-02-05 (API key exposure) | Mitigated | API key loaded from env var, not logged or exposed in errors |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

No intentional stubs. The graph is fully functional but requires:
- ChromaDB with populated documents for meaningful retrieval
- DASHSCOPE_API_KEY for LLM calls

## Self-Check: PASSED

- [x] src/rag/__init__.py exists
- [x] src/rag/state.py contains RAGState TypedDict with 5 required fields
- [x] src/rag/prompts.py contains all prompt constants
- [x] src/rag/nodes.py contains 3 node functions with correct signatures
- [x] src/rag/graph.py contains StateGraph and exports rag_graph
- [x] tests/test_rag_graph.py exists with 4 test functions
- [x] All commit hashes verified in git log

## Next Steps

This RAG graph will be invoked by the FastAPI endpoint (Plan 02-02). The graph assumes:
- `src.config.settings.RETRIEVAL_TOP_K` exists (default 4)
- `src.vectorstore.get_vectorstore()` returns a configured Chroma instance
- `DASHSCOPE_API_KEY` environment variable is set

---
*Summary created: 2026-04-16*
