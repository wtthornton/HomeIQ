"""
Versioning Service for Automation Management

Epic 51, Story 51.11: Add ID/Versioning Strategy & State Restoration

Provides:
- Deterministic ID mapping (alias → config_id → entity_id)
- Version history with diffs, scores, approval tracking
- Robust state restoration (snapshot_entities enumeration)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

import difflib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.ha_client import HomeAssistantClient
from ..database.models import AutomationVersion

logger = logging.getLogger(__name__)


class VersioningService:
    """
    Service for managing automation versions, IDs, and state restoration.
    
    Features:
    - Deterministic ID mapping (alias → config_id → entity_id)
    - Version history with diffs
    - Quality score tracking
    - Approval tracking
    - State restoration via snapshot_entities
    """

    def __init__(
        self,
        db: AsyncSession,
        ha_client: HomeAssistantClient | None = None
    ):
        """
        Initialize versioning service.
        
        Args:
            db: Database session
            ha_client: Home Assistant client (optional, for state restoration)
        """
        self.db = db
        self.ha_client = ha_client

    async def create_version(
        self,
        suggestion_id: int,
        automation_id: str,
        automation_yaml: str,
        alias: str | None = None,
        config_id: str | None = None,
        validation_score: float | None = None,
        safety_score: float | None = None,
        approval_status: str = "pending",
        approved_by: str | None = None,
        deployed_by: str | None = None
    ) -> AutomationVersion:
        """
        Create a new automation version with diff calculation.
        
        Args:
            suggestion_id: Suggestion ID
            automation_id: Home Assistant entity_id
            automation_yaml: YAML content
            alias: Automation alias (for mapping)
            config_id: Home Assistant config_id (for mapping)
            validation_score: Quality score from validation
            safety_score: Safety score
            approval_status: Approval status (approved, rejected, pending)
            approved_by: User/API key who approved
            deployed_by: User/API key who deployed
        
        Returns:
            Created AutomationVersion instance
        """
        # Get previous version to calculate diff
        previous_version = await self.get_latest_version(suggestion_id, automation_id)
        version_number = 1
        yaml_diff = None
        
        if previous_version:
            version_number = previous_version.version_number + 1
            yaml_diff = self._calculate_diff(
                previous_version.automation_yaml,
                automation_yaml
            )
            # Mark previous version as inactive
            previous_version.is_active = False
            await self.db.commit()
        
        # Create snapshot of entity states for restoration
        snapshot_entities = None
        if self.ha_client:
            try:
                snapshot_entities = await self._create_snapshot(automation_id)
            except Exception as e:
                logger.warning(f"Failed to create snapshot for {automation_id}: {e}")
        
        # Create new version
        version = AutomationVersion(
            suggestion_id=suggestion_id,
            automation_id=automation_id,
            config_id=config_id,
            alias=alias,
            version_number=version_number,
            automation_yaml=automation_yaml,
            yaml_diff=yaml_diff,
            validation_score=validation_score,
            safety_score=safety_score,
            approval_status=approval_status,
            approved_by=approved_by,
            deployed_by=deployed_by,
            is_active=True,
            snapshot_entities=json.dumps(snapshot_entities) if snapshot_entities else None
        )
        
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        
        logger.info(
            f"Created version {version_number} for automation {automation_id} "
            f"(suggestion {suggestion_id})"
        )
        
        return version

    async def get_latest_version(
        self,
        suggestion_id: int | None = None,
        automation_id: str | None = None
    ) -> AutomationVersion | None:
        """
        Get the latest version for a suggestion or automation.
        
        Args:
            suggestion_id: Suggestion ID (optional)
            automation_id: Automation ID (optional)
        
        Returns:
            Latest AutomationVersion or None
        """
        query = select(AutomationVersion)
        
        if suggestion_id:
            query = query.where(AutomationVersion.suggestion_id == suggestion_id)
        elif automation_id:
            query = query.where(AutomationVersion.automation_id == automation_id)
        else:
            return None
        
        query = query.order_by(AutomationVersion.version_number.desc())
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_version_history(
        self,
        automation_id: str,
        limit: int = 10
    ) -> list[AutomationVersion]:
        """
        Get version history for an automation.
        
        Args:
            automation_id: Automation ID
            limit: Maximum number of versions to return
        
        Returns:
            List of AutomationVersion instances (newest first)
        """
        query = (
            select(AutomationVersion)
            .where(AutomationVersion.automation_id == automation_id)
            .order_by(AutomationVersion.version_number.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def restore_state(
        self,
        automation_id: str,
        version_number: int | None = None
    ) -> dict[str, Any]:
        """
        Restore entity states from a version's snapshot.
        
        Args:
            automation_id: Automation ID
            version_number: Version number to restore (default: latest)
        
        Returns:
            Dictionary with restoration result
        """
        if not self.ha_client:
            raise ValueError("HA client required for state restoration")
        
        # Get version
        if version_number:
            query = (
                select(AutomationVersion)
                .where(
                    AutomationVersion.automation_id == automation_id,
                    AutomationVersion.version_number == version_number
                )
            )
            result = await self.db.execute(query)
            version = result.scalar_one_or_none()
        else:
            version = await self.get_latest_version(automation_id=automation_id)
        
        if not version:
            raise ValueError(f"Version not found for automation {automation_id}")
        
        if not version.snapshot_entities:
            raise ValueError(f"No snapshot available for version {version.version_number}")
        
        # Parse snapshot
        snapshot = json.loads(version.snapshot_entities)
        
        # Restore states
        restored = []
        failed = []
        
        for entity_state in snapshot:
            try:
                entity_id = entity_state.get("entity_id")
                state = entity_state.get("state")
                attributes = entity_state.get("attributes", {})
                
                # Restore state via HA client
                # Note: This is a simplified example - actual restoration may require
                # service calls depending on entity type
                await self.ha_client.set_state(
                    entity_id=entity_id,
                    state=state,
                    attributes=attributes
                )
                restored.append(entity_id)
            except Exception as e:
                logger.error(f"Failed to restore {entity_state.get('entity_id')}: {e}")
                failed.append(entity_state.get("entity_id"))
        
        return {
            "restored": restored,
            "failed": failed,
            "version_number": version.version_number
        }

    def _calculate_diff(self, old_yaml: str, new_yaml: str) -> str:
        """
        Calculate unified diff between two YAML strings.
        
        Args:
            old_yaml: Previous YAML
            new_yaml: New YAML
        
        Returns:
            Unified diff string
        """
        old_lines = old_yaml.splitlines(keepends=True)
        new_lines = new_yaml.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="previous",
            tofile="current",
            lineterm=""
        )
        
        return "".join(diff)

    async def _create_snapshot(self, automation_id: str) -> list[dict[str, Any]]:
        """
        Create snapshot of entity states for an automation.
        
        Args:
            automation_id: Automation ID
        
        Returns:
            List of entity state dictionaries
        """
        if not self.ha_client:
            return []
        
        try:
            # Get automation from HA to find related entities
            automation = await self.ha_client.get_automation(automation_id)
            
            if not automation:
                return []
            
            # Extract entity IDs from automation
            entity_ids = self._extract_entity_ids_from_automation(automation)
            
            # Get states for all entities
            snapshot = []
            for entity_id in entity_ids:
                try:
                    state = await self.ha_client.get_state(entity_id)
                    if state:
                        snapshot.append({
                            "entity_id": entity_id,
                            "state": state.get("state"),
                            "attributes": state.get("attributes", {})
                        })
                except Exception as e:
                    logger.warning(f"Failed to get state for {entity_id}: {e}")
            
            return snapshot
        except Exception as e:
            logger.error(f"Failed to create snapshot for {automation_id}: {e}")
            return []

    def _extract_entity_ids_from_automation(self, automation: dict[str, Any]) -> list[str]:
        """
        Extract entity IDs from automation data.
        
        Args:
            automation: Automation dictionary from HA
        
        Returns:
            List of entity IDs
        """
        entity_ids = []
        
        # Extract from triggers
        triggers = automation.get("trigger", [])
        for trigger in triggers:
            if "entity_id" in trigger:
                eid = trigger["entity_id"]
                if isinstance(eid, str):
                    entity_ids.append(eid)
                elif isinstance(eid, list):
                    entity_ids.extend(eid)
        
        # Extract from conditions
        conditions = automation.get("condition", [])
        for condition in conditions:
            if "entity_id" in condition:
                eid = condition["entity_id"]
                if isinstance(eid, str):
                    entity_ids.append(eid)
                elif isinstance(eid, list):
                    entity_ids.extend(eid)
        
        # Extract from actions
        actions = automation.get("action", [])
        for action in actions:
            if "entity_id" in action:
                eid = action["entity_id"]
                if isinstance(eid, str):
                    entity_ids.append(eid)
                elif isinstance(eid, list):
                    entity_ids.extend(eid)
            if "target" in action and "entity_id" in action["target"]:
                eid = action["target"]["entity_id"]
                if isinstance(eid, str):
                    entity_ids.append(eid)
                elif isinstance(eid, list):
                    entity_ids.extend(eid)
        
        return list(set(entity_ids))  # Remove duplicates

    async def get_id_mapping(
        self,
        alias: str | None = None,
        config_id: str | None = None,
        automation_id: str | None = None
    ) -> dict[str, str | None]:
        """
        Get ID mapping (alias → config_id → entity_id).
        
        Args:
            alias: Automation alias
            config_id: Config ID
            automation_id: Entity ID
        
        Returns:
            Dictionary with mapping
        """
        query = select(AutomationVersion)
        
        if alias:
            query = query.where(AutomationVersion.alias == alias)
        elif config_id:
            query = query.where(AutomationVersion.config_id == config_id)
        elif automation_id:
            query = query.where(AutomationVersion.automation_id == automation_id)
        else:
            return {}
        
        query = query.where(AutomationVersion.is_active == True)
        query = query.order_by(AutomationVersion.version_number.desc())
        
        result = await self.db.execute(query)
        version = result.scalar_one_or_none()
        
        if not version:
            return {}
        
        return {
            "alias": version.alias,
            "config_id": version.config_id,
            "automation_id": version.automation_id
        }

