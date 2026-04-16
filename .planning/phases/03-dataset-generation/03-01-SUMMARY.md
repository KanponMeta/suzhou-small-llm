---
phase: 03-dataset-generation
plan: 01
subsystem: dataset-generation
tags:
  - qa-generation
  - evaluation-dataset
  - langchain-qwq
  - test-case
dependency_graph:
  requires: []
  provides:
    - src/dataset/models.py: TestCase, EvaluationData
    - src/dataset/generator.py: generate_qa_from_chunks, generate_qa_pairs
  affects:
    - src/config.py (added extra="ignore" for pydantic)
key_files:
  created:
    - src/dataset/__init__.py
    - src/dataset/models.py
    - src/dataset/generator.py
    - tests/test_dataset_generator.py
  modified:
    - src/config.py
tech_stack:
  added:
    - pydantic BaseModel with Literal types
    - langchain-qwq ChatQwen (qwen-long)
    - chromadb document retrieval
  patterns:
    - TDD (RED-GREEN-REFACTOR)
    - Mock-based testing (no real API calls)
    - Grounding enforcement via prompt engineering
decisions:
  - Use pydantic Field(exclude=True) for source_document and source_chunk_id to exclude from JSON export
  - Minimum chunk length of 50 characters to ensure sufficient content for Q&A generation
  - Use qwen-long model for long-document processing (per CLAUDE.md guidance)
metrics:
  duration: 2 minutes
  completed_date: "2026-04-16"
  tasks: 2
  files: 5
  tests: 12
---

# Phase 03 Plan 01: Q&A Pair Generation Engine Summary

## Overview

Built the core Q&A pair generation engine that reads document chunks from ChromaDB and uses ChatQwen (qwen-long) to produce grounded evaluation Q&A pairs in the exact `chat:text` / `free_form` schema required by `数据集提交指南.md`.

## Implementation Details

### Pydantic Models (src/dataset/models.py)

- **TestCase**: Single evaluation Q&A test case with 7 serialized fields (id, task_type, category, user_prompt, answer_type, options, correct_answer) and 2 internal-only fields (source_document, source_chunk_id) excluded from JSON export
- **EvaluationData**: Container wrapping list of TestCase objects under `test_cases` key
- Enforces Literal types: task_type="chat:text", answer_type="free_form"

### Q&A Generator (src/dataset/generator.py)

- **get_llm()**: Returns ChatQwen instance with `qwen-long` model (optimized for long-context document processing)
- **generate_qa_from_chunks()**: Takes chunks, source_name, category; returns list[TestCase]
  - Builds prompt with grounding instruction: "仅基于以下文档内容生成问答对"
  - Skips chunks < 50 characters
  - Handles LLM JSON parsing errors gracefully
- **generate_qa_pairs()**: Orchestrates retrieval from ChromaDB, groups by source document, generates Q&A pairs
- Uses `vectorstore._collection.get()` to retrieve all documents with metadata

### Tests (tests/test_dataset_generator.py)

12 passing tests covering:
- Model validation (required fields, Literal enforcement, serialization keys)
- Q&A generation (TestCase output, grounding, unique IDs, category population)
- Integration with mocked ChromaDB

## Deviation from Plan

### Auto-Fixed Configuration Issue

**Issue:** src/config.py used deprecated class-based Config for Pydantic v2

**Fix:** Migrated to SettingsConfigDict with `extra="ignore"` to allow .env file fields that don't match model (LLM_MODEL_NAME vs GENERATION_MODEL, etc.)

**Files modified:** src/config.py

## Verification

```
python -m pytest tests/test_dataset_generator.py -x -v
# 12 passed in 0.74s
```

All acceptance criteria met:
- task_type is always "chat:text"
- answer_type is always "free_form"
- correct_answer derived from document chunks (not model knowledge)
- Grounding instruction present in prompt
- Tests use mocked ChatQwen (no real API calls)

## Known Stubs

None - all core functionality implemented and tested.

## Threat Flags

None - this component reads from existing ChromaDB and generates dataset output (no new attack surface).
