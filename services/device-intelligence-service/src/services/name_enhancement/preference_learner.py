"""
Preference Learner

Lightweight preference learning from user customizations (no heavy ML).
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.database import Device, DeviceEntity, NamePreference
from .name_generator import NameSuggestion

logger = logging.getLogger(__name__)


class PreferenceLearner:
    """Lightweight preference learning (no heavy ML)"""

    def __init__(self):
        self.patterns: dict[str, Any] = {}  # In-memory patterns
        self._patterns_loaded = False

    async def load_patterns(self, db_session: AsyncSession):
        """Load preference patterns from database"""
        if self._patterns_loaded:
            return

        try:
            result = await db_session.execute(select(NamePreference))
            preferences = result.scalars().all()

            for pref in preferences:
                pattern_type = pref.pattern_type
                if pattern_type not in self.patterns:
                    self.patterns[pattern_type] = []

                # Parse JSON pattern_data
                try:
                    if isinstance(pref.pattern_data, str):
                        pattern_data = json.loads(pref.pattern_data)
                    else:
                        pattern_data = pref.pattern_data or {}
                    
                    self.patterns[pattern_type].append({
                        "data": pattern_data,
                        "confidence": pref.confidence,
                        "count": pref.learned_from_count
                    })
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse pattern data: {e}")

            self._patterns_loaded = True
            logger.info(f"✅ Loaded {len(preferences)} preference patterns")
        except Exception as e:
            logger.warning(f"Failed to load preference patterns: {e}")
            self._patterns_loaded = True  # Mark as loaded to avoid retry loops

    async def learn_from_customization(
        self,
        original_name: str,
        user_customized_name: str,
        device: Device,
        entity: DeviceEntity | None = None,
        db_session: AsyncSession | None = None
    ) -> None:
        """
        Learn simple patterns from user customizations.
        
        Examples:
        - "Hue Color Downlight 1 7" → "Office Back Left"
        - Learn: User prefers location-based names
        - Learn: "_1_7" pattern → "Back Left" position
        
        Storage: Simple dict structure, <1KB per pattern
        """
        try:
            # Pattern 1: Naming style (location-based, descriptive, etc.)
            style = self._detect_naming_style(user_customized_name, device)
            if style:
                await self._update_pattern(
                    "naming_style",
                    {"style": style, "area": device.area_name},
                    db_session
                )

            # Pattern 2: Position extraction from entity ID
            if entity and entity.entity_id:
                position = self._extract_position_mapping(original_name, user_customized_name, entity.entity_id)
                if position:
                    await self._update_pattern(
                        "position_mapping",
                        {"entity_pattern": position["pattern"], "position": position["position"]},
                        db_session
                    )

            # Pattern 3: Area-specific conventions
            if device.area_name:
                await self._update_pattern(
                    "area_convention",
                    {
                        "area": device.area_name,
                        "pattern": self._extract_area_pattern(user_customized_name)
                    },
                    db_session
                )

            # Pattern 4: Modifier preferences (Back, Front, Left, Right, etc.)
            modifiers = self._extract_modifiers(user_customized_name)
            if modifiers:
                await self._update_pattern(
                    "modifier_preference",
                    {"modifiers": modifiers},
                    db_session
                )

        except Exception as e:
            logger.warning(f"Failed to learn from customization: {e}")

    async def apply_preferences(
        self,
        device: Device,
        entity: DeviceEntity | None = None,
        db_session: AsyncSession | None = None
    ) -> NameSuggestion | None:
        """
        Apply learned preferences to generate suggestion.
        
        Performance: <5ms (in-memory lookup)
        """
        if not self._patterns_loaded and db_session:
            await self.load_patterns(db_session)

        # Try to apply naming style preference
        if "naming_style" in self.patterns:
            style_patterns = self.patterns["naming_style"]
            # Find best matching pattern
            for pattern in sorted(style_patterns, key=lambda p: p["confidence"], reverse=True):
                style = pattern["data"].get("style")
                area = pattern["data"].get("area")
                
                if area == device.area_name or not area:
                    # Apply this style
                    if style == "location_based" and device.area_name:
                        device_type = self._get_device_type(device, entity)
                        if device_type:
                            name = f"{device.area_name} {device_type}"
                            return NameSuggestion(
                                name=name,
                                confidence=pattern["confidence"],
                                source="preference",
                                reasoning=f"Applied learned {style} naming style"
                            )

        # Try to apply position mapping
        if entity and "position_mapping" in self.patterns:
            entity_id = entity.entity_id
            for pattern in self.patterns["position_mapping"]:
                pattern_data = pattern["data"]
                if pattern_data.get("entity_pattern") in entity_id:
                    position = pattern_data.get("position")
                    device_type = self._get_device_type(device, entity) or "Device"
                    if device.area_name:
                        name = f"{device.area_name} {position} {device_type}"
                    else:
                        name = f"{position} {device_type}"
                    return NameSuggestion(
                        name=name,
                        confidence=pattern["confidence"],
                        source="preference",
                        reasoning="Applied learned position mapping"
                    )

        return None

    def _detect_naming_style(self, name: str, device: Device) -> str | None:
        """Detect naming style from user customization"""
        # Check if location-based
        if device.area_name and device.area_name.lower() in name.lower():
            return "location_based"
        
        # Check if descriptive (no location, just description)
        if not any(word.lower() in name.lower() for word in ["room", "office", "kitchen", "bedroom"]):
            return "descriptive"
        
        return None

    def _extract_position_mapping(
        self,
        original_name: str,
        customized_name: str,
        entity_id: str
    ) -> dict[str, str] | None:
        """Extract position mapping from entity ID pattern"""
        # Look for position words in customized name
        position_words = ["back", "front", "left", "right", "center", "main", "secondary"]
        found_position = None
        for word in position_words:
            if word.lower() in customized_name.lower():
                found_position = word.title()
                break
        
        if not found_position:
            return None

        # Extract pattern from entity ID (e.g., "_1_7" from "hue_color_downlight_1_7")
        match = re.search(r"_(\d+)(?:_(\d+))?$", entity_id)
        if match:
            pattern = match.group(0)
            return {
                "pattern": pattern,
                "position": found_position
            }
        
        return None

    def _extract_area_pattern(self, name: str) -> str:
        """Extract naming pattern for area"""
        # Simple pattern: location + device type
        # Could be enhanced to detect more patterns
        return "location_device_type"

    def _extract_modifiers(self, name: str) -> list[str]:
        """Extract modifier words (Back, Front, Left, Right, etc.)"""
        modifiers = []
        modifier_words = ["back", "front", "left", "right", "center", "main", "primary", "secondary"]
        
        words = name.lower().split()
        for word in words:
            if word in modifier_words:
                modifiers.append(word.title())
        
        return modifiers

    def _get_device_type(self, device: Device, entity: DeviceEntity | None = None) -> str | None:
        """Get device type string"""
        if entity:
            domain_map = {
                "light": "Light",
                "switch": "Switch",
                "sensor": "Sensor",
                "binary_sensor": "Sensor",
            }
            return domain_map.get(entity.domain)
        
        if device.device_class:
            return device.device_class.replace("_", " ").title()
        
        return None

    async def _update_pattern(
        self,
        pattern_type: str,
        pattern_data: dict[str, Any],
        db_session: AsyncSession | None = None
    ):
        """Update or create a preference pattern"""
        if not db_session:
            # Just update in-memory
            if pattern_type not in self.patterns:
                self.patterns[pattern_type] = []
            self.patterns[pattern_type].append({
                "data": pattern_data,
                "confidence": 0.5,
                "count": 1
            })
            return

        try:
            # Check if pattern exists
            result = await db_session.execute(
                select(NamePreference).where(
                    NamePreference.pattern_type == pattern_type
                )
            )
            existing = result.scalars().all()

            # Find matching pattern
            matching = None
            for pref in existing:
                try:
                    existing_data = json.loads(pref.pattern_data) if isinstance(pref.pattern_data, str) else pref.pattern_data
                    if existing_data == pattern_data:
                        matching = pref
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

            if matching:
                # Update existing pattern
                matching.learned_from_count += 1
                matching.confidence = min(1.0, matching.confidence + 0.1)
                matching.last_updated = datetime.utcnow()
            else:
                # Create new pattern
                new_pattern = NamePreference(
                    pattern_type=pattern_type,
                    pattern_data=json.dumps(pattern_data),
                    confidence=0.5,
                    learned_from_count=1
                )
                db_session.add(new_pattern)

            await db_session.commit()

            # Update in-memory cache
            await self.load_patterns(db_session)

        except Exception as e:
            logger.warning(f"Failed to update pattern: {e}")
            if db_session:
                await db_session.rollback()

