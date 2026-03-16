"""
Auto-Alias Generator (Epic 64, Story 64.2).

Pattern-based alias generation (no AI): singular/plural, area-less,
abbreviations, type shorthand, casual variants. 3-5 suggestions per entity.
Conflict detection prevents duplicate aliases across entities.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Common abbreviation mappings
_ABBREVIATIONS: dict[str, list[str]] = {
    "television": ["TV"],
    "air conditioner": ["AC"],
    "air conditioning": ["AC"],
    "refrigerator": ["fridge"],
    "thermostat": ["thermo"],
    "dehumidifier": ["dehumid"],
    "humidifier": ["humid"],
    "air purifier": ["purifier"],
    "media player": ["player", "media"],
    "binary sensor": ["sensor"],
    "motion sensor": ["motion"],
    "temperature sensor": ["temp sensor", "temp"],
    "humidity sensor": ["humidity"],
    "illuminance sensor": ["lux sensor"],
    "carbon monoxide": ["CO"],
    "carbon dioxide": ["CO2"],
}

# Singular/plural mappings
_PLURALS: dict[str, str] = {
    "light": "lights",
    "switch": "switches",
    "sensor": "sensors",
    "fan": "fans",
    "lock": "locks",
    "camera": "cameras",
    "cover": "covers",
    "blind": "blinds",
    "curtain": "curtains",
    "speaker": "speakers",
    "lamp": "lamps",
}

# Casual name variants
_CASUAL_VARIANTS: dict[str, list[str]] = {
    "light": ["lamp", "bulb"],
    "cover": ["blind", "shade", "curtain"],
    "climate": ["thermostat", "heating", "cooling"],
    "media_player": ["speaker", "TV", "player"],
    "vacuum": ["robot", "roomba"],
    "fan": ["ventilator"],
    "lock": ["deadbolt"],
}


@dataclass
class AliasSuggestion:
    """A suggested alias for an entity."""

    alias: str
    source: str  # "abbreviation", "area_less", "casual", "plural", "shorthand"
    confidence: float  # 0.0-1.0


@dataclass
class AliasResult:
    """Result of alias generation for an entity."""

    entity_id: str
    current_aliases: list[str]
    suggestions: list[AliasSuggestion] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "current_aliases": self.current_aliases,
            "suggestions": [
                {"alias": s.alias, "source": s.source, "confidence": s.confidence}
                for s in self.suggestions
            ],
            "conflicts": self.conflicts,
        }


class AliasGenerator:
    """Generate alias suggestions for entities based on patterns."""

    def suggest_aliases(
        self,
        entity: dict[str, Any],
        existing_aliases_map: dict[str, set[str]] | None = None,
        max_suggestions: int = 5,
    ) -> AliasResult:
        """Generate alias suggestions for a single entity.

        Args:
            entity: Entity dict with entity_id, friendly_name, domain, area_id, aliases.
            existing_aliases_map: Map of alias (lowered) → set of entity_ids that use it.
            max_suggestions: Maximum suggestions to return.

        Returns:
            AliasResult with suggested aliases and any conflicts.
        """
        entity_id = entity.get("entity_id", "unknown")
        friendly_name = entity.get("friendly_name") or ""
        domain = entity.get("domain") or ""
        area_id = entity.get("area_id") or ""
        current_aliases = entity.get("aliases") or []
        if not isinstance(current_aliases, list):
            current_aliases = []

        existing_map = existing_aliases_map or {}
        current_set = {a.lower() for a in current_aliases}

        candidates: list[AliasSuggestion] = []

        # Strategy 1: Area-less variant (remove area prefix from name)
        if area_id and friendly_name:
            area_name = area_id.replace("_", " ")
            name_lower = friendly_name.lower()
            if name_lower.startswith(area_name.lower()):
                short = friendly_name[len(area_name):].strip()
                if short and len(short) > 2:
                    candidates.append(AliasSuggestion(
                        alias=short, source="area_less", confidence=0.85,
                    ))

        # Strategy 2: Abbreviations
        if friendly_name:
            name_lower = friendly_name.lower()
            for long_form, short_forms in _ABBREVIATIONS.items():
                if long_form in name_lower:
                    for short in short_forms:
                        abbrev_name = name_lower.replace(long_form, short)
                        candidates.append(AliasSuggestion(
                            alias=abbrev_name.strip().title(),
                            source="abbreviation",
                            confidence=0.8,
                        ))

        # Strategy 3: Type shorthand (domain-based casual name)
        if domain in _CASUAL_VARIANTS and friendly_name:
            for variant in _CASUAL_VARIANTS[domain][:2]:
                # Replace domain word in name with casual variant
                domain_word = domain.replace("_", " ")
                if domain_word in friendly_name.lower():
                    casual = re.sub(
                        re.escape(domain_word), variant,
                        friendly_name, count=1, flags=re.IGNORECASE,
                    )
                    candidates.append(AliasSuggestion(
                        alias=casual.strip(), source="casual", confidence=0.7,
                    ))
                elif area_id:
                    # Build "Area Variant" alias
                    area_name = area_id.replace("_", " ").title()
                    candidates.append(AliasSuggestion(
                        alias=f"{area_name} {variant.title()}",
                        source="casual",
                        confidence=0.65,
                    ))

        # Strategy 4: Singular/plural variant
        if friendly_name:
            name_lower = friendly_name.lower()
            for singular, plural in _PLURALS.items():
                if name_lower.endswith(f" {singular}"):
                    candidates.append(AliasSuggestion(
                        alias=friendly_name[: -len(singular)] + plural,
                        source="plural",
                        confidence=0.6,
                    ))
                    break
                elif name_lower.endswith(f" {plural}"):
                    candidates.append(AliasSuggestion(
                        alias=friendly_name[: -len(plural)] + singular,
                        source="plural",
                        confidence=0.6,
                    ))
                    break

        # Strategy 5: Just the friendly name as-is (if no aliases at all)
        if not current_aliases and friendly_name:
            candidates.append(AliasSuggestion(
                alias=friendly_name, source="shorthand", confidence=0.5,
            ))

        # Deduplicate and filter
        seen: set[str] = set()
        filtered: list[AliasSuggestion] = []
        conflicts: list[str] = []

        for candidate in candidates:
            alias_lower = candidate.alias.lower().strip()
            if not alias_lower or len(alias_lower) < 2:
                continue
            if alias_lower in seen or alias_lower in current_set:
                continue

            # Check for conflicts
            if alias_lower in existing_map:
                owners = existing_map[alias_lower]
                if entity_id not in owners:
                    conflicts.append(
                        f"'{candidate.alias}' conflicts with {', '.join(owners)}"
                    )
                    continue

            seen.add(alias_lower)
            filtered.append(candidate)

        # Sort by confidence and limit
        filtered.sort(key=lambda s: s.confidence, reverse=True)
        filtered = filtered[:max_suggestions]

        return AliasResult(
            entity_id=entity_id,
            current_aliases=current_aliases,
            suggestions=filtered,
            conflicts=conflicts,
        )

    def build_alias_map(self, entities: list[dict[str, Any]]) -> dict[str, set[str]]:
        """Build a map of existing alias → entity_ids for conflict detection."""
        alias_map: dict[str, set[str]] = {}
        for entity in entities:
            entity_id = entity.get("entity_id", "")
            aliases = entity.get("aliases") or []
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str):
                        key = alias.lower().strip()
                        if key not in alias_map:
                            alias_map[key] = set()
                        alias_map[key].add(entity_id)
        return alias_map
