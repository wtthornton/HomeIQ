"""
Entity Management Endpoints — Story 62.4

CRUD endpoints for managing entity labels, aliases, and friendly names.
Writes to HomeIQ's data-api and syncs to Home Assistant Entity Registry.
"""

import logging
import os
import re
from itertools import count
from typing import Any

import aiohttp
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


def _make_ws_caller(ws: aiohttp.ClientWebSocketResponse) -> Any:
    """Return an async callable running one HA WS command and returning its result."""
    counter = count(1)

    async def call(payload: dict[str, Any]) -> Any:
        msg_id = next(counter)
        await ws.send_json({"id": msg_id, **payload})
        while True:
            msg = await ws.receive_json()
            if msg.get("id") == msg_id and msg.get("type") == "result":
                if not msg.get("success"):
                    raise RuntimeError(str(msg.get("error")))
                return msg.get("result")

    return call


def _slugify_label(name: str) -> str:
    """Approximate HA's label_id slugification (lowercase, non-alnum -> _)."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


async def _resolve_label_ids(call: Any, label_names: list[str]) -> list[str]:
    """Map label names to label_registry ids, creating missing labels.

    Matches by exact name OR by slug: HA stores label_ids as slugs, and those
    slugs round-trip back through the entity store as if they were names
    (e.g. "role_presence" for "role:presence"). Treating such a slug as a new
    name would mint a duplicate "<slug>_2" label on every re-apply.
    """
    registry = await call({"type": "config/label_registry/list"})
    by_name = {lbl["name"]: lbl["label_id"] for lbl in registry}
    by_id = {lbl["label_id"] for lbl in registry}
    label_ids = []
    for name in label_names:
        if name in by_name:
            label_ids.append(by_name[name])
        elif name in by_id or _slugify_label(name) in by_id:
            label_ids.append(name if name in by_id else _slugify_label(name))
        else:
            created = await call({"type": "config/label_registry/create", "name": name})
            by_name[name] = created["label_id"]
            by_id.add(created["label_id"])
            label_ids.append(created["label_id"])
    return label_ids


async def _sync_to_ha(entity_id: str, ha_patch: dict[str, Any]) -> dict[str, Any]:
    """Sync entity registry changes to Home Assistant over its WebSocket API.

    The entity registry is WebSocket-only (REST 404s). Label assignments must
    reference label_registry ids, so label names are resolved (and created)
    there first. Returns {"synced": bool, "detail": str} so callers can surface
    whether HA actually applied the change.
    """
    if not HA_URL or not HA_TOKEN:
        return {"synced": False, "detail": "HA_URL or HA_TOKEN not configured"}

    ws_url = re.sub(r"^http", "ws", HA_URL.rstrip("/"), count=1) + "/api/websocket"
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.ws_connect(ws_url) as ws,
        ):
            await ws.receive_json()  # auth_required
            await ws.send_json({"type": "auth", "access_token": HA_TOKEN})
            auth = await ws.receive_json()
            if auth.get("type") != "auth_ok":
                logger.warning("HA sync auth failed for %s", entity_id)
                return {"synced": False, "detail": "HA websocket auth failed"}

            call = _make_ws_caller(ws)
            patch = dict(ha_patch)
            if "labels" in patch:
                patch["labels"] = await _resolve_label_ids(call, patch["labels"])

            await call(
                {"type": "config/entity_registry/update", "entity_id": entity_id, **patch}
            )
            logger.info("Synced entity %s to HA registry", entity_id)
            return {"synced": True, "detail": "ok"}
    except (aiohttp.ClientError, RuntimeError, TimeoutError) as exc:
        logger.warning("HA sync failed for %s: %s", entity_id, exc)
        return {"synced": False, "detail": f"HA sync failed: {exc}"}


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.put("/{entity_id}/labels")
async def set_entity_labels(entity_id: str, body: SetLabelsRequest) -> dict[str, Any]:
    """Set labels for an entity — Story 62.4"""
    entity_id = _validate_entity_id(entity_id)
    result = await _patch_data_api(entity_id, {"labels": body.labels})
    ha = await _sync_to_ha(entity_id, {"labels": body.labels})
    return {
        "success": ha["synced"],
        "entity_id": entity_id,
        "labels": body.labels,
        "data_api": result,
        "ha": ha,
    }


@router.put("/{entity_id}/aliases")
async def set_entity_aliases(entity_id: str, body: SetAliasesRequest) -> dict[str, Any]:
    """Set aliases for an entity — Story 62.4"""
    entity_id = _validate_entity_id(entity_id)
    result = await _patch_data_api(entity_id, {"aliases": body.aliases})
    ha = await _sync_to_ha(entity_id, {"aliases": body.aliases})
    return {
        "success": ha["synced"],
        "entity_id": entity_id,
        "aliases": body.aliases,
        "data_api": result,
        "ha": ha,
    }


@router.put("/{entity_id}/name")
async def set_entity_name(entity_id: str, body: SetNameRequest) -> dict[str, Any]:
    """Set user-customized friendly name — Story 62.4"""
    entity_id = _validate_entity_id(entity_id)
    result = await _patch_data_api(entity_id, {"name_by_user": body.name_by_user})
    ha = await _sync_to_ha(entity_id, {"name": body.name_by_user})
    return {
        "success": ha["synced"],
        "entity_id": entity_id,
        "name_by_user": body.name_by_user,
        "data_api": result,
        "ha": ha,
    }


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
                resp = await client.get(f"{DATA_API_URL}/api/entities/{eid}", headers=headers)
                if resp.status_code == 404:
                    errors.append(f"{eid}: not found")
                    continue
                resp.raise_for_status()
                entity = resp.json()

                # Keep only pattern-conforming label names. HA-side label_id
                # slugs ("role_presence") round-trip into the store via
                # ingestion sync; carrying them forward would re-mint deleted
                # labels as "<slug>_2" duplicates on every write.
                current_labels = {
                    lbl for lbl in (entity.get("labels") or []) if _LABEL_PATTERN.match(lbl)
                }
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

                ha = await _sync_to_ha(eid, {"labels": new_labels_list})
                if not ha["synced"]:
                    errors.append(f"{eid}: {ha['detail']}")

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
