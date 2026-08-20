"""
Suggestion Engine for Area Assignment

Proposes area assignments to a HUMAN by reading entity names. Every signal it
has is a name — the entity_id string and the friendly name — so nothing it
produces may drive a decision the system makes on its own. See
`.claude/rules/friendly-names.md`.

That is not a theoretical concern here. Two identically-modelled dimmers on this
instance carried SWAPPED friendly names, so a name-derived area for either one
named the wrong room. This engine used to answer 100% confidence when the area
name appeared in the entity_id and 95% when it appeared in the friendly name;
`validation_service` then flagged the entity's real area as
`incorrect_area_assignment` at >= 80, and that flows to a path that writes an
area to HA. A renamed device could therefore relocate itself.

Confidence is now capped below that threshold by construction
(`NAME_DERIVED_CONFIDENCE_CAP`), and every suggestion carries `basis:
"name_only"` so a consumer cannot mistake it for evidence. The relative ordering
is preserved, because ranking candidates for a person to choose between is
exactly what this engine is for.

Epic 32: Home Assistant Configuration Validation & Suggestions
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Everything this engine knows comes from a name, and a name is a presentation
# artifact — it may rank options for a person, never clear a system threshold.
# `validation_service` acts at >= 80; this cap sits below it so no name match can
# reach it however exact the string is. Raising this constant re-opens the
# rename-relocates-the-device defect.
NAME_DERIVED_CONFIDENCE_CAP = 49.0

# What each match is worth, all under the cap. The ORDER is the useful part: a
# person choosing between three candidates wants the best guess first.
CONFIDENCE_EXACT_IN_ENTITY_ID = 49.0
CONFIDENCE_EXACT_IN_ENTITY_NAME = 45.0
CONFIDENCE_PARTIAL_IN_ENTITY_ID = 35.0
CONFIDENCE_KEYWORD = 25.0


class SuggestionEngine:
    """
    Engine for generating area assignment suggestions

    Analyzes entity names and matches them to areas using:
    - Exact name matching
    - Partial name matching
    - Keyword extraction
    - Pattern recognition
    """

    # Common location keywords and their area name mappings
    LOCATION_KEYWORDS = {
        "office": ["office", "workspace", "study", "desk"],
        "living_room": ["living", "livingroom", "lr", "family"],
        "bedroom": ["bedroom", "bed", "master", "guest"],
        "kitchen": ["kitchen", "cook"],
        "bathroom": ["bathroom", "bath", "toilet", "restroom"],
        "garage": ["garage"],
        "hallway": ["hallway", "hall", "corridor"],
        "dining_room": ["dining", "diningroom", "dinner"],
        "basement": ["basement"],
        "attic": ["attic"],
    }

    def __init__(self):
        self.logger = logger

    async def suggest_area(
        self, entity_id: str, entity_name: str | None, areas: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Suggest area assignments for an entity

        Args:
            entity_id: Entity ID (e.g., "light.hue_office_back_left")
            entity_name: Friendly name (e.g., "Office Back Left")
            areas: List of area dictionaries with area_id and name

        Returns:
            List of suggestions with confidence scores, sorted by confidence
        """
        suggestions = []

        # Normalize entity identifiers
        entity_id_lower = entity_id.lower()
        entity_name_lower = (entity_name or "").lower()

        # Extract location keywords from entity
        entity_keywords = self._extract_keywords(entity_id_lower, entity_name_lower)

        # Match against areas
        for area in areas:
            area_id = area.get("area_id")
            area_name = area.get("name", "")
            area_name_lower = area_name.lower()

            # Calculate confidence score
            confidence, reasoning = self._calculate_confidence(
                entity_id_lower, entity_name_lower, entity_keywords, area_id, area_name_lower
            )

            if confidence > 0:
                suggestions.append(
                    {
                        "area_id": area_id,
                        "area_name": area_name,
                        "confidence": confidence,
                        "reasoning": reasoning,
                        # Declared so no consumer can mistake this for evidence.
                        # A name match is what a person should look at, never
                        # what the system should act on.
                        "basis": "name_only",
                        "actionable": False,
                    }
                )

        # Sort by confidence (highest first)
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)

        # Return top 3 suggestions
        return suggestions[:3]

    def _extract_keywords(self, entity_id: str, entity_name: str) -> set[str]:
        """Extract location keywords from entity identifiers"""
        keywords = set()

        # Extract from entity_id (e.g., "light.hue_office_back_left" -> ["office"])
        # Split by common separators
        parts = re.split(r"[._-]", entity_id)
        for part in parts:
            part_clean = part.strip()
            if len(part_clean) > 2:  # Ignore short parts
                keywords.add(part_clean)

        # Extract from entity_name (e.g., "Office Back Left" -> ["office"])
        if entity_name:
            name_parts = re.split(r"[\s_-]+", entity_name)
            for part in name_parts:
                part_clean = part.strip().lower()
                if len(part_clean) > 2:
                    keywords.add(part_clean)

        return keywords

    def _calculate_confidence(
        self,
        entity_id: str,
        entity_name: str,
        entity_keywords: set[str],
        area_id: str,
        area_name: str,
    ) -> tuple[float, str]:
        """
        Calculate confidence score for area assignment

        Returns:
            Tuple of (confidence_score, reasoning)
        """
        confidence = 0.0
        reasoning_parts = []

        # Normalize area name
        area_name_lower = area_name.lower()
        area_id_lower = area_id.lower()

        # 1. Exact match in entity_id (100% confidence)
        if area_id_lower in entity_id or area_name_lower in entity_id:
            confidence = CONFIDENCE_EXACT_IN_ENTITY_ID
            reasoning_parts.append(
                f"name only: '{area_id}' appears in the entity_id — a naming "
                "convention, not evidence of where the device is"
            )
            return confidence, "; ".join(reasoning_parts)

        # 2. Exact match in entity_name (95% confidence)
        if entity_name and (
            area_id_lower in entity_name.lower() or area_name_lower in entity_name.lower()
        ):
            confidence = CONFIDENCE_EXACT_IN_ENTITY_NAME
            reasoning_parts.append(
                f"name only: '{area_name}' appears in the friendly name — the field "
                "that was swapped on two dimmers here"
            )
            return confidence, "; ".join(reasoning_parts)

        # 3. Partial match in entity_id (80% confidence)
        area_words = re.split(r"[\s_-]+", area_name_lower)
        for word in area_words:
            if len(word) > 3 and word in entity_id:
                confidence = max(confidence, CONFIDENCE_PARTIAL_IN_ENTITY_ID)
                reasoning_parts.append(f"name only: partial match '{word}' in the entity_id")

        # 4. Keyword matching (60% confidence)
        for keyword in entity_keywords:
            # Check if keyword matches area name
            if keyword in area_name_lower or area_name_lower in keyword:
                confidence = max(confidence, CONFIDENCE_KEYWORD)
                reasoning_parts.append(f"Keyword match: '{keyword}' matches area '{area_name}'")

            # Check location keyword mappings
            for area_key, keywords_list in self.LOCATION_KEYWORDS.items():
                if keyword in keywords_list and area_id_lower == area_key:
                    confidence = max(confidence, CONFIDENCE_KEYWORD)
                    reasoning_parts.append(
                        f"Location keyword match: '{keyword}' maps to '{area_name}'"
                    )

        # 5. Partial word match (40% confidence)
        for keyword in entity_keywords:
            if len(keyword) > 4 and (keyword in area_name_lower or area_name_lower in keyword):
                confidence = max(confidence, 40.0)
                reasoning_parts.append(f"Partial word match: '{keyword}' similar to '{area_name}'")

        # If no matches found, return 0
        if confidence == 0:
            return 0.0, "No matches found"

        return confidence, "; ".join(reasoning_parts) if reasoning_parts else "Low confidence match"
