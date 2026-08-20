"""
Naming Convention API Endpoints (Epic 64, Stories 64.1, 64.2, 64.4).

Endpoints:
  GET  /api/naming/audit           — Full audit across all entities
  GET  /api/naming/score/{id}      — Score a single entity
  POST /api/naming/score           — Score caller-supplied entities (stateless)
  POST /api/naming/suggest-aliases — Generate alias suggestions
  GET  /api/naming/suggest-name/{id} — Suggest convention-aware name
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..core.database import get_db_session
from ..models.database import DeviceEntity
from ..services.naming_convention.alias_generator import AliasGenerator
from ..services.naming_convention.name_builder import compose_name, device_type_label
from ..services.naming_convention.score_engine import ScoreEngine

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/naming", tags=["Naming Convention"])

# Singletons
_score_engine = ScoreEngine()

# Rubric dimensions HomeIQ does not collect, so it cannot score them. They are
# reported rather than silently counted as failures: `config/entity_registry/list`
# carries no `aliases` key at all, and `device_class` is a state attribute this
# router never reads. Every entity therefore forfeits these points equally, which
# depresses the absolute score without changing the ranking. Closing the gap means
# collecting the data first — scoring harder against data that was never fetched
# would just be a confident wrong number.
UNCOLLECTED_RUBRIC_FIELDS = ("aliases", "device_class")


def compose_friendly_name(
    entity_name: str | None,
    original_name: str | None,
    has_entity_name: bool,
    device_name: str | None,
) -> str:
    """Rebuild the friendly name HA shows, from the registry fields we store.

    HA does not persist `friendly_name`; it composes it, and scoring the raw
    `name` column instead reports "entity has no friendly name" for entities that
    plainly have one — `light.inovelli_vzm31_sn` stores an empty name and shows
    as "Office Light Dimmer".

    Verified against this instance:
      has_entity_name, original_name NULL  -> device name
        light.inovelli_vzm31_sn        -> "Office Light Dimmer"
      has_entity_name, original_name set   -> "<device> <original>"
        sensor.inovelli_vzm31_sn_power -> "Office Light Dimmer Power"
    A user-set entity name overrides all of it.
    """
    if entity_name:
        return entity_name
    if has_entity_name and device_name:
        return f"{device_name} {original_name}".strip() if original_name else device_name
    return original_name or ""


_alias_generator = AliasGenerator()


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class ScoreEntityInput(BaseModel):
    """One entity to score. Mirrors the fields the rubric reads."""

    entity_id: str
    domain: str = ""
    area_id: str = ""
    friendly_name: str = ""
    device_class: str = ""
    aliases: list[str] = []
    labels: list[str] = []


class ScoreBatchRequest(BaseModel):
    """Score entities as supplied, without reading the database."""

    entities: list[ScoreEntityInput] = Field(..., min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class RuleScoreResponse(BaseModel):
    rule: str
    earned: int
    max: int
    issues: list[str] = []
    suggestions: list[str] = []


class EntityScoreResponse(BaseModel):
    entity_id: str
    total_score: int
    max_score: int = 100
    pct: float
    rules: list[RuleScoreResponse] = []
    issues: list[str] = []
    suggestions: list[str] = []


class ScoreBatchResponse(BaseModel):
    entities: list[EntityScoreResponse] = []


class TopIssueResponse(BaseModel):
    issue: str
    count: int


class AuditResponse(BaseModel):
    total_entities: int
    average_score: float
    compliance_pct: float
    top_issues: list[TopIssueResponse] = []
    score_distribution: dict[str, int] = {}
    entities: list[EntityScoreResponse] = []
    uncollected_fields: list[str] = Field(
        default_factory=lambda: list(UNCOLLECTED_RUBRIC_FIELDS),
        description=(
            "Rubric dimensions HomeIQ does not collect, so every entity forfeits "
            "them equally. The scores below are partial by this much — read them as "
            "a ranking, not as an absolute compliance percentage."
        ),
    )


class AliasSuggestionResponse(BaseModel):
    alias: str
    source: str
    confidence: float


class AliasResultResponse(BaseModel):
    entity_id: str
    current_aliases: list[str] = []
    suggestions: list[AliasSuggestionResponse] = []
    conflicts: list[str] = []


class AliasBatchRequest(BaseModel):
    entity_ids: list[str] | None = Field(
        default=None,
        description="Specific entity IDs, or None for all entities",
    )
    max_suggestions: int = Field(default=5, ge=1, le=10)


class AliasBatchResponse(BaseModel):
    results: list[AliasResultResponse]
    total: int


class NameSuggestionResponse(BaseModel):
    entity_id: str
    current_name: str
    suggested_name: str
    confidence: float
    reasoning: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _load_entities(
    session: AsyncSession,
    entity_ids: list[str] | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Load entities from DB as dicts suitable for scoring."""
    # `area_id` lives on the DEVICE, not the entity: HA exposes an entity-level
    # area_id but it is an override that is unset on all 768 entities here, so
    # the device's area is the only one there is. Eager-loaded because scoring
    # 500 entities one lazy `device` hop at a time is 500 round trips.
    query = select(DeviceEntity).options(joinedload(DeviceEntity.device))
    if entity_ids:
        query = query.where(DeviceEntity.entity_id.in_(entity_ids))
    query = query.limit(limit)

    result = await session.execute(query)
    rows = result.scalars().unique().all()

    entities = []
    for row in rows:
        labels = row.labels if isinstance(row.labels, list) else []
        entities.append(
            {
                "entity_id": row.entity_id,
                "domain": row.domain or "",
                "area_id": (row.device.area_id if row.device else None) or "",
                "friendly_name": compose_friendly_name(
                    row.name,
                    row.original_name,
                    bool(row.has_entity_name),
                    row.device.name if row.device else None,
                ),
                "name_by_user": row.name or "",
                # Not collected — see UNCOLLECTED_RUBRIC_FIELDS.
                "device_class": "",
                "aliases": [],
                "labels": labels,
            }
        )

    return entities


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/audit", response_model=AuditResponse)
async def audit_naming_conventions(
    limit: int = Query(default=500, ge=1, le=2000, description="Max entities to audit"),
    session: AsyncSession = Depends(get_db_session),
):
    """Full naming convention audit across all entities."""
    try:
        entities = await _load_entities(session, limit=limit)
        summary = _score_engine.audit(entities)
        return {**summary.to_dict(), "uncollected_fields": list(UNCOLLECTED_RUBRIC_FIELDS)}
    except Exception as e:
        logger.error("Audit failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/score/{entity_id}", response_model=EntityScoreResponse)
async def score_entity(
    entity_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Score a single entity against naming conventions."""
    try:
        entities = await _load_entities(session, entity_ids=[entity_id])
        if not entities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found",
            )
        score = _score_engine.score_entity(entities[0])
        return score.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Score failed for %s: %s", entity_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post("/score", response_model=ScoreBatchResponse)
async def score_entities(request: ScoreBatchRequest):
    """Score caller-supplied entities against the naming rubric.

    Unlike ``GET /score/{entity_id}``, this reads nothing from the database, so
    a caller holding an entity the registry has not synced yet — an edit the
    dashboard just applied, say — still gets an authoritative score rather than
    a stale one. It is the only way for a client to score without owning a
    second copy of the rubric (TAP-6230).
    """
    scores = [
        _score_engine.score_entity(entity.model_dump()).to_dict() for entity in request.entities
    ]
    return {"entities": scores}


@router.post("/suggest-aliases", response_model=AliasBatchResponse)
async def suggest_aliases(
    request: AliasBatchRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Generate alias suggestions for entities (pattern-based, no AI)."""
    try:
        entities = await _load_entities(session, entity_ids=request.entity_ids)
        alias_map = _alias_generator.build_alias_map(entities)

        results = []
        for entity in entities:
            result = _alias_generator.suggest_aliases(
                entity=entity,
                existing_aliases_map=alias_map,
                max_suggestions=request.max_suggestions,
            )
            results.append(result.to_dict())

        return AliasBatchResponse(results=results, total=len(results))
    except Exception as e:
        logger.error("Alias suggestion failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/suggest-name/{entity_id}", response_model=NameSuggestionResponse)
async def suggest_name(
    entity_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Suggest a convention-aware name for an entity (Story 64.4).

    Uses DeviceNameGenerator patterns with convention rules:
    area prefix, Title Case, no brand names.
    """
    try:
        entities = await _load_entities(session, entity_ids=[entity_id])
        if not entities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found",
            )

        entity = entities[0]
        current_name = entity.get("friendly_name") or entity_id
        area_id = entity.get("area_id") or ""
        domain = entity.get("domain") or ""
        device_class = entity.get("device_class") or ""

        # Build convention-aware name
        suggested, confidence, reasoning = _build_convention_name(
            area_id=area_id,
            domain=domain,
            device_class=device_class,
        )

        return NameSuggestionResponse(
            entity_id=entity_id,
            current_name=current_name,
            suggested_name=suggested,
            confidence=confidence,
            reasoning=reasoning,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Name suggestion failed for %s: %s", entity_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


def _build_convention_name(
    area_id: str,
    domain: str,
    device_class: str,
) -> tuple[str, float, str]:
    """Build a convention-compliant name.

    Returns: (suggested_name, confidence, reasoning)
    """
    # One composer for the whole service (TAP-6231) — see name_builder.
    device_type = device_type_label(domain, device_class)
    area_name = area_id.replace("_", " ").title() if area_id else ""
    suggested = compose_name(area_name or None, device_type)

    if area_name:
        confidence = 0.9
        reasoning = (
            f"Convention: area prefix ({area_name}) + device type ({device_type}), Title Case"
        )
    else:
        confidence = 0.6
        reasoning = (
            f"Convention: device type ({device_type}), Title Case. Consider assigning an area."
        )

    return suggested, confidence, reasoning
