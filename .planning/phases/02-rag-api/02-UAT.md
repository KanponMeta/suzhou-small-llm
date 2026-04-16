---
status: testing
phase: 02-rag-api
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md]
started: 2026-04-16T07:20:32Z
updated: 2026-04-16T10:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server. Start the application from scratch: `uvicorn src.main:app --host 0.0.0.0 --port 8000`. Server boots without errors, no import failures, and the process stays alive. (A GET http://localhost:8000/ or http://localhost:8000/health should return a response — even a 404 is fine as long as the server is running.)
result: pass

### 2. Authentication - No Token Returns 401
expected: A POST to /v1/chat/completions with no Authorization header returns HTTP 401. Example: `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"qwen-plus","messages":[{"role":"user","content":"test"}]}'` → should print 403 or 401.
result: pass
note: Initial failure was app/src split (app.main:app running instead of src.main:app) — fixed by quick task 260416-pmt

### 3. Request Validation - Malformed Body Returns 422
expected: A POST to /v1/chat/completions with a missing required field (e.g., no `messages`) returns HTTP 422 Unprocessable Entity. Example: `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/chat/completions -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{"model":"qwen-plus"}'` → should print 422.
result: pass

### 4. Response Schema Compliance
expected: A valid POST to /v1/chat/completions (with correct auth and messages) returns JSON with ALL required fields: `object` = "chat.completion", `choices` array with `choices[0].message.role` = "assistant", `choices[0].message.content` as a string, `choices[0].finish_reason` = "stop", `usage` with `prompt_tokens`, `completion_tokens`, `total_tokens`, `created` as unix timestamp, `model` echoing back the requested model, and `id` starting with "chatcmpl-".
result: issue
reported: "POST /v1/chat/completions with valid auth and body returns {\"detail\":\"Not Found\"}"
severity: blocker

### 5. RAG Fallback Response
expected: When querying about a topic clearly unrelated to any uploaded documents (e.g., "火星上的天气如何？" with an empty or mismatched knowledge base), the response still returns HTTP 200 with a graceful Chinese fallback message in `choices[0].message.content` (not a 500 error or empty string).
result: blocked
blocked_by: server
reason: "Same root cause as Test 4 — /v1/chat/completions returns 404 for valid requests"

### 6. Chinese Answer from Knowledge Base
expected: After uploading a document containing specific Chinese content, a query about that content returns an answer in `choices[0].message.content` that is in Chinese and references or paraphrases the document content — not just a generic fallback. This confirms the retrieve→grade→generate flow is working end-to-end.
result: blocked
blocked_by: server
reason: "Same root cause as Test 4 — /v1/chat/completions returns 404 for valid requests"

## Summary

total: 6
passed: 3
issues: 1
pending: 0
skipped: 0
blocked: 2

## Gaps

- truth: "POST /v1/chat/completions with valid auth and full body returns OpenAI-compatible JSON (object, choices, usage, id)"
  status: failed
  reason: "User reported: POST with valid auth and body returns {\"detail\":\"Not Found\"}"
  severity: blocker
  test: 4
  artifacts: []
  missing: []
