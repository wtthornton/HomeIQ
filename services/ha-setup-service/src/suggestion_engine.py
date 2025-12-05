"""
Suggestion Engine for Area Assignment

Generates intelligent suggestions for area assignments based on entity names.
Epic 32: Home Assistant Configuration Validation & Suggestions
"""
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


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
        self,
        entity_id: str,
        entity_name: str | None,
        areas: list[dict[str, Any]]
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
                entity_id_lower,
                entity_name_lower,
                entity_keywords,
                area_id,
                area_name_lower
            )
            
            if confidence > 0:
                suggestions.append({
                    "area_id": area_id,
                    "area_name": area_name,
                    "confidence": confidence,
                    "reasoning": reasoning
                })
        
        # Sort by confidence (highest first)
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Return top 3 suggestions
        return suggestions[:3]
    
    def _extract_keywords(
        self,
        entity_id: str,
        entity_name: str
    ) -> set[str]:
        """Extract location keywords from entity identifiers"""
        keywords = set()
        
        # Extract from entity_id (e.g., "light.hue_office_back_left" -> ["office"])
        # Split by common separators
        parts = re.split(r'[._-]', entity_id)
        for part in parts:
            part_clean = part.strip()
            if len(part_clean) > 2:  # Ignore short parts
                keywords.add(part_clean)
        
        # Extract from entity_name (e.g., "Office Back Left" -> ["office"])
        if entity_name:
            name_parts = re.split(r'[\s_-]+', entity_name)
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
        area_name: str
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
            confidence = 100.0
            reasoning_parts.append(f"Exact match: '{area_id}' found in entity_id")
            return confidence, "; ".join(reasoning_parts)
        
        # 2. Exact match in entity_name (95% confidence)
        if entity_name and (area_id_lower in entity_name.lower() or area_name_lower in entity_name.lower()):
            confidence = 95.0
            reasoning_parts.append(f"Exact match: '{area_name}' found in entity name")
            return confidence, "; ".join(reasoning_parts)
        
        # 3. Partial match in entity_id (80% confidence)
        area_words = re.split(r'[\s_-]+', area_name_lower)
        for word in area_words:
            if len(word) > 3 and word in entity_id:
                confidence = max(confidence, 80.0)
                reasoning_parts.append(f"Partial match: '{word}' found in entity_id")
        
        # 4. Keyword matching (60% confidence)
        for keyword in entity_keywords:
            # Check if keyword matches area name
            if keyword in area_name_lower or area_name_lower in keyword:
                confidence = max(confidence, 60.0)
                reasoning_parts.append(f"Keyword match: '{keyword}' matches area '{area_name}'")
            
            # Check location keyword mappings
            for area_key, keywords_list in self.LOCATION_KEYWORDS.items():
                if keyword in keywords_list and area_id_lower == area_key:
                    confidence = max(confidence, 60.0)
                    reasoning_parts.append(f"Location keyword match: '{keyword}' maps to '{area_name}'")
        
        # 5. Partial word match (40% confidence)
        for keyword in entity_keywords:
            if len(keyword) > 4:
                # Check if keyword is substring of area name or vice versa
                if keyword in area_name_lower or area_name_lower in keyword:
                    confidence = max(confidence, 40.0)
                    reasoning_parts.append(f"Partial word match: '{keyword}' similar to '{area_name}'")
        
        # If no matches found, return 0
        if confidence == 0:
            return 0.0, "No matches found"
        
        return confidence, "; ".join(reasoning_parts) if reasoning_parts else "Low confidence match"

