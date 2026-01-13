"""
Spatial Intelligence Module

Phase 2.2: Spatial intelligence for cross-area and proximity-based synergies.

Enables cross-area synergies by validating spatial relationships between areas
and detecting proximity-based patterns.
"""

import logging
from collections import defaultdict
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SpatialIntelligenceService:
    """
    Provides spatial intelligence for cross-area synergy detection.
    
    Builds spatial relationship graph from area data and validates
    cross-area synergies based on adjacency and proximity.
    
    Attributes:
        area_lookup: Dictionary mapping area_id to area metadata
        adjacency_graph: Graph structure for area adjacencies
    """
    
    def __init__(self):
        """Initialize spatial intelligence service."""
        self.area_lookup: dict[str, dict[str, Any]] = {}
        self.adjacency_graph: dict[str, set[str]] = defaultdict(set)
    
    def build_spatial_graph(
        self,
        entities: list[dict[str, Any]]
    ) -> dict[str, set[str]]:
        """
        Build spatial relationship graph from entity data.
        
        Currently uses heuristics based on area IDs and entity patterns.
        Can be enhanced with explicit adjacency data from data-api.
        
        Args:
            entities: List of entity dictionaries with area_id
            
        Returns:
            Dictionary mapping area_id -> set of adjacent area_ids
        """
        # Group entities by area
        area_entities: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entity in entities:
            area_id = entity.get('area_id')
            if area_id:
                area_entities[area_id].append(entity)
                self.area_lookup[area_id] = {
                    'area_id': area_id,
                    'entity_count': len(area_entities[area_id])
                }
        
        # Build adjacency graph (basic heuristic: areas with common patterns are adjacent)
        # This is a simplified implementation - can be enhanced with explicit adjacency data
        area_ids = list(area_entities.keys())
        for i, area1 in enumerate(area_ids):
            for area2 in area_ids[i+1:]:
                # Simple heuristic: areas are considered adjacent if they have similar naming patterns
                # (e.g., "bedroom" and "bedroom_hallway", "kitchen" and "kitchen_dining")
                # This is a placeholder - should be replaced with actual adjacency data
                if self._heuristic_adjacent(area1, area2):
                    self.adjacency_graph[area1].add(area2)
                    self.adjacency_graph[area2].add(area1)
        
        logger.debug(f"Built spatial graph with {len(self.adjacency_graph)} areas")
        return dict(self.adjacency_graph)
    
    def _heuristic_adjacent(
        self,
        area1: str,
        area2: str
    ) -> bool:
        """
        Heuristic to determine if two areas are adjacent.
        
        This is a placeholder implementation. In production, this should
        use explicit adjacency data from Home Assistant or data-api.
        
        Args:
            area1: First area ID
            area2: Second area ID
            
        Returns:
            True if areas are heuristically adjacent
        """
        area1_lower = area1.lower()
        area2_lower = area2.lower()
        
        # Check for common prefixes (e.g., "bedroom" and "bedroom_hallway")
        if area1_lower in area2_lower or area2_lower in area1_lower:
            return True
        
        # Check for common patterns (e.g., "kitchen" and "dining" -> "kitchen_dining")
        common_words = ['bedroom', 'kitchen', 'bathroom', 'living', 'dining', 'hallway', 'office']
        for word in common_words:
            if word in area1_lower and word in area2_lower:
                return True
        
        return False
    
    def are_adjacent(
        self,
        area1: str,
        area2: str
    ) -> bool:
        """
        Check if two areas are adjacent.
        
        Args:
            area1: First area ID
            area2: Second area ID
            
        Returns:
            True if areas are adjacent (directly connected)
        """
        if area1 == area2:
            return False
        
        return area2 in self.adjacency_graph.get(area1, set())
    
    def validate_cross_area_synergy(
        self,
        synergy: dict[str, Any],
        entities: list[dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if a cross-area synergy makes spatial sense.
        
        Args:
            synergy: Synergy dictionary with devices and area
            entities: List of entity dictionaries
            
        Returns:
            Tuple of (is_valid: bool, reason: Optional[str])
        """
        devices = synergy.get('devices', synergy.get('device_ids', []))
        if not devices or len(devices) < 2:
            return True, None  # Single device or no devices - skip validation
        
        # Get areas for devices
        device_areas: list[Optional[str]] = []
        for device in devices:
            # Find entity for device
            entity_id = device if isinstance(device, str) else device.get('entity_id', '')
            area = next((e.get('area_id') for e in entities if e.get('entity_id') == entity_id), None)
            device_areas.append(area)
        
        # Filter out None values
        areas = [a for a in device_areas if a]
        
        if len(areas) < 2:
            return True, None  # Not enough areas to validate
        
        unique_areas = set(areas)
        
        # Same area - always valid
        if len(unique_areas) == 1:
            return True, None
        
        # Cross-area: validate adjacency
        if len(unique_areas) == 2:
            area1, area2 = list(unique_areas)
            if self.are_adjacent(area1, area2):
                return True, None
            else:
                # Allow cross-area even if not explicitly adjacent (users may have different layouts)
                # But log a warning
                logger.debug(f"Cross-area synergy between non-adjacent areas: {area1} <-> {area2}")
                return True, f"Cross-area synergy (not explicitly adjacent: {area1} <-> {area2})"
        
        # Multiple areas: check if all are adjacent or at least connected
        # For now, allow multi-area synergies
        return True, "Multi-area synergy"
    
    def suggest_cross_area_patterns(
        self,
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Suggest cross-area patterns based on spatial relationships.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of suggested cross-area pattern dictionaries
        """
        # Build spatial graph
        self.build_spatial_graph(entities)
        
        suggestions: list[dict[str, Any]] = []
        
        # Find adjacent area pairs with compatible devices
        for area1, adjacent_areas in self.adjacency_graph.items():
            for area2 in adjacent_areas:
                # Find devices in each area
                area1_entities = [e for e in entities if e.get('area_id') == area1]
                area2_entities = [e for e in entities if e.get('area_id') == area2]
                
                # Suggest common patterns (lights, switches, etc.)
                area1_lights = [e for e in area1_entities if e.get('entity_id', '').startswith('light.')]
                area2_lights = [e for e in area2_entities if e.get('entity_id', '').startswith('light.')]
                
                if area1_lights and area2_lights:
                    suggestions.append({
                        'pattern_type': 'cross_area_lighting',
                        'area1': area1,
                        'area2': area2,
                        'description': f'Cross-area lighting between {area1} and {area2}',
                        'suggested_synergy': {
                            'devices': [area1_lights[0].get('entity_id'), area2_lights[0].get('entity_id')],
                            'area': None,  # Cross-area
                            'complexity': 'medium',
                            'rationale': f'Adjacent areas {area1} and {area2} could coordinate lighting'
                        }
                    })
        
        logger.debug(f"Suggested {len(suggestions)} cross-area patterns")
        return suggestions
