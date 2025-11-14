"""
Simple API key authentication middleware.
"""
from fastapi import HTTPException, status, Header
from typing import Optional
from app.config import settings


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify API key from request headers.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The API key if valid

    Raises:
        HTTPException: If authentication is enabled and key is invalid
    """
    if not settings.auth_enabled:
        return "no-auth"

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header"
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return x_api_key
