"""
Name Uniqueness Validator

Fast uniqueness validation with in-memory cache and SQLite fallback.
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.database import Device, DeviceEntity

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Validation result"""
    is_unique: bool
    conflicts: list[dict[str, Any]]
    suggestions: list[str] | None = None


class NameUniquenessValidator:
    """Fast uniqueness validation with in-memory cache"""

    def __init__(self):
        self.name_cache: set[str] = set()  # In-memory cache (normalized names)
        self._cache_loaded = False

    async def load_cache(self, db_session: AsyncSession):
        """Load existing names into memory cache (one-time on startup)"""
        if self._cache_loaded:
            return

        try:
            # Load device names
            result = await db_session.execute(select(Device.name, Device.name_by_user))
            for row in result:
                if row.name:
                    self.name_cache.add(self._normalize_name(row.name))
                if row.name_by_user:
                    self.name_cache.add(self._normalize_name(row.name_by_user))

            # Load entity names
            result = await db_session.execute(
                select(DeviceEntity.name, DeviceEntity.original_name)
            )
            for row in result:
                if row.name:
                    self.name_cache.add(self._normalize_name(row.name))
                if row.original_name:
                    self.name_cache.add(self._normalize_name(row.original_name))

            self._cache_loaded = True
            logger.info(f"✅ Loaded {len(self.name_cache)} names into cache")
        except Exception as e:
            logger.warning(f"Failed to load name cache: {e}")
            self._cache_loaded = True  # Mark as loaded to avoid retry loops

    async def validate_uniqueness(
        self,
        proposed_name: str,
        device_id: str | None = None,
        entity_id: str | None = None,
        exclude_ids: list[str] | None = None,
        db_session: AsyncSession | None = None
    ) -> ValidationResult:
        """
        Fast validation using in-memory cache.
        
        Performance: <1ms (cache hit) or 5-10ms (SQLite query)
        """
        normalized_name = self._normalize_name(proposed_name)
        
        # Check cache first (fast)
        if normalized_name not in self.name_cache:
            return ValidationResult(is_unique=True, conflicts=[])

        # Name exists in cache, check if it's the same device/entity
        if db_session:
            conflicts = await self._find_conflicts(
                normalized_name, device_id, entity_id, exclude_ids, db_session
            )
            if not conflicts:
                # False positive in cache (same device), add to cache and return unique
                self.name_cache.add(normalized_name)
                return ValidationResult(is_unique=True, conflicts=[])
            
            return ValidationResult(
                is_unique=False,
                conflicts=conflicts,
                suggestions=await self._generate_alternatives(proposed_name, conflicts, db_session)
            )

        # No DB session, assume conflict if in cache
        return ValidationResult(
            is_unique=False,
            conflicts=[{"name": proposed_name}],
            suggestions=[f"{proposed_name} 1", f"{proposed_name} 2"]
        )

    async def generate_unique_variant(
        self,
        base_name: str,
        device: Device,
        existing_names: set[str] | None = None,
        db_session: AsyncSession | None = None
    ) -> str:
        """
        Generate unique variant with minimal changes.
        
        Strategies (in order):
        1. Add location: "Light" → "Office Light"
        2. Add descriptive: "Light" → "Main Light"
        3. Add number: "Light" → "Light 1" (last resort)
        
        Performance: <5ms
        """
        if existing_names is None:
            existing_names = self.name_cache.copy()

        # Strategy 1: Add location
        if device.area_name:
            location_name = f"{device.area_name} {base_name}"
            normalized = self._normalize_name(location_name)
            if normalized not in existing_names:
                # Also check in database if session provided
                if db_session:
                    validation = await self.validate_uniqueness(location_name, device.id, None, None, db_session)
                    if validation.is_unique:
                        return location_name
                else:
                    return location_name

        # Strategy 2: Add descriptive modifier
        modifiers = ["Main", "Primary", "Secondary", "Back", "Front", "Left", "Right"]
        for modifier in modifiers:
            modified_name = f"{modifier} {base_name}"
            normalized = self._normalize_name(modified_name)
            if normalized not in existing_names:
                return modified_name

        # Strategy 3: Add number suffix (last resort)
        for i in range(1, 100):
            numbered_name = f"{base_name} {i}"
            normalized = self._normalize_name(numbered_name)
            if normalized not in existing_names:
                return numbered_name

        # Fallback: Add timestamp or random suffix
        return f"{base_name} {device.id[:8]}"

    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison (case-insensitive, remove punctuation)"""
        import re
        # Lowercase, remove punctuation, normalize whitespace
        normalized = name.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    async def _find_conflicts(
        self,
        normalized_name: str,
        device_id: str | None,
        entity_id: str | None,
        exclude_ids: list[str] | None,
        db_session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Find conflicting device/entity names in database"""
        conflicts = []
        exclude_ids = exclude_ids or []

        # Check devices
        if device_id not in exclude_ids:
            result = await db_session.execute(
                select(Device.id, Device.name, Device.name_by_user).where(
                    (Device.id != device_id) if device_id else True
                )
            )
            for row in result:
                if (row.name and self._normalize_name(row.name) == normalized_name) or \
                   (row.name_by_user and self._normalize_name(row.name_by_user) == normalized_name):
                    conflicts.append({
                        "type": "device",
                        "id": row.id,
                        "name": row.name or row.name_by_user
                    })

        # Check entities
        if entity_id not in exclude_ids:
            result = await db_session.execute(
                select(DeviceEntity.entity_id, DeviceEntity.name, DeviceEntity.original_name).where(
                    (DeviceEntity.entity_id != entity_id) if entity_id else True
                )
            )
            for row in result:
                if (row.name and self._normalize_name(row.name) == normalized_name) or \
                   (row.original_name and self._normalize_name(row.original_name) == normalized_name):
                    conflicts.append({
                        "type": "entity",
                        "id": row.entity_id,
                        "name": row.name or row.original_name
                    })

        return conflicts

    async def _generate_alternatives(
        self,
        base_name: str,
        conflicts: list[dict[str, Any]],
        db_session: AsyncSession
    ) -> list[str]:
        """Generate alternative name suggestions"""
        suggestions = []
        
        # Add number suffix
        for i in range(1, 6):
            suggestions.append(f"{base_name} {i}")
        
        # Add location if available from conflicts
        # (This is a simple implementation - could be enhanced)
        
        return suggestions[:3]  # Return top 3

    async def refresh_cache(self, db_session: AsyncSession):
        """Refresh cache (call periodically or on-demand)"""
        self._cache_loaded = False
        self.name_cache.clear()
        await self.load_cache(db_session)

