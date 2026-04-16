---
status: resolved
trigger: "POST /dataset/generate returns 404 with {detail: No Q&A pairs could be generated from indexed documents} instead of HTTP 200 + ZIP file"
created: 2026-04-16T00:00:00Z
updated: 2026-04-16T00:00:01Z
---

## Current Focus

hypothesis: CONFIRMED — generator.py get_llm() uses wrong parameter name (dashscope_api_key instead of api_key) and missing CN endpoint (api_base). LLM calls fail silently per-chunk, producing empty test_cases list, which triggers the 404.
test: confirmed by code reading and ChatQwen parameter inspection
expecting: fix get_llm() in generator.py to match working pattern in nodes.py
next_action: await human verification that POST /dataset/generate returns 200 + ZIP

## Symptoms

expected: POST /dataset/generate returns HTTP 200 with Content-Type application/zip and a valid ZIP body containing evaluation_data.json
actual: Returns HTTP 404 with body {"detail": "No Q&A pairs could be generated from indexed documents"}
errors: 404 Not Found — {"detail": "No Q&A pairs could be generated from indexed documents"}
reproduction: Call POST /dataset/generate when the app is running (documents may or may not be indexed)
started: Discovered during UAT for Phase 3 (dataset-generation). Phase was just implemented.

## Eliminated

- hypothesis: ChromaDB returns no documents (404 from empty collection)
  evidence: The error message is "No Q&A pairs could be generated" (line 67 of dataset.py) not "No documents indexed" (line 52). Different 404 branch — documents ARE present.
  timestamp: 2026-04-16T00:00:01Z

- hypothesis: ChromaDB .get() default include doesn't return document text
  evidence: Inspected ChromaDB Collection.get() signature — default includes=['metadatas','documents']. Documents are returned.
  timestamp: 2026-04-16T00:00:01Z

- hypothesis: async/sync mismatch causes LLM call failures
  evidence: Not applicable — llm.invoke() is synchronous and works fine from sync context inside async handler.
  timestamp: 2026-04-16T00:00:01Z

## Evidence

- timestamp: 2026-04-16T00:00:01Z
  checked: src/dataset/generator.py get_llm() at line 65-68
  found: Uses dashscope_api_key=settings.DASHSCOPE_API_KEY (wrong param name) and no api_base
  implication: ChatQwen moves dashscope_api_key to model_kwargs (ignored for auth), uses default (non-CN) endpoint

- timestamp: 2026-04-16T00:00:01Z
  checked: ChatQwen parameter inspection (python runtime)
  found: WARNING - dashscope_api_key is not default parameter, transferred to model_kwargs. ChatQwen's correct param is api_key=.
  implication: get_llm() uses env var for auth key (if set) but wrong endpoint, causing API call failures

- timestamp: 2026-04-16T00:00:01Z
  checked: src/rag/nodes.py grade_documents and generate functions (working code)
  found: Uses api_key=settings.DASHSCOPE_API_KEY AND api_base=_DASHSCOPE_CN_BASE — the correct pattern
  implication: The same fix applied in commit "fix: ChatQwen use CN endpoint and explicit api_key from settings" was NOT applied to generator.py

- timestamp: 2026-04-16T00:00:01Z
  checked: generate_qa_from_chunks exception handling (lines 175-177)
  found: Each per-chunk LLM exception is caught, logged, and continued — silently producing zero test_cases
  implication: LLM failures are hidden; the route only sees an empty list and raises 404 instead of 500

- timestamp: 2026-04-16T00:00:01Z
  checked: dataset.py route handler lines 64-69
  found: Raises HTTPException 404 when test_cases is empty — wrong status code for a server-side generation failure
  implication: 404 (Not Found) is semantically incorrect here; should be 500 (Internal Server Error)

## Resolution

root_cause: generator.py get_llm() uses wrong ChatQwen parameter name (dashscope_api_key instead of api_key) and is missing the CN DashScope endpoint (api_base). This causes silent LLM call failures for each chunk, resulting in empty test_cases. The route then raises HTTP 404 with a misleading message. The fix applied to nodes.py in a previous commit was not applied to generator.py.
fix: (1) Fix get_llm() to use api_key= and api_base= matching the pattern in nodes.py. (2) Change the empty-test_cases HTTPException from 404 to 500 since it's a server-side generation failure.
verification: Human confirmed — POST /dataset/generate returns HTTP 200 + valid ZIP
files_changed: [src/dataset/generator.py, src/api/routes/dataset.py]
