"""FastAPI route handlers for OpenAI-compatible chat completions API."""
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    build_chat_response,
)
from src.rag.graph import rag_graph
from src.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Validate Bearer token against configured API key.

    Args:
        credentials: HTTP Authorization credentials with Bearer token.

    Returns:
        The validated API key string.

    Raises:
        HTTPException: 401 if token is invalid or missing.
    """
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


def estimate_tokens(text: str) -> int:
    """Rough token estimate for Chinese and English text.

    Uses heuristic: ~1.5 Chinese characters per token, ~4 English chars per token.
    This is suitable for usage reporting (not billing-accurate).

    Args:
        text: Input text to estimate.

    Returns:
        Estimated token count (minimum 1).
    """
    # Simple heuristic suitable for usage reporting
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return max(1, int(chinese_chars / 1.5) + int(other_chars / 4))


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    api_key: str = Depends(verify_api_key),
) -> ChatCompletionResponse:
    """OpenAI-compatible chat completions endpoint.

    Extracts user query from messages, invokes LangGraph RAG graph,
    returns response in 接口规范.md format.

    Args:
        request: Chat completion request with model and messages.
        api_key: Validated API key from Bearer token.

    Returns:
        ChatCompletionResponse matching OpenAI format.

    Raises:
        HTTPException: 400 if no user message found, 500 on RAG processing error.
    """
    # Extract the last user message as the query
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found in messages array")

    query = user_messages[-1].content

    # Invoke RAG graph
    try:
        result = rag_graph.invoke({"query": query})
    except Exception as e:
        logger.error(f"RAG graph invocation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")

    generation = result.get("generation", "")

    # Estimate token usage
    prompt_text = " ".join(m.content for m in request.messages)
    prompt_tokens = estimate_tokens(prompt_text)
    completion_tokens = estimate_tokens(generation)

    return build_chat_response(
        content=generation,
        model=request.model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
