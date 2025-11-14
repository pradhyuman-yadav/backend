"""
FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import llm
from app.services.llm.ollama_service import ollama_service
from app.utils.helpers import setup_logging


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    """
    # Startup
    logger.info("Application starting...")
    logger.info(f"Ollama service configured at: {settings.ollama_base_url}")
    logger.info(f"Authentication enabled: {settings.auth_enabled}")
    logger.info(f"CORS allowed origins: {settings.allowed_origins}")
    yield
    # Shutdown
    logger.info("Application shutting down...")
    await ollama_service.close()


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(llm.router)


# Root endpoint
@app.get("/", summary="API root")
async def root():
    """Root endpoint for API information."""
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "documentation": "/docs",
        "ollama_url": settings.ollama_base_url
    }


# Health check endpoint
@app.get("/health", summary="Application health check")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": settings.api_title
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
