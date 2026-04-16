from fastapi import FastAPI
from app.config import get_settings
from app.api.documents import router as documents_router
from app.api.health import router as health_router

settings = get_settings()

app = FastAPI(
    title="Enterprise Knowledge Base RAG",
    description="Enterprise document knowledge base with RAG-powered Q&A",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(documents_router)


@app.get("/")
async def root():
    return {"message": "Enterprise Knowledge Base RAG System", "version": "0.1.0"}
