"""
Configuration management for the FastAPI application.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_title: str = "MLOps Backend Service"
    api_version: str = "0.1.0"
    api_description: str = "Backend service for LLM integration with Ollama"

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"

    # Authentication
    api_key: str = "your-secret-api-key-change-this"
    auth_enabled: bool = True

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 3002
    debug: bool = False

    # CORS Configuration - comma-separated list from .env or default
    # Set to "*" for development to allow all origins (not recommended for production)
    # Set to specific origins for production: "http://localhost:3000,http://example.com"
    allowed_origins: str = "http://localhost:*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_allowed_origins(self) -> list:
        """
        Parse allowed origins from config string.

        Supports:
        - Specific origins: "http://localhost:3000,http://example.com"
        - All localhost: "http://localhost:*"
        - All origins: "*"

        Returns:
            List of allowed origins for CORS middleware
        """
        if self.allowed_origins == "*":
            return ["*"]

        if self.allowed_origins == "http://localhost:*":
            # Return regex pattern for matching localhost with any port
            return ["http://localhost:*"]

        # Parse comma-separated origins
        return [origin.strip() for origin in self.allowed_origins.split(",")]


settings = Settings()
