"""Admin API router — blacklist CRUD operations."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class BlacklistAddRequest(BaseModel):
    """Request to add a blacklist pattern."""

    pattern: str = Field(
        ...,
        description=(
            "Blacklist pattern: glob (e.g. 'cover.*'), "
            "exact entity ID, or area-based ('area:Garage')"
        ),
    )


class BlacklistEntry(BaseModel):
    """A blacklist entry returned from the API."""

    id: int
    pattern: str


@router.get("/blacklist", response_model=list[BlacklistEntry])
async def list_blacklist() -> list[BlacklistEntry]:
    """List all entity blacklist patterns."""
    from ..main import blacklist_service

    if blacklist_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    entries = blacklist_service.list_all()
    return [BlacklistEntry(id=e.id, pattern=e.pattern) for e in entries]


@router.post("/blacklist", response_model=BlacklistEntry, status_code=201)
async def add_blacklist(req: BlacklistAddRequest) -> BlacklistEntry:
    """Add a new blacklist pattern."""
    from ..main import blacklist_service

    if blacklist_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    entry = blacklist_service.add(req.pattern)
    return BlacklistEntry(id=entry.id, pattern=entry.pattern)


@router.delete("/blacklist/{entry_id}", status_code=204)
async def remove_blacklist(entry_id: int) -> None:
    """Remove a blacklist pattern by ID."""
    from ..main import blacklist_service

    if blacklist_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    removed = blacklist_service.remove(entry_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Blacklist entry {entry_id} not found")
