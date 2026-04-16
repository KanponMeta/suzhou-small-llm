---
status: complete
phase: 03-dataset-generation
source: 03-01-SUMMARY.md, 03-02-SUMMARY.md
started: 2026-04-16T07:20:35Z
updated: 2026-04-16T13:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server. Start the application from scratch with `uvicorn src.main:app --reload` (or `docker compose up`). Server boots without errors, and GET /health (or root `/`) returns a live response.
result: pass

### 2. Dataset Generate Endpoint Exists
expected: POST /dataset/generate returns HTTP 200 with Content-Type `application/zip` (or `application/octet-stream`). The response body is a valid ZIP file, not an error message.
result: pass
note: "Initially 404 due to wrong ChatQwen params in generator.py — fixed during UAT (see .planning/debug/resolved/dataset-generate-404.md)"

### 3. ZIP Package Structure
expected: Download the ZIP from /dataset/generate. Unpack it. You should see `evaluation_data.json` at the root of the archive AND an `attachments/` directory (even if empty).
result: pass

### 4. evaluation_data.json Schema
expected: Open `evaluation_data.json` from the ZIP. It should contain a `test_cases` array. Each entry should have: `task_type: "chat:text"`, `answer_type: "free_form"`, a non-empty `user_prompt`, and a non-empty `correct_answer`. Internal fields `source_document` and `source_chunk_id` should NOT appear in the JSON.
result: pass

### 5. Chinese Character Encoding
expected: Open `evaluation_data.json` with any text editor. Chinese characters should display as readable text (e.g., `"用户查询如何申请"`) — NOT as escaped unicode sequences like `\u7528\u6237`. The file should be valid UTF-8.
result: pass

### 6. Q&A Grounding in Document Content
expected: The generated questions and answers should clearly relate to documents in the knowledge base — not generic questions the model invented from training data. For example, if you uploaded a document about company leave policy, questions should reference that specific policy content.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
