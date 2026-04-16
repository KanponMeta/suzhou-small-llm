"""Pydantic v2 request/response schemas for OpenAI-compatible API.

Matches 接口规范.md sections 2.1.1 through 2.1.5 exactly.
"""
from pydantic import BaseModel, Field
from typing import Optional
import time
import uuid


class ChatMessage(BaseModel):
    """Single message in the chat conversation."""
    role: str  # "system", "user", or "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    """Request body for POST /v1/chat/completions.

    Per 接口规范.md section 2.1.2:
    Only `model` (String, required) and `messages` (Array, required) are required.
    The spec explicitly states "您的 API 接口不应该有额外的必选参数".
    """
    model: str
    messages: list[ChatMessage]


class ChoiceMessage(BaseModel):
    """Message content within a Choice."""
    role: str = "assistant"
    content: str


class Choice(BaseModel):
    """Single choice in the completion response."""
    message: ChoiceMessage
    finish_reason: str = "stop"
    index: int = 0
    logprobs: Optional[object] = None


class PromptTokensDetails(BaseModel):
    """Details about prompt token usage."""
    cached_tokens: int = 0


class Usage(BaseModel):
    """Token usage statistics for the request."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: PromptTokensDetails = Field(default_factory=PromptTokensDetails)


class ChatCompletionResponse(BaseModel):
    """Response body for POST /v1/chat/completions.

    Matches 接口规范.md section 2.1.4 exactly:
    - choices: Array of Choice objects
    - object: Literal "chat.completion"
    - usage: Token usage object
    - created: Unix timestamp
    - system_fingerprint: null
    - model: Model identifier
    - id: Unique completion ID starting with "chatcmpl-"
    """
    choices: list[Choice]
    object: str = "chat.completion"
    usage: Usage
    created: int = Field(default_factory=lambda: int(time.time()))
    system_fingerprint: Optional[str] = None
    model: str
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")


def build_chat_response(
    content: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> ChatCompletionResponse:
    """Build a ChatCompletionResponse from generated content.

    Args:
        content: The generated text content (Chinese answer from RAG graph).
        model: The model identifier used for generation.
        prompt_tokens: Estimated number of prompt tokens.
        completion_tokens: Estimated number of completion tokens.

    Returns:
        ChatCompletionResponse matching 接口规范.md format.
    """
    return ChatCompletionResponse(
        choices=[Choice(message=ChoiceMessage(content=content))],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
        model=model,
    )
