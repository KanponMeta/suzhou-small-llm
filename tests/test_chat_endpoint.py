"""Tests for /v1/chat/completions endpoint schema compliance."""
import pytest


def test_request_schema_accepts_minimal_body():
    """ChatCompletionRequest only requires model and messages."""
    from src.api.schemas import ChatCompletionRequest
    req = ChatCompletionRequest(
        model="qwen-plus",
        messages=[{"role": "user", "content": "什么是知识库？"}],
    )
    assert req.model == "qwen-plus"
    assert len(req.messages) == 1
    assert req.messages[0].role == "user"


def test_request_schema_accepts_system_and_user():
    """ChatCompletionRequest accepts system + user messages."""
    from src.api.schemas import ChatCompletionRequest
    req = ChatCompletionRequest(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "你是谁？"},
        ],
    )
    assert len(req.messages) == 2


def test_response_schema_matches_spec():
    """ChatCompletionResponse matches 接口规范.md section 2.1.4."""
    from src.api.schemas import build_chat_response
    resp = build_chat_response(
        content="我是一款知识库助手。",
        model="qwen-plus",
        prompt_tokens=100,
        completion_tokens=20,
    )
    d = resp.model_dump()

    # Top-level fields per 接口规范.md
    assert d["object"] == "chat.completion"
    assert isinstance(d["created"], int)
    assert d["model"] == "qwen-plus"
    assert d["id"].startswith("chatcmpl-")
    assert d["system_fingerprint"] is None

    # choices array
    assert len(d["choices"]) == 1
    choice = d["choices"][0]
    assert choice["message"]["role"] == "assistant"
    assert choice["message"]["content"] == "我是一款知识库助手。"
    assert choice["finish_reason"] == "stop"
    assert choice["index"] == 0
    assert choice["logprobs"] is None

    # usage object
    assert d["usage"]["prompt_tokens"] == 100
    assert d["usage"]["completion_tokens"] == 20
    assert d["usage"]["total_tokens"] == 120
    assert d["usage"]["prompt_tokens_details"]["cached_tokens"] == 0


def test_response_json_serializable():
    """Response can be serialized to JSON (FastAPI requirement)."""
    import json
    from src.api.schemas import build_chat_response
    resp = build_chat_response(content="测试", model="test", prompt_tokens=1, completion_tokens=1)
    json_str = resp.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["choices"][0]["message"]["content"] == "测试"


def test_token_estimation():
    """Token estimator handles Chinese and English text."""
    from src.api.chat import estimate_tokens
    # Chinese text
    chinese_tokens = estimate_tokens("你好世界测试一下")
    assert chinese_tokens > 0
    # English text
    english_tokens = estimate_tokens("hello world test")
    assert english_tokens > 0
    # Empty string
    assert estimate_tokens("") >= 1


def test_verify_api_key_rejects_invalid():
    """verify_api_key raises 401 for wrong token."""
    from unittest.mock import MagicMock
    from fastapi import HTTPException
    from src.api.chat import verify_api_key
    creds = MagicMock()
    creds.credentials = "wrong-key-12345"
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(creds)
    assert exc_info.value.status_code == 401
