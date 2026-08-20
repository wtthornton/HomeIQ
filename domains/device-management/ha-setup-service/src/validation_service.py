"""
Home Assistant Configuration Validation Service

Validates HA configuration and provides suggestions for fixes.
Epic 32: Home Assistant Configuration Validation & Suggestions
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from homeiq_ha.client import HAClient as SharedHAClient
from homeiq_ha.client import HAWebSocketClient
from homeiq_ha.registry_writer import HARegistryWriter
from pydantic import BaseModel, Field

from .config import get_settings
from .http_client import get_http_session
from .suggestion_engine import SuggestionEngine

settings = get_settings()
logger = logging.getLogger(__name__)


class AreaReassignRefused(Exception):
    """Refusal to overwrite an already-assigned area without explicit opt-in.

    Filling an empty area and overwriting a deliberate assignment are different
    risks (`.claude/rules/friendly-names.md`): the suggestions feeding this path
    are name-derived, so silently changing a room a person chose is the
    "expensive to unpick" case. Callers opt in per item via ``allow_reassign``.
    """


class ValidationIssue(BaseModel):
    """A single validation issue with suggestions"""

    entity_id: str
    category: str
    current_area: str | None = None
    suggestions: list[dict[str, Any]] = Field(default_factory=list)
    device_id: str | None = None
    entity_name: str | None = None
    confidence: float = 0.0


class ValidationSummary(BaseModel):
    """Summary of validation results"""

    total_issues: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    scan_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ha_version: str | None = None


class ValidationResult(BaseModel):
    """Complete validation result"""

    summary: ValidationSummary
    issues: list[ValidationIssue] = Field(default_factory=list)


class ValidationService:
    """
    Service for validating Home Assistant configuration

    Detects:
    - Missing area assignments
    - Incorrect area assignments
    - Provides smart suggestions based on entity names
    """

    def __init__(self):
        self.ha_url = settings.ha_url.rstrip("/")
        self.ha_token = settings.ha_token
        self._ws: HAWebSocketClient | None = None
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.suggestion_engine = SuggestionEngine()

        # Cache for validation results (5 minute TTL)
        self._cache: dict[str, tuple[datetime, ValidationResult]] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_lock = asyncio.Lock()

    async def validate_ha_config(
        self, category: str | None = None, min_confidence: float = 0.0, use_cache: bool = True
    ) -> ValidationResult:
        """
        Validate Home Assistant configuration

        Args:
            category: Optional filter by issue category
            min_confidence: Minimum confidence score (0-100)
            use_cache: Whether to use cached results (default: True)

        Returns:
            ValidationResult with issues and suggestions
        """
        try:
            # Check cache first (only if no filters applied)
            cache_key = f"validation:{category or 'all'}:{min_confidence}"
            if use_cache and not category and min_confidence == 0:
                async with self._cache_lock:
                    if cache_key in self._cache:
                        cached_time, cached_result = self._cache[cache_key]
                        if datetime.now(UTC) - cached_time < self._cache_ttl:
                            logger.debug("Returning cached validation results")
                            return cached_result
                        else:
                            # Cache expired, remove it
                            del self._cache[cache_key]

            logger.info("Starting HA configuration validation...")

            # Fetch entities and areas from HA
            entities, areas, device_areas, ha_version = await self._fetch_ha_data()

            logger.info(f"Fetched {len(entities)} entities and {len(areas)} areas")

            # Detect issues
            issues = await self._detect_issues(entities, areas, device_areas)

            # Filter by category if specified
            if category:
                issues = [i for i in issues if i.category == category]

            # Filter by confidence
            if min_confidence > 0:
                filtered_issues = []
                for issue in issues:
                    # Keep issue if any suggestion meets confidence threshold
                    if issue.suggestions:
                        max_confidence = max(s.get("confidence", 0) for s in issue.suggestions)
                        if max_confidence >= min_confidence:
                            filtered_issues.append(issue)
                    elif issue.confidence >= min_confidence:
                        filtered_issues.append(issue)
                issues = filtered_issues

            # Generate summary
            summary = self._generate_summary(issues, ha_version)

            logger.info(f"Validation complete: {summary.total_issues} issues found")

            result = ValidationResult(summary=summary, issues=issues)

            # Cache result (only if no filters applied)
            if use_cache and not category and min_confidence == 0:
                async with self._cache_lock:
                    self._cache[cache_key] = (datetime.now(UTC), result)
                    # Clean up old cache entries
                    now = datetime.now(UTC)
                    expired_keys = [
                        k for k, (t, _) in self._cache.items() if now - t >= self._cache_ttl
                    ]
                    for k in expired_keys:
                        del self._cache[k]

            return result

        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            raise

    def clear_cache(self):
        """Clear validation cache"""
        self._cache.clear()
        logger.info("Validation cache cleared")

    async def _connection(self) -> HAWebSocketClient:
        """Return a live Home Assistant WebSocket connection, opening one on first use.

        Cached so a validation pass and the fixes that follow it share one auth
        handshake; dropped on failure so the next call reconnects.
        """
        if self._ws is None:
            # The facade derives the ws:// URL from the HTTP base URL.
            self._ws = SharedHAClient(self.ha_url, self.ha_token).ws
            await self._ws.connect()
        return self._ws

    async def _close_ws(self):
        """Close and forget the WebSocket connection"""
        if self._ws is not None:
            try:
                await self._ws.close()
            finally:
                self._ws = None

    async def _fetch_ha_data(
        self,
    ) -> tuple[list[dict], list[dict], dict[str, str], str | None]:
        """Fetch entities, areas, and the device->area map from Home Assistant"""
        session = await get_http_session()
        headers = {"Authorization": f"Bearer {self.ha_token}", "Content-Type": "application/json"}

        # Entities and areas are WebSocket registry commands (TAP-5424). The REST
        # paths this used never existed, so the entity read always fell through to
        # the states API — which carries no registry metadata (no platform, no
        # disabled_by), quietly validating against a thinner picture than the
        # caller believed. That fallback is removed rather than ported: a registry
        # that cannot be read is a failure worth surfacing, not worth degrading.
        connection = await self._connection()
        entities = await connection.list_entities()
        areas = await connection.list_areas()
        # Most HA entities carry no area override of their own — their area is
        # inherited from the device. Detection that reads only the entity-level
        # area_id is blind to exactly the swapped-dimmer shape this service
        # exists to report (TAP-6228), so the device map rides along.
        devices = await connection.list_devices()
        device_areas = {d["id"]: d["area_id"] for d in devices if d.get("id") and d.get("area_id")}

        # Get HA version
        ha_version = None
        try:
            async with session.get(
                f"{self.ha_url}/api/config", headers=headers, timeout=self.timeout
            ) as config_response:
                if config_response.status == 200:
                    config = await config_response.json()
                    ha_version = config.get("version")
        except Exception as e:
            logger.warning(f"Could not fetch HA version: {e}")

        return entities, areas, device_areas, ha_version

    async def _detect_issues(
        self,
        entities: list[dict],
        areas: list[dict],
        device_areas: dict[str, str] | None = None,
    ) -> list[ValidationIssue]:
        """Detect validation issues in entities.

        ``device_areas`` maps device_id -> area_id so the check runs against the
        entity's EFFECTIVE area: its own override, else its device's. Without it
        a device-inherited area reads as "missing" and the mismatch report never
        fires for the majority of entities (TAP-6228).
        """
        issues = []
        device_areas = device_areas or {}

        for entity in entities:
            entity_id = entity.get("entity_id")
            if not entity_id:
                continue

            entity_name = entity.get("name") or entity_id
            device_id = entity.get("device_id")
            current_area_id = entity.get("area_id") or device_areas.get(device_id or "")

            # Check for missing area assignment
            if not current_area_id:
                # Generate suggestions
                suggestions = await self.suggestion_engine.suggest_area(
                    entity_id=entity_id, entity_name=entity_name, areas=areas
                )

                if suggestions:
                    issues.append(
                        ValidationIssue(
                            entity_id=entity_id,
                            category="missing_area_assignment",
                            current_area=None,
                            suggestions=suggestions,
                            device_id=device_id,
                            entity_name=entity_name,
                            confidence=max(s.get("confidence", 0) for s in suggestions)
                            if suggestions
                            else 0,
                        )
                    )

            # The entity's NAME points at one area while it is assigned to another.
            # Worth a human's attention — this is precisely the shape of the
            # swapped-dimmer defect — but it does NOT say which side is wrong. A
            # name is a presentation artifact (`.claude/rules/friendly-names.md`),
            # so the discrepancy is reported, never resolved. It used to be raised
            # as `incorrect_area_assignment` above a >= 80 confidence gate, which
            # asserted the registry was wrong on the strength of a string and fed
            # a path that writes an area to HA.
            elif current_area_id:
                suggestions = await self.suggestion_engine.suggest_area(
                    entity_id=entity_id, entity_name=entity_name, areas=areas
                )

                if suggestions and suggestions[0].get("area_id") != current_area_id:
                    top_suggestion = suggestions[0]
                    issues.append(
                        ValidationIssue(
                            entity_id=entity_id,
                            category="name_area_mismatch",
                            current_area=current_area_id,
                            suggestions=[top_suggestion],
                            device_id=device_id,
                            entity_name=entity_name,
                            confidence=top_suggestion.get("confidence", 0),
                        )
                    )

        return issues

    def _generate_summary(
        self, issues: list[ValidationIssue], ha_version: str | None
    ) -> ValidationSummary:
        """Generate summary statistics"""
        by_category = {}
        for issue in issues:
            by_category[issue.category] = by_category.get(issue.category, 0) + 1

        return ValidationSummary(
            total_issues=len(issues),
            by_category=by_category,
            scan_timestamp=datetime.now(UTC),
            ha_version=ha_version,
        )

    async def _effective_area(self, connection: Any, entity_id: str) -> str | None:
        """The area the entity currently resolves to: its own, else its device's."""
        entry = (
            await connection.send_command(
                "config/entity_registry/get", fields={"entity_id": entity_id}
            )
            or {}
        )
        if entry.get("area_id"):
            return str(entry["area_id"])
        device_id = entry.get("device_id")
        if not device_id:
            return None
        devices = await connection.send_command("config/device_registry/list") or []
        for device in devices:
            if device.get("id") == device_id:
                return device.get("area_id")
        return None

    async def apply_fix(
        self, entity_id: str, area_id: str, allow_reassign: bool = False
    ) -> dict[str, Any]:
        """
        Apply area assignment fix to Home Assistant

        Args:
            entity_id: Entity ID to update
            area_id: Area ID to assign
            allow_reassign: Explicit per-item opt-in to overwrite an area the
                entity (or its device) already resolves to. Without it, a fix
                against an already-assigned area is refused (TAP-6228): the
                suggestions feeding this path are name-derived and must not
                silently override a human decision.

        Returns:
            Success response with details

        Raises:
            AreaReassignRefused: the entity already has a different area and
                ``allow_reassign`` was not passed.
        """
        try:
            # config/entity_registry/update is a WebSocket command; the REST path
            # this used to POST to does not exist, so no fix was ever applied.
            # HARegistryWriter is the one path that writes an area (TAP-6230): it
            # reads the value back, so "applied" here means the registry agrees,
            # and it refuses an area_id HA does not know rather than storing a
            # dangling one. Clearing the cache afterwards re-derives the view; it
            # was never a check that the write landed.
            connection = await self._connection()
            current = await self._effective_area(connection, entity_id)
            if current and current != area_id and not allow_reassign:
                raise AreaReassignRefused(
                    f"{entity_id} already resolves to area {current!r}; "
                    f"changing it to {area_id!r} needs allow_reassign=true "
                    f"per item -- name-derived suggestions never overwrite an "
                    f"existing assignment silently"
                )
            result = await HARegistryWriter(
                connection, caller="ha-setup.validation_service"
            ).set_entity_area(entity_id, area_id)
            logger.info(f"Successfully updated {entity_id} to area {area_id}")
            return {
                "success": True,
                "entity_id": entity_id,
                "area_id": area_id,
                "applied_at": datetime.now(UTC).isoformat(),
                "changed": result.wrote,
                "previous_area_id": result.previous,
            }

        except Exception as e:
            logger.error(f"Error applying fix: {e}", exc_info=True)
            await self._close_ws()
            raise

    async def apply_bulk_fixes(self, fixes: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Apply multiple area assignment fixes

        Args:
            fixes: List of dicts with entity_id and area_id. Overwriting an
                already-assigned area requires ``allow_reassign: true`` on that
                item -- there is deliberately no bulk-level override (TAP-6228).

        Returns:
            Summary of applied fixes
        """
        results = []
        applied = 0
        failed = 0

        for fix in fixes:
            entity_id = fix.get("entity_id")
            area_id = fix.get("area_id")

            if not entity_id or not area_id:
                results.append(
                    {
                        "entity_id": entity_id or "unknown",
                        "success": False,
                        "error": "Missing entity_id or area_id",
                    }
                )
                failed += 1
                continue

            try:
                await self.apply_fix(
                    entity_id, area_id, allow_reassign=bool(fix.get("allow_reassign"))
                )
                results.append({"entity_id": entity_id, "success": True})
                applied += 1
            except AreaReassignRefused as e:
                logger.warning(f"Refused reassign for {entity_id}: {e}")
                results.append(
                    {
                        "entity_id": entity_id,
                        "success": False,
                        "refused": True,
                        "error": str(e),
                    }
                )
                failed += 1
            except Exception as e:
                logger.error(f"Failed to apply fix for {entity_id}: {e}")
                results.append({"entity_id": entity_id, "success": False, "error": str(e)})
                failed += 1

        return {"success": True, "applied": applied, "failed": failed, "results": results}
