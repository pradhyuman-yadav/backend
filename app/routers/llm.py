"""
API routes for LLM endpoints.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.middleware.auth import verify_api_key
from app.services.llm.ollama_service import ollama_service
from app.services.llm.streaming_utils import stream_ollama_response
from app.schemas.llm import (
    GenerateRequest,
    GenerateResponse,
    ModelsResponse,
    ModelInfo
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/llm", tags=["LLM"])


@router.get("/health", summary="Health check for LLM service")
async def health_check():
    """Check if LLM service is healthy."""
    try:
        await ollama_service.get_available_models()
        return {"status": "healthy", "service": "Ollama LLM"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service is unavailable"
        )


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="Get available models",
    dependencies=[Depends(verify_api_key)]
)
async def get_models():
    """Get list of available models from Ollama."""
    try:
        models = await ollama_service.get_available_models()
        model_list = [
            ModelInfo(
                name=m.get("name"),
                modified_at=m.get("modified_at"),
                size=m.get("size"),
                digest=m.get("digest")
            )
            for m in models
        ]
        return ModelsResponse(models=model_list)
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@router.post(
    "/generate",
    summary="Generate text (non-streaming)",
    dependencies=[Depends(verify_api_key)]
)
async def generate(request: GenerateRequest):
    """
    Generate text using specified model.

    For non-streaming responses, the full generated text is returned in one response.
    """
    try:
        result = await ollama_service.generate(
            model=request.model,
            prompt=request.prompt,
            stream=False
        )
        return result
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@router.post(
    "/stream",
    summary="Generate text (streaming)",
    dependencies=[Depends(verify_api_key)]
)
async def stream_generate(request: GenerateRequest):
    """
    Generate text with streaming response.

    Returns Server-Sent Events (SSE) stream of generated text chunks.
    Each event contains a JSON object with 'text' field for text chunks
    and a final event with 'done': true when generation is complete.
    """
    try:
        # Get the stream generator from Ollama
        stream_gen = await ollama_service.generate(
            model=request.model,
            prompt=request.prompt,
            stream=True
        )

        # Convert to SSE format
        return StreamingResponse(
            stream_ollama_response(stream_gen),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Error in streaming generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
