"""FastAPI application for Enterprise Knowledge Base RAG System."""
from fastapi import FastAPI
from src.api.chat import router as chat_router

app = FastAPI(
    title="Enterprise Knowledge Base RAG System",
    description="OpenAI-compatible RAG API for enterprise document Q&A",
    version="1.0.0",
)

# Include the chat completions router
app.include_router(chat_router)
