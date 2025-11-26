"""
Setup Issue Detector
Phase 2.3: Detect common setup problems
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class SetupIssueDetector:
    """Detects setup issues for devices"""

    def __init__(self, ha_url: str, ha_token: str):
        """
        Initialize issue detector.
        
        Args:
            ha_url: Home Assistant URL
            ha_token: Home Assistant access token
        """
        self.ha_url = ha_url.rstrip('/')
        self.ha_token = ha_token
        self.headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json"
        }
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HA API session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
                raise_for_status=False
            )
        return self._session

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
            session = await self._get_session()
            
            # Check 1: Device not responding (no events in 24h)
            if not await self._is_device_active(session, entity_ids):
                issues.append({
                    "type": "device_not_responding",
                    "severity": "error",
                    "message": f"{device_name} has not sent any events in 24 hours",
                    "solution": "Check device power and network connection",
                    "details": {
                        "device_id": device_id,
                        "hours_since_last_event": 24
                    }
                })
            
            # Check 2: Missing expected entities
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
            
            # Check 3: No entities at all
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
            
            # Check 4: All entities disabled
            disabled_count = await self._count_disabled_entities(session, entity_ids)
            if disabled_count == len(entity_ids) and len(entity_ids) > 0:
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
                "message": f"Failed to detect setup issues: {str(e)}",
                "solution": "Check Home Assistant connection",
                "details": {}
            })
        
        return issues

    async def _is_device_active(self, session: aiohttp.ClientSession, entity_ids: list[str]) -> bool:
        """Check if device has sent events in last 24 hours"""
        if not entity_ids:
            return False
        
        try:
            # Check last changed time for first entity
            entity_id = entity_ids[0]
            state_url = f"{self.ha_url}/api/states/{entity_id}"
            
            async with session.get(state_url) as response:
                if response.status == 200:
                    state_data = await response.json()
                    last_changed = state_data.get("last_changed")
                    if last_changed:
                        try:
                            dt = datetime.fromisoformat(last_changed.replace("Z", "+00:00"))
                            hours_ago = (datetime.now(dt.tzinfo) - dt).total_seconds() / 3600
                            return hours_ago < 24
                        except Exception:
                            pass
            return False
        except Exception:
            return False

    async def _count_disabled_entities(self, session: aiohttp.ClientSession, entity_ids: list[str]) -> int:
        """Count disabled entities"""
        try:
            registry_url = f"{self.ha_url}/api/config/entity_registry/list"
            async with session.get(registry_url) as response:
                if response.status == 200:
                    registry_data = await response.json()
                    entities = registry_data.get("entities", [])
                    
                    disabled_count = 0
                    for entity_id in entity_ids:
                        entity_info = next(
                            (e for e in entities if e.get("entity_id") == entity_id),
                            None
                        )
                        if entity_info and entity_info.get("disabled_by") is not None:
                            disabled_count += 1
                    return disabled_count
        except Exception:
            pass
        return 0

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

