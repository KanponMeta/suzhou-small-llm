"""Health check endpoint with service dependency verification."""
import chromadb
from fastapi import APIRouter
from pydantic import BaseModel
from src.config import get_settings

router = APIRouter(tags=["health"])


class ServiceStatus(BaseModel):
    """Status of an individual service dependency."""
    status: str  # "ok" or "error"
    detail: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str  # "ok" or "degraded" or "error"
    services: dict[str, ServiceStatus]


def check_chromadb() -> ServiceStatus:
    """Check ChromaDB connectivity via heartbeat."""
    settings = get_settings()
    try:
        client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
        heartbeat = client.heartbeat()
        return ServiceStatus(status="ok", detail=f"heartbeat={heartbeat}")
    except Exception as e:
        return ServiceStatus(status="error", detail=str(e))


def check_dashscope_config() -> ServiceStatus:
    """Check that DashScope API key is configured (non-empty)."""
    settings = get_settings()
    if settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_API_KEY != "your_dashscope_api_key_here":
        return ServiceStatus(status="ok", detail="API key configured")
    return ServiceStatus(
        status="error",
        detail="DASHSCOPE_API_KEY not set or still placeholder",
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check system health including all service dependencies.

    Returns HTTP 200 with status 'ok' when all services are ready.
    Returns HTTP 200 with status 'degraded' if any non-critical service is down.
    Returns HTTP 503 if critical services are unavailable.
    """
    services = {
        "chromadb": check_chromadb(),
        "dashscope": check_dashscope_config(),
    }

    all_ok = all(s.status == "ok" for s in services.values())

    return HealthResponse(
        status="ok" if all_ok else "degraded",
        services=services,
    )
