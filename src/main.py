"""FastAPI application for Enterprise Knowledge Base RAG System."""
from dotenv import load_dotenv
load_dotenv()  # Load .env into os.environ before any library reads it

from fastapi import FastAPI
from src.api.chat import router as chat_router
from src.api.routes.dataset import router as dataset_router
from src.api.documents import router as documents_router
from src.api.health import router as health_router

app = FastAPI(
    title="Enterprise Knowledge Base RAG System",
    description="OpenAI-compatible RAG API for enterprise document Q&A",
    version="1.0.0",
)

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(dataset_router)


@app.get("/")
async def root():
    return {"message": "Enterprise Knowledge Base RAG System", "version": "1.0.0"}
