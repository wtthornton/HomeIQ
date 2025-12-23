"""
Common Router Utilities

Epic 39, Story 39.13: Router Modularization
Shared utilities for routers including dependency injection, error handling, and validation.
"""

from .dependencies import (
    get_ha_client,
    get_openai_client,
    get_db,
)

__all__ = [
    "get_ha_client",
    "get_openai_client",
    "get_db",
]

