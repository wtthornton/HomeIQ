"""
Common Dependency Injection Functions

Epic 39, Story 39.13: Router Modularization
Centralized dependency injection for routers to avoid duplication.
"""

import logging
from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...clients.ha_client import HomeAssistantClient
from ...llm.openai_client import OpenAIClient
from ...database import get_db as get_db_session

logger = logging.getLogger(__name__)

# Global client instances (initialized by main.py)
_ha_client: HomeAssistantClient | None = None
_openai_client: OpenAIClient | None = None


def set_ha_client(client: HomeAssistantClient) -> None:
    """Set the global Home Assistant client instance."""
    global _ha_client
    _ha_client = client
    logger.info("✅ Home Assistant client registered in common dependencies")


def set_openai_client(client: OpenAIClient) -> None:
    """Set the global OpenAI client instance."""
    global _openai_client
    _openai_client = client
    logger.info("✅ OpenAI client registered in common dependencies")


def get_ha_client() -> HomeAssistantClient:
    """
    Dependency injection for Home Assistant client.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(ha_client: HomeAssistantClient = Depends(get_ha_client)):
            ...
    """
    global _ha_client
    if not _ha_client:
        raise HTTPException(
            status_code=500,
            detail="Home Assistant client not initialized"
        )
    return _ha_client


def get_openai_client() -> OpenAIClient:
    """
    Dependency injection for OpenAI client.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(openai_client: OpenAIClient = Depends(get_openai_client)):
            ...
    """
    global _openai_client
    if not _openai_client:
        raise HTTPException(
            status_code=500,
            detail="OpenAI client not initialized"
        )
    return _openai_client


def get_db() -> AsyncSession:
    """
    Dependency injection for database session.
    Re-export from database module for convenience.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    return Depends(get_db_session)

