"""Remediation helpers for device hygiene issues."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.ha_client import HomeAssistantClient
from ..models.database import DeviceHygieneIssue


class DeviceHygieneRemediationService:
    """Apply Home Assistant remediation actions with guardrails."""

    def __init__(self, ha_client: HomeAssistantClient, session: AsyncSession):
        self._ha_client = ha_client
        self._session = session

    async def apply_action(
        self,
        issue: DeviceHygieneIssue,
        action: str,
        value: str | None = None,
    ) -> bool:
        if action == "rename_device":
            return await self._rename_device(issue, value)
        if action == "assign_area":
            return await self._assign_area(issue, value)
        if action == "review_entity_state":
            return await self._enable_entity(issue)
        if action == "start_config_flow":
            return await self._start_config_flow(issue, value)
        msg = f"Unsupported remediation action: {action}"
        raise ValueError(msg)

    async def _rename_device(
        self, issue: DeviceHygieneIssue, name: str | None,
    ) -> bool:
        if not issue.device_id or not name or not name.strip():
            return False

        result = await self._ha_client.update_device_registry_entry(
            issue.device_id,
            name=name.strip(),
        )
        return await self._mark_resolved(issue, {"applied_value": result.get("name", name.strip())})

    async def _assign_area(
        self, issue: DeviceHygieneIssue, area_id: str | None,
    ) -> bool:
        if not issue.device_id or not area_id:
            return False

        await self._ha_client.update_device_registry_entry(
            issue.device_id,
            area_id=area_id,
        )
        return await self._mark_resolved(issue, {"area_id": area_id})

    async def _enable_entity(self, issue: DeviceHygieneIssue) -> bool:
        if not issue.entity_id:
            return False

        await self._ha_client.update_entity_registry_entry(
            issue.entity_id,
            disabled_by=None,
        )
        return await self._mark_resolved(issue, {})

    async def _start_config_flow(
        self, issue: DeviceHygieneIssue, handler: str | None,
    ) -> bool:
        integration = handler or (issue.metadata_json or {}).get("integration")
        if not integration:
            return False

        await self._ha_client.start_config_flow(integration)
        return await self._mark_resolved(issue, {"config_flow": integration})

    async def _mark_resolved(self, issue: DeviceHygieneIssue, metadata_update: dict) -> bool:
        now = datetime.now(timezone.utc)
        issue.status = "resolved"
        issue.updated_at = now
        issue.resolved_at = now
        metadata = issue.metadata_json or {}
        metadata.update(metadata_update)
        issue.metadata_json = metadata

        try:
            await self._session.commit()
            return True
        except SQLAlchemyError:
            await self._session.rollback()
            raise
