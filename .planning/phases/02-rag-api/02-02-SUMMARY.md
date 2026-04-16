---
phase: 02-rag-api
plan: 02
name: Build FastAPI OpenAI-Compatible Chat Endpoint
duration: 15 minutes
deviations: 0
commit_count: 2
tags: [fastapi, pydantic, api, openai-compatible]
dependency_graph:
  requires:
    - "02-01: RAG graph must be compiled and export rag_graph"
    - "src/config.py: settings.API_KEY for Bearer token validation"
  provides:
    - "POST /v1/chat/completions endpoint"
    - "OpenAI-compatible request/response schemas"
  affects:
    - "src/main.py: adds chat router to FastAPI app"
tech_stack:
  added:
    - fastapi 0.135.3
    - pydantic 2.13.1
  patterns:
    - "HTTPBearer dependency for API key validation"
    - "Pydantic v2 models for OpenAI-compatible schemas"
key_files:
  created:
    - src/api/__init__.py
    - src/api/schemas.py
    - src/api/chat.py
    - src/main.py
    - tests/test_chat_endpoint.py
  modified: []
decisions:
  - "Token estimation uses heuristic (~1.5 Chinese chars/token, ~4 English chars/token) suitable for usage reporting, not billing-accurate"
  - "Last user message extracted as query (supports multi-turn with system context)"
  - "RAG graph errors caught and logged, generic 500 returned to client (security)"
---

# Phase 02 Plan 02: Build FastAPI OpenAI-Compatible Chat Endpoint

## One-Liner Summary

FastAPI endpoint exposing RAG graph as OpenAI-compatible `/v1/chat/completions` API with Pydantic v2 schemas matching 接口规范.md exactly, Bearer token authentication, and token usage estimation.

## Key Decisions

1. **Token estimation heuristic**: Uses ~1.5 Chinese characters per token and ~4 English characters per token. This is suitable for usage reporting but not billing-accurate. Actual token counts would require tiktoken or model-specific tokenizers.

2. **Last user message extraction**: The endpoint extracts the last message with `role="user"` as the query. This supports multi-turn conversations where earlier system/user context is present but only the final user message is passed to the RAG graph.

3. **Generic error responses**: RAG graph invocation errors are caught and logged server-side, but a generic "Internal processing error" (500) is returned to clients. This prevents information disclosure about internal components.

## What Was Built

### Files Created

| File | Purpose | Key Exports |
|------|---------|-------------|
| `src/api/__init__.py` | API package init | (empty) |
| `src/api/schemas.py` | Pydantic v2 schemas | `ChatCompletionRequest`, `ChatCompletionResponse`, `build_chat_response()` |
| `src/api/chat.py` | Chat router with auth | `router`, `verify_api_key()`, `estimate_tokens()`, `chat_completions()` |
| `src/main.py` | FastAPI app | `app` with chat_router included |
| `tests/test_chat_endpoint.py` | API tests | 6 test functions for schema compliance |

### Schema Compliance (接口规范.md)

**Request (section 2.1.1-2.1.2):**
```python
ChatCompletionRequest
  model: str (required)
  messages: list[ChatMessage] (required)
    ChatMessage
      role: str ("system" | "user" | "assistant")
      content: str
```

**Response (section 2.1.4-2.1.5):**
```python
ChatCompletionResponse
  choices: list[Choice]
    Choice
      message: ChoiceMessage (role="assistant", content=str)
      finish_reason: str = "stop"
      index: int = 0
      logprobs: Optional[object] = None
  object: str = "chat.completion"
  usage: Usage
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: PromptTokensDetails (cached_tokens=0)
  created: int (unix timestamp)
  system_fingerprint: Optional[str] = None
  model: str
  id: str ("chatcmpl-{uuid}")
```

### API Endpoint

**POST /v1/chat/completions**

- **Auth**: HTTP Bearer token (Authorization: Bearer $API_KEY)
- **Request Body**: `{model: str, messages: [{role: str, content: str}]}`
- **Response**: OpenAI-compatible JSON with `choices[0].message.content` containing RAG-generated Chinese answer
- **Error Codes**:
  - 400: No user message in messages array
  - 401: Invalid or missing Bearer token
  - 422: Malformed request body (Pydantic validation)
  - 500: RAG graph processing error

### Graph Invocation

```python
# From src/api/chat.py chat_completions()
result = rag_graph.invoke({"query": query})
generation = result.get("generation", "")  # Chinese answer from RAG
```

The RAG graph (from Plan 02-01) handles:
1. Document retrieval from ChromaDB
2. Relevance grading with qwen-plus
3. Answer generation or FALLBACK_RESPONSE

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 68679bd | Define Pydantic v2 request/response schemas matching 接口规范.md |
| 2 | de147b5 | Implement /v1/chat/completions endpoint with auth and RAG graph invocation |

## Threat Model Compliance

All dispositions from plan's threat model have been addressed:

| Threat ID | Status | Implementation |
|-----------|--------|----------------|
| T-02-06 (Spoofing) | Mitigated | Bearer token authentication via HTTPBearer dependency. `verify_api_key()` compares token against `settings.API_KEY`. Returns 401 for missing/invalid tokens. Per 接口规范.md section 1. |
| T-02-07 (Tampering) | Mitigated | Pydantic v2 model validates request body strictly. Only `model` (str) and `messages` (list) accepted. Invalid types return 422 automatically. |
| T-02-08 (Injection) | Mitigated | User content passed through structured prompt templates as data, not system instructions. System prompts hardcoded in prompts.py. |
| T-02-09 (Info Disclosure) | Mitigated | Internal exceptions caught with generic "Internal processing error" message. Stack traces and DashScope API details not exposed to client. Python logging captures details server-side only. |
| T-02-10 (DoS) | Accepted | Each request triggers 5 LLM API calls. Acceptable for single-tenant internal deployment. Rate limiting can be added via middleware in future phase. |
| T-02-11 (Info Disclosure/API key) | Mitigated | API key loaded from environment variable via python-dotenv, never hardcoded. Docker Compose uses env_file directive. Key not included in error messages, logs, or API responses. |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

No intentional stubs. The endpoint is fully functional but requires:
- Valid `DASHSCOPE_API_KEY` for RAG graph LLM calls
- Populated ChromaDB collection for meaningful retrieval
- Docker Compose environment with proper env_file configuration

## Verification Steps

To verify the implementation:

1. **Schema validation** (can run without dependencies):
   ```bash
   cd /home/developer/.kanpon/code/suzhou-small-llm
   python -c "
   from src.api.schemas import ChatCompletionRequest, ChatCompletionResponse, build_chat_response
   req = ChatCompletionRequest(model='test', messages=[{'role': 'user', 'content': 'hi'}])
   resp = build_chat_response(content='hello', model='test', prompt_tokens=10, completion_tokens=5)
   d = resp.model_dump()
   assert d['object'] == 'chat.completion'
   assert d['choices'][0]['message']['role'] == 'assistant'
   assert d['usage']['total_tokens'] == 15
   print('schema validation ok')
   "
   ```

2. **Run tests** (requires dependencies):
   ```bash
   pip install -r requirements.txt
   python -m pytest tests/test_chat_endpoint.py -v
   ```

3. **Manual API test** (requires running server):
   ```bash
   # Start server
   cd /home/developer/.kanpon/code/suzhou-small-llm
   uvicorn src.main:app --host 0.0.0.0 --port 8000

   # Test endpoint
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Authorization: Bearer test-api-key" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "qwen-plus",
       "messages": [{"role": "user", "content": "什么是知识库？"}]
     }'
   ```

## Self-Check: PASSED

- [x] src/api/__init__.py exists
- [x] src/api/schemas.py contains ChatCompletionRequest with model (str) and messages (list)
- [x] src/api/schemas.py contains ChatCompletionResponse with all required fields
- [x] src/api/schemas.py contains Usage with prompt_tokens_details
- [x] src/api/schemas.py contains build_chat_response helper
- [x] src/api/chat.py contains router = APIRouter()
- [x] src/api/chat.py contains @router.post("/v1/chat/completions")
- [x] src/api/chat.py contains verify_api_key with HTTPBearer dependency
- [x] src/api/chat.py contains rag_graph.invoke calling RAG graph
- [x] src/main.py contains app.include_router for chat_router
- [x] tests/test_chat_endpoint.py contains 6 test functions
- [x] All commit hashes verified in git log

## Next Steps

This endpoint will be used by:
- External systems calling the knowledge base API
- Evaluation platform testing RAG responses
- Phase 3 dataset generation (will use this API for Q&A pair validation)

Dependencies for full operation:
- Running ChromaDB with populated documents
- Valid DASHSCOPE_API_KEY in environment
- Docker Compose configuration (from Phase 1)

---
*Summary created: 2026-04-16*
