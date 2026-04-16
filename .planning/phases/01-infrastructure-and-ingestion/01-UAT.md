---
status: complete
phase: 01-infrastructure-and-ingestion
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md]
started: 2026-04-16T07:20:12Z
updated: 2026-04-16T08:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch with: docker compose up --build. Both services (app + chromadb) should start without errors. The app container should pass its healthcheck and a GET http://localhost:8080/ (or configured port) should return a live response.
result: pass
note: "Initially failed (chromadb unhealthy — python3/curl absent, /api/v1 path stale). Fixed inline: healthcheck now uses bash /dev/tcp against /api/v2/heartbeat. Confirmed working after fix."

### 2. Upload a Document
expected: POST /documents/upload with a PDF, Markdown, or TXT file attached as multipart form data. Response is JSON with doc_id (UUID string) and chunk_count (integer > 0). The file is parsed, split into chunks, embedded via DashScope, and stored in ChromaDB.
result: pass

### 3. Health Check Endpoint
expected: GET /health returns HTTP 200 with JSON body containing status ("ok" or "degraded") and a services dict with chromadb and dashscope entries. When both services are reachable and the API key is configured, status should be "ok".
result: pass

### 4. List Indexed Documents
expected: GET /documents returns HTTP 200 with JSON containing total count and a list of documents. Each document has doc_id, filename, file_type, and chunk_count. Documents uploaded via /documents/upload should appear here.
result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
