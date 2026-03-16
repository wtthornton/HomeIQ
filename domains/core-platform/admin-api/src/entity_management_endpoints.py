"""
Entity Management Endpoints — Story 62.4

CRUD endpoints for managing entity labels, aliases, and friendly names.
Writes to HomeIQ's data-api and syncs to Home Assistant Entity Registry.
"""

import logging
import os
import re
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities", tags=["Entity Management"])

DATA_API_URL = os.getenv("DATA_API_URL", "http://data-api:8006")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")
HA_URL = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
HA_TOKEN = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")

# Label format: prefix:name (e.g., ai:automatable, sensor:primary)
_LABEL_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*$")


# ── Request Models ──────────────────────────────────────────────────────────

class SetLabelsRequest(BaseModel):
    """Set labels for an entity."""
    labels: list[str] = Field(description="Labels in prefix:name format")

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: list[str]) -> list[str]:
        for lbl in v:
            if not _LABEL_PATTERN.match(lbl):
                msg = f"Invalid label format '{lbl}'. Expected 'prefix:name' (lowercase)."
                raise ValueError(msg)
        return v


class SetAliasesRequest(BaseModel):
    """Set aliases for an entity."""
    aliases: list[str] = Field(description="Alternative names for the entity")


class SetNameRequest(BaseModel):
    """Set user-customized friendly name."""
    name_by_user: str = Field(min_length=1, max_length=200)


class BulkLabelRequest(BaseModel):
    """Add or remove labels across multiple entities."""
    entity_ids: list[str] = Field(min_length=1)
    add_labels: list[str] = Field(default_factory=list)
    remove_labels: list[str] = Field(default_factory=list)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _validate_entity_id(entity_id: str) -> str:
    """Validate entity_id format to prevent injection."""
    if not re.match(r"^[a-z_]+\.[a-z0-9_]+$", entity_id):
        raise HTTPException(status_code=400, detail=f"Invalid entity_id: {entity_id}")
    return entity_id


async def _patch_data_api(entity_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    """Update entity fields in data-api via internal bulk_upsert."""
    url = f"{DATA_API_URL}/internal/entities/bulk_upsert"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if DATA_API_KEY:
        headers["Authorization"] = f"Bearer {DATA_API_KEY}"

    payload = [{"entity_id": entity_id, **patch}]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error("Failed to update entity %s in data-api: %s", entity_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"data-api update failed: {exc}",
        ) from exc


async def _sync_to_ha(entity_id: str, ha_patch: dict[str, Any]) -> None:
    """Best-effort sync to Home Assistant Entity Registry."""
    if not HA_URL or not HA_TOKEN:
        logger.debug("HA sync skipped — HA_URL or HA_TOKEN not configured")
        return

    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
    # HA uses websocket for entity registry updates; REST endpoint may vary.
    # We use the websocket message format via REST call.
    ws_msg = {
        "type": "config/entity_registry/update",
        "entity_id": entity_id,
        **ha_patch,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{HA_URL.rstrip('/')}/api/websocket",
                json=ws_msg,
                headers=headers,
            )
            if resp.status_code < 400:
                logger.info("Synced entity %s to HA registry", entity_id)
            else:
                logger.warning("HA sync returned %d for %s", resp.status_code, entity_id)
    except httpx.HTTPError as exc:
        logger.warning("HA sync failed for %s (best-effort): %s", entity_id, exc)


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.put("/{entity_id}/labels")
async def set_entity_labels(entity_id: str, body: SetLabelsRequest) -> dict[str, Any]:
    """Set labels for an entity — Story 62.4"""
    entity_id = _validate_entity_id(entity_id)
    result = await _patch_data_api(entity_id, {"labels": body.labels})
    await _sync_to_ha(entity_id, {"labels": body.labels})
    return {"success": True, "entity_id": entity_id, "labels": body.labels, "data_api": result}


@router.put("/{entity_id}/aliases")
async def set_entity_aliases(entity_id: str, body: SetAliasesRequest) -> dict[str, Any]:
    """Set aliases for an entity — Story 62.4"""
    entity_id = _validate_entity_id(entity_id)
    result = await _patch_data_api(entity_id, {"aliases": body.aliases})
    await _sync_to_ha(entity_id, {"aliases": body.aliases})
    return {"success": True, "entity_id": entity_id, "aliases": body.aliases, "data_api": result}


@router.put("/{entity_id}/name")
async def set_entity_name(entity_id: str, body: SetNameRequest) -> dict[str, Any]:
    """Set user-customized friendly name — Story 62.4"""
    entity_id = _validate_entity_id(entity_id)
    result = await _patch_data_api(entity_id, {"name_by_user": body.name_by_user})
    await _sync_to_ha(entity_id, {"name": body.name_by_user})
    return {"success": True, "entity_id": entity_id, "name_by_user": body.name_by_user, "data_api": result}


@router.post("/bulk-label")
async def bulk_label_entities(body: BulkLabelRequest) -> dict[str, Any]:
    """Add or remove labels across multiple entities — Story 62.4"""
    if not body.add_labels and not body.remove_labels:
        raise HTTPException(status_code=400, detail="Specify add_labels or remove_labels")

    # Validate all labels
    for lbl in body.add_labels + body.remove_labels:
        if not _LABEL_PATTERN.match(lbl):
            raise HTTPException(status_code=400, detail=f"Invalid label: {lbl}")

    # Fetch current labels for each entity, then compute new label sets
    updated: list[str] = []
    errors: list[str] = []

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if DATA_API_KEY:
        headers["Authorization"] = f"Bearer {DATA_API_KEY}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        for eid in body.entity_ids:
            try:
                eid = _validate_entity_id(eid)
                # Fetch current entity
                resp = await client.get(
                    f"{DATA_API_URL}/api/entities/{eid}", headers=headers
                )
                if resp.status_code == 404:
                    errors.append(f"{eid}: not found")
                    continue
                resp.raise_for_status()
                entity = resp.json()

                current_labels = set(entity.get("labels") or [])
                new_labels = (current_labels | set(body.add_labels)) - set(body.remove_labels)
                new_labels_list = sorted(new_labels)

                # Update via bulk_upsert
                upsert_resp = await client.post(
                    f"{DATA_API_URL}/internal/entities/bulk_upsert",
                    json=[{"entity_id": eid, "labels": new_labels_list}],
                    headers=headers,
                )
                upsert_resp.raise_for_status()
                updated.append(eid)

                # Best-effort HA sync
                await _sync_to_ha(eid, {"labels": new_labels_list})

            except HTTPException:
                raise
            except Exception as exc:
                errors.append(f"{eid}: {exc}")

    return {
        "success": len(errors) == 0,
        "updated_count": len(updated),
        "updated_entities": updated,
        "errors": errors,
    }
