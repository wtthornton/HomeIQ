"""Device hygiene endpoints."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

DEVICE_INTELLIGENCE_URL = os.getenv("DEVICE_INTELLIGENCE_URL", "http://localhost:8019")


class HygieneIssueResponse(BaseModel):
    """API response model for a hygiene issue."""

    issue_key: str
    issue_type: str
    severity: str
    status: str
    device_id: str | None = None
    entity_id: str | None = None
    name: str | None = None
    summary: str | None = None
    suggested_action: str | None = None
    suggested_value: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    detected_at: str | None = None
    updated_at: str | None = None
    resolved_at: str | None = None


class HygieneIssueListResponse(BaseModel):
    """Response model for issue list endpoint."""

    issues: list[HygieneIssueResponse]
    count: int
    total: int


class UpdateIssueStatusRequest(BaseModel):
    """Payload for updating issue status."""

    status: str = Field(pattern="^(open|ignored|resolved)$")


class ApplyIssueActionRequest(BaseModel):
    action: str
    value: str | None = None


router = APIRouter(prefix="/api/v1/hygiene", tags=["Device Hygiene"])


async def _request_device_intelligence(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{DEVICE_INTELLIGENCE_URL}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.request(method, url, params=params, json=payload)

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except Exception:  # pragma: no cover - best effort parse
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)

    return response.json()


@router.get("/issues", response_model=HygieneIssueListResponse)
async def list_hygiene_issues(
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    issue_type: str | None = Query(default=None),
    device_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    params: dict[str, Any] = {"limit": limit}
    if status_filter:
        params["status"] = status_filter
    if severity:
        params["severity"] = severity
    if issue_type:
        params["issue_type"] = issue_type
    if device_id:
        params["device_id"] = device_id

    payload = await _request_device_intelligence("GET", "/api/hygiene/issues", params=params)

    return HygieneIssueListResponse(
        issues=[HygieneIssueResponse(**issue) for issue in payload.get("issues", [])],
        count=payload.get("count", 0),
        total=payload.get("total", 0),
    )


@router.post("/issues/{issue_key}/status", response_model=HygieneIssueResponse)
async def update_issue_status(
    issue_key: str,
    payload: UpdateIssueStatusRequest,
):
    result = await _request_device_intelligence(
        "POST",
        f"/api/hygiene/issues/{issue_key}/status",
        payload=payload.model_dump(),
    )

    return HygieneIssueResponse(**result)


@router.post("/issues/{issue_key}/actions/apply", response_model=HygieneIssueResponse)
async def apply_issue_action(
    issue_key: str,
    payload: ApplyIssueActionRequest,
):
    result = await _request_device_intelligence(
        "POST",
        f"/api/hygiene/issues/{issue_key}/actions/apply",
        payload=payload.model_dump(),
    )

    return HygieneIssueResponse(**result)

