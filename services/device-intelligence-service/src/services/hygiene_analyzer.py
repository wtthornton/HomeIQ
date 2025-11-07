"""Device and entity hygiene analyzer."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.ha_client import HAArea, HADevice, HAEntity
from ..models.database import DeviceHygieneIssue

logger = logging.getLogger(__name__)


PLACEHOLDER_PATTERNS = (
    re.compile(r"^unnamed( device)?$", re.IGNORECASE),
    re.compile(r"^default( device)?$", re.IGNORECASE),
    re.compile(r"^new device$", re.IGNORECASE),
    re.compile(r"^device [0-9]+$", re.IGNORECASE),
    re.compile(r"^light [0-9]+$", re.IGNORECASE),
)

STALE_DISCOVERY_AGE = timedelta(days=30)


@dataclass
class HygieneFinding:
    """Intermediate hygiene finding representation."""

    issue_key: str
    issue_type: str
    severity: str
    name: Optional[str]
    summary: str
    suggested_action: Optional[str]
    suggested_value: Optional[str]
    device_id: Optional[str]
    entity_id: Optional[str]
    metadata: Dict[str, Any]


class DeviceHygieneAnalyzer:
    """Analyzes Home Assistant registries for hygiene issues."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def analyze(
        self,
        ha_devices: Sequence[HADevice],
        ha_entities: Sequence[HAEntity],
        areas: Sequence[HAArea],
    ) -> List[HygieneFinding]:
        """Run analysis and persist findings."""

        area_lookup = {area.area_id: area for area in areas if area.area_id}
        entity_lookup: Dict[str, List[HAEntity]] = {}
        for entity in ha_entities:
            if entity.device_id:
                entity_lookup.setdefault(entity.device_id, []).append(entity)

        findings: List[HygieneFinding] = []
        findings.extend(self._detect_duplicate_names(ha_devices, area_lookup, entity_lookup))
        findings.extend(self._detect_placeholder_names(ha_devices, area_lookup, entity_lookup))
        findings.extend(self._detect_unassigned_areas(ha_devices, area_lookup, entity_lookup))
        findings.extend(self._detect_stale_discoveries(ha_devices, entity_lookup))
        findings.extend(self._detect_disabled_entities(ha_entities))

        await self._persist_findings(findings)
        logger.info("🧹 Hygiene analyzer produced %s findings", len(findings))
        return findings

    def _detect_duplicate_names(
        self,
        ha_devices: Sequence[HADevice],
        areas: Dict[str, HAArea],
        entity_lookup: Dict[str, List[HAEntity]],
    ) -> List[HygieneFinding]:
        by_name: Dict[str, List[HADevice]] = {}
        for device in ha_devices:
            candidate = device.name_by_user or device.name
            normalized = self._normalize_name(candidate)
            if not normalized:
                continue
            by_name.setdefault(normalized, []).append(device)

        findings: List[HygieneFinding] = []
        for normalized, devices in by_name.items():
            if len(devices) < 2:
                continue
            conflicts = [d.id for d in devices]
            for device in devices:
                suggestion = self._suggest_device_name(device, areas)
                findings.append(
                    HygieneFinding(
                        issue_key=f"duplicate_name:{device.id}",
                        issue_type="duplicate_name",
                        severity="high",
                        name=device.name_by_user or device.name,
                        summary="Multiple devices share the same name, which breaks automation targeting.",
                        suggested_action="rename_device",
                        suggested_value=suggestion,
                        device_id=device.id,
                        entity_id=None,
                        metadata={
                            "conflicting_device_ids": [cid for cid in conflicts if cid != device.id],
                            "entities": [e.entity_id for e in entity_lookup.get(device.id, [])],
                            "normalized_name": normalized,
                        },
                    )
                )
        return findings

    def _detect_placeholder_names(
        self,
        ha_devices: Sequence[HADevice],
        areas: Dict[str, HAArea],
        entity_lookup: Dict[str, List[HAEntity]],
    ) -> List[HygieneFinding]:
        findings: List[HygieneFinding] = []
        for device in ha_devices:
            candidate = device.name_by_user or device.name
            if not candidate:
                continue
            if any(pattern.match(candidate) for pattern in PLACEHOLDER_PATTERNS):
                suggestion = self._suggest_device_name(device, areas)
                findings.append(
                    HygieneFinding(
                        issue_key=f"placeholder_name:{device.id}",
                        issue_type="placeholder_name",
                        severity="medium",
                        name=candidate,
                        summary="Device name is a default placeholder and should be clarified.",
                        suggested_action="rename_device",
                        suggested_value=suggestion,
                        device_id=device.id,
                        entity_id=None,
                        metadata={
                            "entities": [e.entity_id for e in entity_lookup.get(device.id, [])],
                            "integration": device.integration,
                        },
                    )
                )
        return findings

    def _detect_unassigned_areas(
        self,
        ha_devices: Sequence[HADevice],
        areas: Dict[str, HAArea],
        entity_lookup: Dict[str, List[HAEntity]],
    ) -> List[HygieneFinding]:
        findings: List[HygieneFinding] = []
        for device in ha_devices:
            if device.area_id:
                continue
            suggested = device.suggested_area
            suggested_name = areas.get(suggested).name if suggested and suggested in areas else None
            findings.append(
                HygieneFinding(
                    issue_key=f"unassigned_area:{device.id}",
                    issue_type="missing_area",
                    severity="medium",
                    name=device.name_by_user or device.name,
                    summary="Device is not assigned to an area, reducing location context for automations.",
                    suggested_action="assign_area",
                    suggested_value=suggested_name or suggested,
                    device_id=device.id,
                    entity_id=None,
                    metadata={
                        "suggested_area_id": suggested,
                        "entities": [e.entity_id for e in entity_lookup.get(device.id, [])],
                    },
                )
            )
        return findings

    def _detect_stale_discoveries(
        self,
        ha_devices: Sequence[HADevice],
        entity_lookup: Dict[str, List[HAEntity]],
    ) -> List[HygieneFinding]:
        now = datetime.now(timezone.utc)
        findings: List[HygieneFinding] = []
        for device in ha_devices:
            age = now - device.created_at
            if age < STALE_DISCOVERY_AGE:
                continue
            if device.config_entries:
                continue
            entities = entity_lookup.get(device.id, [])
            if entities:
                continue
            findings.append(
                HygieneFinding(
                    issue_key=f"stale_discovery:{device.id}",
                    issue_type="pending_configuration",
                    severity="medium",
                    name=device.name_by_user or device.name,
                    summary="Device was discovered weeks ago but never configured.",
                    suggested_action="start_config_flow",
                    suggested_value=device.integration,
                    device_id=device.id,
                    entity_id=None,
                    metadata={
                        "age_days": round(age.total_seconds() / 86400, 1),
                        "integration": device.integration,
                    },
                )
            )
        return findings

    def _detect_disabled_entities(self, ha_entities: Sequence[HAEntity]) -> List[HygieneFinding]:
        findings: List[HygieneFinding] = []
        for entity in ha_entities:
            if not entity.disabled_by:
                continue
            if entity.entity_category and entity.entity_category.lower() in {"diagnostic", "config"}:
                continue
            findings.append(
                HygieneFinding(
                    issue_key=f"disabled_entity:{entity.entity_id}",
                    issue_type="disabled_entity",
                    severity="low",
                    name=entity.entity_id,
                    summary="Entity is disabled and may break automations that reference it.",
                    suggested_action="review_entity_state",
                    suggested_value=entity.disabled_by,
                    device_id=entity.device_id,
                    entity_id=entity.entity_id,
                    metadata={
                        "disabled_by": entity.disabled_by,
                        "entity_category": entity.entity_category,
                        "domain": entity.domain,
                    },
                )
            )
        return findings

    async def _persist_findings(self, findings: Iterable[HygieneFinding]) -> None:
        finding_list = list(findings)
        existing_result = await self.session.execute(select(DeviceHygieneIssue))
        existing = {issue.issue_key: issue for issue in existing_result.scalars()}

        current_keys = {finding.issue_key for finding in finding_list}
        now = datetime.now(timezone.utc)

        for issue_key, issue in existing.items():
            if issue_key in current_keys:
                continue
            if issue.status == "open":
                issue.status = "resolved"
                issue.resolved_at = now
                issue.updated_at = now

        for finding in finding_list:
            issue = existing.get(finding.issue_key)
            if issue:
                issue.issue_type = finding.issue_type
                issue.severity = finding.severity
                issue.name = finding.name
                issue.suggested_action = finding.suggested_action
                issue.suggested_value = finding.suggested_value
                issue.summary = finding.summary
                issue.metadata_json = finding.metadata
                issue.device_id = finding.device_id
                issue.entity_id = finding.entity_id
                issue.updated_at = now
                if issue.status not in {"ignored"}:
                    issue.status = "open"
                    issue.resolved_at = None
            else:
                issue = DeviceHygieneIssue(
                    issue_key=finding.issue_key,
                    issue_type=finding.issue_type,
                    severity=finding.severity,
                    status="open",
                    name=finding.name,
                    suggested_action=finding.suggested_action,
                    suggested_value=finding.suggested_value,
                    summary=finding.summary,
                    metadata_json=finding.metadata,
                    device_id=finding.device_id,
                    entity_id=finding.entity_id,
                    detected_at=now,
                )
                self.session.add(issue)

        await self.session.commit()

    def _normalize_name(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        simplified = re.sub(r"[^a-z0-9]+", " ", value.lower())
        simplified = re.sub(r"\s+", " ", simplified).strip()
        return simplified or None

    def _suggest_device_name(self, device: HADevice, areas: Dict[str, HAArea]) -> Optional[str]:
        parts: List[str] = []
        if device.area_id and device.area_id in areas:
            parts.append(areas[device.area_id].name)
        elif device.suggested_area and device.suggested_area in areas:
            parts.append(areas[device.suggested_area].name)
        if device.manufacturer:
            parts.append(device.manufacturer.split()[0])
        if device.model:
            parts.append(device.model.split()[0])
        elif device.integration:
            parts.append(device.integration.title())
        return " ".join(parts) if parts else None


