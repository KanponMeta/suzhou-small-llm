"""Dataset generation API routes."""
import logging

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse

from src.dataset.generator import generate_qa_pairs
from src.dataset.exporter import export_dataset_to_zip
from src.vectorstore import get_vectorstore
from src.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.post("/generate")
async def generate_dataset():
    """Generate evaluation dataset ZIP from indexed documents.

    This endpoint:
    1. Retrieves all document chunks from ChromaDB
    2. Generates Q&A pairs using LLM (qwen-long)
    3. Exports to ZIP file compliant with 数据集提交指南.md
    4. Returns ZIP file as streaming download

    Returns:
        StreamingResponse: ZIP file with evaluation_data.json and attachments/

    Raises:
        HTTPException 404: No documents indexed in vector store
        HTTPException 500: Internal error during generation
    """
    try:
        # Get vectorstore
        vectorstore = get_vectorstore()

        # Check if any documents exist
        try:
            result = vectorstore._collection.get()
            ids = result.get("ids", [])
        except Exception as e:
            logger.error(f"Failed to query vector store: {e}")
            raise HTTPException(status_code=500, detail="Failed to query vector store")

        if not ids or len(ids) == 0:
            logger.warning("No documents found in vector store")
            raise HTTPException(
                status_code=404,
                detail="No documents indexed. Please upload documents first."
            )

        logger.info(f"Found {len(ids)} document chunks in vector store")

        # Generate Q&A pairs
        try:
            evaluation_data = generate_qa_pairs(vectorstore)
        except Exception as e:
            logger.error(f"Failed to generate Q&A pairs: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate Q&A pairs: {str(e)}")

        if not evaluation_data.test_cases:
            logger.warning("No Q&A pairs generated")
            raise HTTPException(
                status_code=404,
                detail="No Q&A pairs could be generated from indexed documents"
            )

        logger.info(f"Generated {len(evaluation_data.test_cases)} test cases")

        # Export to ZIP
        try:
            zip_buffer = export_dataset_to_zip(evaluation_data)
        except Exception as e:
            logger.error(f"Failed to export dataset: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to export dataset: {str(e)}")

        # Return streaming response
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=evaluation_dataset.zip"
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_dataset: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
