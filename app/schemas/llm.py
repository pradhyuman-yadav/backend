"""
Pydantic schemas for LLM requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional


class GenerateRequest(BaseModel):
    """Request schema for text generation."""
    model: str = Field(..., description="Model name to use")
    prompt: str = Field(..., description="Input prompt for generation")
    stream: bool = Field(default=False, description="Whether to stream the response")


class GenerateResponse(BaseModel):
    """Response schema for non-streaming generation."""
    model: str = Field(..., description="Model used")
    response: str = Field(..., description="Generated text")
    done: bool = Field(..., description="Whether generation is complete")
    total_duration: Optional[int] = Field(None, description="Total time taken in nanoseconds")
    load_duration: Optional[int] = Field(None, description="Time to load model in nanoseconds")
    prompt_eval_count: Optional[int] = Field(None, description="Number of tokens in prompt")
    eval_count: Optional[int] = Field(None, description="Number of tokens generated")


class ModelInfo(BaseModel):
    """Information about an available model."""
    name: str = Field(..., description="Model name")
    modified_at: Optional[str] = Field(None, description="Last modified timestamp")
    size: Optional[int] = Field(None, description="Model size in bytes")
    digest: Optional[str] = Field(None, description="Model digest hash")


class ModelsResponse(BaseModel):
    """Response schema for listing available models."""
    models: list[ModelInfo] = Field(..., description="List of available models")


class StreamChunk(BaseModel):
    """Single chunk from streaming response."""
    text: str = Field(..., description="Text chunk")


class StreamError(BaseModel):
    """Error message in stream."""
    error: str = Field(..., description="Error message")


class StreamComplete(BaseModel):
    """Stream completion marker."""
    done: bool = Field(..., description="Whether stream is complete")
