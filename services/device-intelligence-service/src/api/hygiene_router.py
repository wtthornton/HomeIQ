"""API endpoints for device hygiene insights and remediation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..core.database import get_db_session
from ..models.database import DeviceHygieneIssue
from ..services.remediation_service import DeviceHygieneRemediationService

router = APIRouter(prefix="/api/hygiene", tags=["Device Hygiene"])


def _serialize_issue(issue: DeviceHygieneIssue) -> Dict[str, Any]:
    return {
        "issue_key": issue.issue_key,
        "issue_type": issue.issue_type,
        "severity": issue.severity,
        "status": issue.status,
        "device_id": issue.device_id,
        "entity_id": issue.entity_id,
        "name": issue.name,
        "summary": issue.summary,
        "suggested_action": issue.suggested_action,
        "suggested_value": issue.suggested_value,
        "metadata": issue.metadata_json or {},
        "detected_at": issue.detected_at.isoformat() if isinstance(issue.detected_at, datetime) else issue.detected_at,
        "updated_at": issue.updated_at.isoformat() if isinstance(issue.updated_at, datetime) else issue.updated_at,
        "resolved_at": issue.resolved_at.isoformat() if isinstance(issue.resolved_at, datetime) else issue.resolved_at,
    }


async def get_ha_client() -> AsyncGenerator[HomeAssistantClient, None]:
    settings = Settings()
    client = HomeAssistantClient(settings.HA_URL, settings.NABU_CASA_URL, settings.HA_TOKEN)

    if not await client.connect():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Unable to connect to Home Assistant")

    await client.start_message_handler()

    try:
        yield client
    finally:
        await client.disconnect()


class IssuesResponse(BaseModel):
    issues: list[dict]
    count: int
    total: int


class StatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(open|ignored|resolved)$")


class ApplyActionRequest(BaseModel):
    action: str
    value: Optional[str] = None


@router.get("/issues", response_model=IssuesResponse)
async def list_hygiene_issues(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    severity: Optional[str] = None,
    issue_type: Optional[str] = None,
    device_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
):
    stmt = select(DeviceHygieneIssue).order_by(DeviceHygieneIssue.detected_at.desc()).limit(limit)

    if status_filter:
        stmt = stmt.where(DeviceHygieneIssue.status == status_filter)
    if severity:
        stmt = stmt.where(DeviceHygieneIssue.severity == severity)
    if issue_type:
        stmt = stmt.where(DeviceHygieneIssue.issue_type == issue_type)
    if device_id:
        stmt = stmt.where(DeviceHygieneIssue.device_id == device_id)

    result = await session.execute(stmt)
    issues = result.scalars().all()

    total_stmt = select(func.count(DeviceHygieneIssue.id))
    total_result = await session.execute(total_stmt)
    total = total_result.scalar_one()

    return IssuesResponse(
        issues=[_serialize_issue(issue) for issue in issues],
        count=len(issues),
        total=total,
    )


@router.post("/issues/{issue_key}/status", response_model=dict)
async def update_issue_status(
    issue_key: str,
    payload: StatusUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(DeviceHygieneIssue).where(DeviceHygieneIssue.issue_key == issue_key)
    )
    issue = result.scalar_one_or_none()
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    issue.status = payload.status
    if payload.status == "resolved":
        issue.resolved_at = datetime.now(timezone.utc)
    elif payload.status == "open":
        issue.resolved_at = None

    await session.commit()
    await session.refresh(issue)
    return _serialize_issue(issue)


@router.post("/issues/{issue_key}/actions/apply", response_model=dict)
async def apply_issue_action(
    issue_key: str,
    payload: ApplyActionRequest,
    session: AsyncSession = Depends(get_db_session),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
):
    result = await session.execute(
        select(DeviceHygieneIssue).where(DeviceHygieneIssue.issue_key == issue_key)
    )
    issue = result.scalar_one_or_none()
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    service = DeviceHygieneRemediationService(ha_client, session)
    try:
        applied = await service.apply_action(issue, payload.action, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not applied:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action requirements not met")

    await session.refresh(issue)
    return _serialize_issue(issue)

