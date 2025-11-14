"""
Ollama LLM service for handling requests to Ollama server.
"""
import httpx
import logging
from typing import AsyncGenerator
from app.config import settings


logger = logging.getLogger(__name__)


class OllamaService:
    """Service for interacting with Ollama LLM server."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.client = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout
        return self.client

    async def close(self):
        """Close the HTTP client."""
        if self.client is not None:
            await self.client.aclose()

    async def get_available_models(self) -> list:
        """
        Get list of available models from Ollama.

        Returns:
            List of available models
        """
        try:
            client = await self.get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            logger.info(f"Retrieved {len(models)} available models from Ollama")
            return models
        except httpx.RequestError as e:
            logger.error(f"Error connecting to Ollama: {str(e)}")
            raise Exception(f"Cannot connect to Ollama server at {self.base_url}")
        except Exception as e:
            logger.error(f"Error getting models from Ollama: {str(e)}")
            raise

    async def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = False
    ) -> AsyncGenerator[str, None] | dict:
        """
        Generate text using Ollama.

        Args:
            model: Model name to use
            prompt: Input prompt
            stream: Whether to stream the response

        Yields/Returns:
            Text chunks if streaming, or complete response if not streaming
        """
        try:
            client = await self.get_client()
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream
            }

            if stream:
                return self._stream_response(client, payload)
            else:
                return await self._non_stream_response(client, payload)

        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            raise

    async def _non_stream_response(self, client: httpx.AsyncClient, payload: dict) -> dict:
        """Handle non-streaming response."""
        response = await client.post(f"{self.base_url}/api/generate", json=payload)
        response.raise_for_status()
        return response.json()

    async def _stream_response(
        self,
        client: httpx.AsyncClient,
        payload: dict
    ) -> AsyncGenerator[str, None]:
        """
        Handle streaming response from Ollama.

        Yields:
            JSON chunks as strings
        """
        async with client.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    yield line + "\n"


# Global instance
ollama_service = OllamaService()
