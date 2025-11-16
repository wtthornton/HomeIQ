import os
from typing import Any, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/api/v1/ha-proxy", tags=["Home Assistant Proxy"])

HA_URL = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
HA_TOKEN = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")


async def _fetch_from_home_assistant(path: str) -> Any:
    if not HA_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HA_URL is not configured for admin-api"
        )
    if not HA_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HA token is not configured for admin-api"
        )

    url = f"{HA_URL.rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach Home Assistant: {exc}"
        ) from exc


@router.get("/states", summary="List Home Assistant entity states")
async def list_states(
    domain: Optional[str] = Query(None, description="Filter by HA domain, e.g. sensor"),
    entity_prefix: Optional[str] = Query(None, description="Filter by entity_id prefix, e.g. sensor.team_tracker"),
    limit: int = Query(1000, ge=1, le=5000, description="Max entities to return"),
) -> List[Any]:
    states = await _fetch_from_home_assistant("/api/states")

    if not isinstance(states, list):
        raise HTTPException(status_code=502, detail="Unexpected response from Home Assistant")

    filtered: List[Any] = []
    for state in states:
        entity_id = state.get("entity_id", "")
        if domain and not entity_id.startswith(f"{domain}."):
            continue
        if entity_prefix and not entity_id.startswith(entity_prefix):
            continue

        filtered.append(state)
        if len(filtered) >= limit:
            break

    return filtered


@router.get(
    "/states/{entity_id}",
    summary="Fetch a specific Home Assistant entity state",
)
async def get_state(entity_id: str) -> Any:
    normalized = entity_id if "." in entity_id else entity_id.replace("__", ".")
    try:
        return await _fetch_from_home_assistant(f"/api/states/{normalized}")
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {normalized} not found"
            ) from exc
        raise
