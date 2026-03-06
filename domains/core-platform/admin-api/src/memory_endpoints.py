"""Memory management admin endpoints.

Provides CRUD operations for the HomeIQ memory brain system,
including listing, filtering, deletion, and confidence reinforcement.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from homeiq_memory import Memory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/memories", tags=["Memories"])

_memory_client = None


def _get_memory_client():
    """Lazy initialization of memory client."""
    global _memory_client
    if _memory_client is None:
        from homeiq_memory import MemoryClient

        _memory_client = MemoryClient(
            database_url=os.getenv("MEMORY_DATABASE_URL"),
        )
    return _memory_client


async def _ensure_client_initialized():
    """Ensure memory client is initialized."""
    client = _get_memory_client()
    if not client.available:
        success = await client.initialize()
        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory database unavailable",
            )
    return client


class MemoryResponse(BaseModel):
    """Response model for a single memory."""

    id: int
    content: str
    memory_type: str
    confidence: float
    effective_confidence: float
    source_channel: str
    source_service: str | None = None
    entity_ids: list[str] | None = None
    area_ids: list[str] | None = None
    tags: list[str] | None = None
    created_at: str
    updated_at: str


class MemoryListResponse(BaseModel):
    """Response model for paginated memory list."""

    memories: list[MemoryResponse]
    total: int
    page: int
    page_size: int


class ReinforceResponse(BaseModel):
    """Response model for reinforce operation."""

    id: int
    old_confidence: float
    new_confidence: float
    message: str


class DeleteResponse(BaseModel):
    """Response model for delete operation."""

    id: int
    archived: bool
    reason: str
    message: str


class TrustScoreResponse(BaseModel):
    """Response model for domain trust score."""

    domain: str
    trust_score: float = Field(..., ge=0.0, le=1.0, description="Trust score 0.0-1.0")
    approvals: int
    rejections: int
    overrides: int
    total_interactions: int
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence based on sample size")


class TrustScoresResponse(BaseModel):
    """Response model for all domain trust scores."""

    scores: list[TrustScoreResponse]
    overall_trust: float = Field(..., ge=0.0, le=1.0)


def _memory_to_response(memory: "Memory") -> MemoryResponse:
    """Convert Memory model to response model."""
    from homeiq_memory import effective_confidence

    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        memory_type=memory.memory_type.value,
        confidence=memory.confidence,
        effective_confidence=effective_confidence(memory),
        source_channel=memory.source_channel.value,
        source_service=memory.source_service,
        entity_ids=memory.entity_ids,
        area_ids=memory.area_ids,
        tags=memory.tags,
        created_at=memory.created_at.isoformat() if memory.created_at else "",
        updated_at=memory.updated_at.isoformat() if memory.updated_at else "",
    )


TRUST_DOMAINS = ["light", "climate", "lock", "cover", "fan", "switch", "sensor", "automation"]


async def _calculate_domain_trust(domain: str, session) -> TrustScoreResponse:
    """Calculate trust score for a single domain using memory queries."""
    from sqlalchemy import select

    from homeiq_memory import Memory, MemoryType

    # Query outcome memories for approvals (positive outcomes in this domain)
    approval_stmt = (
        select(Memory)
        .where(Memory.memory_type == MemoryType.OUTCOME)
        .where(Memory.content.ilike(f"%{domain}%approved%"))
    )
    approval_result = await session.execute(approval_stmt)
    approvals = list(approval_result.scalars().all())

    # Also count positive outcomes without explicit "approved" keyword
    positive_stmt = (
        select(Memory)
        .where(Memory.memory_type == MemoryType.OUTCOME)
        .where(Memory.content.ilike(f"%{domain}%success%"))
    )
    positive_result = await session.execute(positive_stmt)
    approvals.extend(positive_result.scalars().all())

    # Query boundary/preference memories for rejections
    rejection_stmt = (
        select(Memory)
        .where(Memory.memory_type.in_([MemoryType.BOUNDARY, MemoryType.PREFERENCE]))
        .where(Memory.content.ilike(f"%{domain}%reject%"))
    )
    rejection_result = await session.execute(rejection_stmt)
    rejections = list(rejection_result.scalars().all())

    # Also count explicit "never" preferences as rejections
    never_stmt = (
        select(Memory)
        .where(Memory.memory_type.in_([MemoryType.BOUNDARY, MemoryType.PREFERENCE]))
        .where(Memory.content.ilike(f"%{domain}%never%"))
    )
    never_result = await session.execute(never_stmt)
    rejections.extend(never_result.scalars().all())

    # Query behavioral memories for overrides
    override_stmt = (
        select(Memory)
        .where(Memory.memory_type == MemoryType.BEHAVIORAL)
        .where(Memory.content.ilike(f"%{domain}%override%"))
    )
    override_result = await session.execute(override_stmt)
    overrides = list(override_result.scalars().all())

    # Also count manual corrections as overrides
    correction_stmt = (
        select(Memory)
        .where(Memory.memory_type == MemoryType.BEHAVIORAL)
        .where(Memory.content.ilike(f"%{domain}%correct%"))
    )
    correction_result = await session.execute(correction_stmt)
    overrides.extend(correction_result.scalars().all())

    # Deduplicate by memory ID
    approval_ids = {m.id for m in approvals}
    rejection_ids = {m.id for m in rejections}
    override_ids = {m.id for m in overrides}

    approval_count = len(approval_ids)
    rejection_count = len(rejection_ids)
    override_count = len(override_ids)
    total = approval_count + rejection_count + override_count

    # Calculate trust with Bayesian smoothing (Beta(1,1) uniform prior)
    a = approval_count + 1
    b = rejection_count + override_count + 1
    trust_score = a / (a + b)

    # Confidence based on sample size (reaches 1.0 at 20+ interactions)
    confidence = min(1.0, total / 20)

    return TrustScoreResponse(
        domain=domain,
        trust_score=round(trust_score, 3),
        approvals=approval_count,
        rejections=rejection_count,
        overrides=override_count,
        total_interactions=total,
        confidence=round(confidence, 3),
    )


@router.get("/trust", response_model=TrustScoresResponse)
async def get_trust_scores(
    domain: str | None = Query(None, description="Filter to specific domain"),
) -> TrustScoresResponse:
    """Get trust scores for automation domains.

    Trust = approvals / (approvals + rejections + overrides) with Bayesian smoothing.
    Uses Beta(1,1) uniform prior for smoothing, so new domains start at 0.5 trust.
    Confidence increases with sample size, reaching 1.0 at 20+ interactions.
    """
    client = await _ensure_client_initialized()

    domains_to_check = [domain] if domain else TRUST_DOMAINS

    scores = []
    async with client._get_session() as session:
        for d in domains_to_check:
            score = await _calculate_domain_trust(d, session)
            scores.append(score)

    overall = sum(s.trust_score for s in scores) / len(scores) if scores else 0.5

    return TrustScoresResponse(scores=scores, overall_trust=round(overall, 3))


@router.get("/trust/{domain}", response_model=TrustScoreResponse)
async def get_domain_trust(domain: str) -> TrustScoreResponse:
    """Get trust score for a specific domain.

    Valid domains: light, climate, lock, cover, fan, switch, sensor, automation.
    """
    if domain not in TRUST_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain '{domain}' not found. Valid domains: {', '.join(TRUST_DOMAINS)}",
        )

    result = await get_trust_scores(domain=domain)
    return result.scores[0]


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    memory_type: str | None = Query(
        None, description="Filter by memory type (behavioral, preference, etc.)"
    ),
    min_confidence: float = Query(
        0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"
    ),
    entity_id: str | None = Query(
        None, description="Filter by entity ID (partial match)"
    ),
    search: str | None = Query(
        None, description="Full-text search in memory content"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> MemoryListResponse:
    """List memories with filters, pagination, and sorting.

    Returns memories sorted by updated_at descending (most recent first).
    Supports filtering by memory type, minimum confidence, entity association,
    and full-text search.
    """
    client = await _ensure_client_initialized()

    from sqlalchemy import select

    from homeiq_memory import Memory, MemoryType, effective_confidence

    async with client._get_session() as session:
        stmt = select(Memory).order_by(Memory.updated_at.desc())

        if memory_type:
            try:
                mt = MemoryType(memory_type)
                stmt = stmt.where(Memory.memory_type == mt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid memory_type: {memory_type}",
                ) from None

        if search:
            stmt = stmt.where(Memory.content.ilike(f"%{search}%"))

        result = await session.execute(stmt)
        all_memories = result.scalars().all()

    filtered_memories = []
    for mem in all_memories:
        if min_confidence > 0 and effective_confidence(mem) < min_confidence:
            continue

        if entity_id and (
            not mem.entity_ids or not any(entity_id in eid for eid in mem.entity_ids)
        ):
            continue

        filtered_memories.append(mem)

    total = len(filtered_memories)
    start = (page - 1) * page_size
    end = start + page_size
    page_memories = filtered_memories[start:end]

    return MemoryListResponse(
        memories=[_memory_to_response(m) for m in page_memories],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: int) -> MemoryResponse:
    """Get a single memory by ID.

    Returns the memory with its current and effective (decayed) confidence scores.
    """
    client = await _ensure_client_initialized()

    memory = await client.get(memory_id)
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found",
        )

    return _memory_to_response(memory)


@router.delete("/{memory_id}", response_model=DeleteResponse)
async def delete_memory(
    memory_id: int,
    reason: str = Query("admin_action", description="Reason for deletion"),
) -> DeleteResponse:
    """Delete (archive) a memory.

    Moves the memory to the archive table with the specified reason.
    This is a soft delete - the memory can be recovered from the archive.
    """
    client = await _ensure_client_initialized()

    memory = await client.get(memory_id)
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found",
        )

    archived = await client.delete(memory_id, reason=reason)

    logger.info("Deleted memory %d with reason: %s", memory_id, reason)

    return DeleteResponse(
        id=memory_id,
        archived=archived,
        reason=reason,
        message=f"Memory {memory_id} archived successfully",
    )


@router.post("/{memory_id}/reinforce", response_model=ReinforceResponse)
async def reinforce_memory(
    memory_id: int,
    amount: float = Query(0.1, ge=0.01, le=0.5, description="Confidence boost amount"),
) -> ReinforceResponse:
    """Manually boost memory confidence.

    Reinforces the memory's confidence score, simulating a confirming observation.
    Confidence is capped at 0.95.
    """
    client = await _ensure_client_initialized()

    memory = await client.get(memory_id)
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory {memory_id} not found",
        )

    old_confidence = memory.confidence

    from homeiq_memory import reinforce

    memory = reinforce(memory, amount=amount)

    updated = await client.update(memory_id, confidence=memory.confidence)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update memory confidence",
        )

    logger.info(
        "Reinforced memory %d: %.2f -> %.2f",
        memory_id,
        old_confidence,
        memory.confidence,
    )

    return ReinforceResponse(
        id=memory_id,
        old_confidence=old_confidence,
        new_confidence=memory.confidence,
        message=f"Memory {memory_id} reinforced successfully",
    )
