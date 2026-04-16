from fastapi import FastAPI
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Enterprise Knowledge Base RAG",
    description="Enterprise document knowledge base with RAG-powered Q&A",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"message": "Enterprise Knowledge Base RAG System", "version": "0.1.0"}
