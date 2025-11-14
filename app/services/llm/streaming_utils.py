"""
Utilities for handling streaming responses.
"""
import json
import logging
from typing import AsyncGenerator


logger = logging.getLogger(__name__)


async def stream_ollama_response(
    stream_generator: AsyncGenerator[str, None]
) -> AsyncGenerator[str, None]:
    """
    Convert Ollama streaming response to SSE format.

    Args:
        stream_generator: Async generator yielding JSON lines from Ollama

    Yields:
        Server-Sent Event formatted strings
    """
    try:
        async for line in stream_generator:
            try:
                data = json.loads(line)
                # Extract response text from Ollama response
                response_text = data.get("response", "")
                if response_text:
                    # Format as SSE
                    yield f"data: {json.dumps({'text': response_text})}\n\n"

                # Check if this is the last chunk
                if data.get("done", False):
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    break

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON line: {line}, error: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in stream processing: {str(e)}")
        yield f"data: {json.dumps({'error': 'Stream processing error'})}\n\n"
