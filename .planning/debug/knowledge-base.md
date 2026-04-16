# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## dataset-generate-404 — ChatQwen wrong param name causes silent LLM failures and spurious 404
- **Date:** 2026-04-16
- **Error patterns:** 404, No Q&A pairs could be generated, dataset generate, ChatQwen, dashscope_api_key, api_key, api_base, test_cases, generator, empty
- **Root cause:** generator.py get_llm() used wrong ChatQwen parameter name (dashscope_api_key instead of api_key) and omitted the CN DashScope endpoint (api_base). Each per-chunk LLM call failed silently (exception caught and swallowed), producing an empty test_cases list. The route then raised HTTP 404 with a misleading "No Q&A pairs" message.
- **Fix:** (1) Changed get_llm() to use api_key= and api_base= matching the already-working pattern in nodes.py. (2) Changed the empty-test_cases HTTPException from 404 to 500 since the failure is server-side, not a missing resource.
- **Files changed:** src/dataset/generator.py, src/api/routes/dataset.py
---
