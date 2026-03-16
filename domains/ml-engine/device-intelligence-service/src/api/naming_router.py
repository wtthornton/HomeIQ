"""
Naming Convention API Endpoints (Epic 64, Stories 64.1, 64.2, 64.4).

Endpoints:
  GET  /api/naming/audit           — Full audit across all entities
  GET  /api/naming/score/{id}      — Score a single entity
  POST /api/naming/suggest-aliases — Generate alias suggestions
  GET  /api/naming/suggest-name/{id} — Suggest convention-aware name
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..models.database import DeviceEntity
from ..services.naming_convention.alias_generator import AliasGenerator
from ..services.naming_convention.score_engine import ScoreEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/naming", tags=["Naming Convention"])

# Singletons
_score_engine = ScoreEngine()
_alias_generator = AliasGenerator()


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
    query = select(DeviceEntity)
    if entity_ids:
        query = query.where(DeviceEntity.entity_id.in_(entity_ids))
    query = query.limit(limit)

    result = await session.execute(query)
    rows = result.scalars().all()

    entities = []
    for row in rows:
        entities.append({
            "entity_id": row.entity_id,
            "domain": row.domain or "",
            "area_id": row.area_id or "",
            "friendly_name": row.friendly_name or row.name or "",
            "name_by_user": getattr(row, "name_by_user", None) or "",
            "device_class": row.device_class or "",
            "aliases": row.aliases if isinstance(row.aliases, list) else [],
            "labels": row.labels if isinstance(row.labels, list) else [],
        })

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
        return summary.to_dict()
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
            entity_id=entity_id,
            current_name=current_name,
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
    entity_id: str,
    current_name: str,
    area_id: str,
    domain: str,
    device_class: str,
) -> tuple[str, float, str]:
    """Build a convention-compliant name.

    Returns: (suggested_name, confidence, reasoning)
    """
    # Device type label
    type_map = {
        "light": "Light",
        "switch": "Switch",
        "sensor": "Sensor",
        "binary_sensor": "Sensor",
        "climate": "Thermostat",
        "cover": "Cover",
        "lock": "Lock",
        "fan": "Fan",
        "camera": "Camera",
        "media_player": "Media Player",
        "vacuum": "Vacuum",
        "automation": "Automation",
        "script": "Script",
        "scene": "Scene",
    }

    device_type = type_map.get(domain, "")
    if not device_type and device_class:
        device_type = device_class.replace("_", " ").title()
    if not device_type:
        device_type = domain.replace("_", " ").title() if domain else "Device"

    area_name = area_id.replace("_", " ").title() if area_id else ""

    if area_name:
        suggested = f"{area_name} {device_type}"
        confidence = 0.9
        reasoning = f"Convention: area prefix ({area_name}) + device type ({device_type}), Title Case"
    else:
        suggested = f"{device_type}"
        confidence = 0.6
        reasoning = f"Convention: device type ({device_type}), Title Case. Consider assigning an area."

    return suggested, confidence, reasoning
