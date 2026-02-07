"""
Setup Issue Detector
Phase 2.3: Detect common setup problems
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("device-setup-assistant")


class SetupIssueDetector:
    """Detects setup issues for devices"""

    def __init__(self, ha_client: 'HAClient'):
        """
        Initialize issue detector with a shared HAClient.

        Args:
            ha_client: Shared Home Assistant API client instance
        """
        self.ha_client = ha_client
        self.ha_url = ha_client.ha_url
        self.ha_token = ha_client.ha_token

    async def detect_setup_issues(
        self,
        device_id: str,
        device_name: str,
        entity_ids: list[str],
        expected_entities: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Detect setup issues for a device.

        Args:
            device_id: Device identifier
            device_name: Device name
            entity_ids: List of entity IDs for this device
            expected_entities: List of expected entity IDs (optional)

        Returns:
            List of detected issues
        """
        issues = []

        try:
            session = await self.ha_client._get_session()

            # Check 1: No entities at all (must come before activity check)
            if not entity_ids:
                issues.append({
                    "type": "no_entities",
                    "severity": "error",
                    "message": f"{device_name} has no entities configured",
                    "solution": "Check device integration configuration",
                    "details": {
                        "device_id": device_id
                    }
                })
            else:
                # Check 2: Device not responding (no events in 24h) - only if entities exist
                activity_result = await self._is_device_active(session, entity_ids)
                if activity_result is not None and not activity_result["active"]:
                    issues.append({
                        "type": "device_not_responding",
                        "severity": "error",
                        "message": f"{device_name} has not sent any events in {activity_result['hours_since']:.0f} hours",
                        "solution": "Check device power and network connection",
                        "details": {
                            "device_id": device_id,
                            "hours_since_last_event": round(activity_result["hours_since"])
                        }
                    })

            # Check 3: Missing expected entities
            if expected_entities:
                missing = set(expected_entities) - set(entity_ids)
                if missing:
                    issues.append({
                        "type": "missing_entities",
                        "severity": "warning",
                        "message": f"Expected entities not found: {', '.join(missing)}",
                        "solution": "Check device configuration in Home Assistant",
                        "details": {
                            "missing_entities": list(missing),
                            "found_entities": entity_ids
                        }
                    })

            # Check 4: All entities disabled
            if entity_ids:
                disabled_count = await self._count_disabled_entities(session, entity_ids)
                if disabled_count == len(entity_ids):
                    issues.append({
                        "type": "all_entities_disabled",
                        "severity": "warning",
                        "message": f"All {disabled_count} entities for {device_name} are disabled",
                        "solution": "Enable entities in Home Assistant entity registry",
                        "details": {
                            "disabled_count": disabled_count,
                            "total_entities": len(entity_ids)
                        }
                    })

        except Exception as e:
            logger.error(f"Error detecting setup issues for {device_id}: {e}")
            issues.append({
                "type": "detection_error",
                "severity": "warning",
                "message": "Failed to detect setup issues due to an internal error",
                "solution": "Check Home Assistant connection",
                "details": {}
            })

        return issues

    async def _is_device_active(
        self, session, entity_ids: list[str]
    ) -> dict[str, Any] | None:
        """
        Check if device has sent events in last 24 hours.
        Checks ALL entities, returns True if ANY is active.

        Returns:
            dict with 'active' (bool) and 'hours_since' (float), or None if check failed.
        """
        if not entity_ids:
            return None

        max_hours_since = 0.0
        any_active = False

        for entity_id in entity_ids:
            try:
                state_url = f"{self.ha_url}/api/states/{entity_id}"

                async with session.get(state_url) as response:
                    if response.status == 200:
                        state_data = await response.json()
                        last_changed = state_data.get("last_changed")
                        if last_changed:
                            try:
                                dt = datetime.fromisoformat(last_changed.replace("Z", "+00:00"))
                                hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                                max_hours_since = max(max_hours_since, hours_ago)
                                if hours_ago < 24:
                                    any_active = True
                            except Exception:
                                pass
            except Exception as e:
                logger.error(f"Error checking activity for entity {entity_id}: {e}")
                return None

        return {"active": any_active, "hours_since": max_hours_since}

    async def _count_disabled_entities(
        self, session, entity_ids: list[str]
    ) -> int:
        """Count disabled entities"""
        try:
            registry_url = f"{self.ha_url}/api/config/entity_registry/list"
            async with session.get(registry_url) as response:
                if response.status == 200:
                    registry_data = await response.json()
                    entities = registry_data if isinstance(registry_data, list) else registry_data.get("entities", [])

                    # Build a dict for O(1) lookups instead of O(N*M) scanning
                    entity_map = {
                        e.get("entity_id"): e for e in entities if e.get("entity_id")
                    }

                    disabled_count = 0
                    for entity_id in entity_ids:
                        entity_info = entity_map.get(entity_id)
                        if entity_info and entity_info.get("disabled_by") is not None:
                            disabled_count += 1
                    return disabled_count
        except Exception as e:
            logger.error(f"Error counting disabled entities: {e}")
        return 0
