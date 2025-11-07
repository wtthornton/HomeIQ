"""Device hygiene endpoints."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

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
    device_id: Optional[str] = None
    entity_id: Optional[str] = None
    name: Optional[str] = None
    summary: Optional[str] = None
    suggested_action: Optional[str] = None
    suggested_value: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    detected_at: Optional[str] = None
    updated_at: Optional[str] = None
    resolved_at: Optional[str] = None


class HygieneIssueListResponse(BaseModel):
    """Response model for issue list endpoint."""

    issues: List[HygieneIssueResponse]
    count: int
    total: int


class UpdateIssueStatusRequest(BaseModel):
    """Payload for updating issue status."""

    status: str = Field(pattern="^(open|ignored|resolved)$")


class ApplyIssueActionRequest(BaseModel):
    action: str
    value: Optional[str] = None


router = APIRouter(prefix="/api/v1/hygiene", tags=["Device Hygiene"])


async def _request_device_intelligence(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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
    status_filter: Optional[str] = Query(default=None, alias="status"),
    severity: Optional[str] = Query(default=None),
    issue_type: Optional[str] = Query(default=None),
    device_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    params: Dict[str, Any] = {"limit": limit}
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

