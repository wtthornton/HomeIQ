"""
Spatial Proximity Validator

Validates device pairs based on semantic proximity to prevent false relationships
like "front door lock + backyard light".

Phase 1: Semantic Proximity Validation
Phase 2: Real-World Rules Integration
"""

import logging
import re
from typing import Optional, Tuple

from .real_world_rules import RealWorldRulesValidator

logger = logging.getLogger(__name__)


class SpatialProximityValidator:
    """
    Validates device pairs based on semantic proximity.
    
    Prevents false relationships like:
    - front_door_lock + backyard_light (different semantic locations)
    - front_door_lock + front_door_light (same semantic location - GOOD)
    """
    
    # Location qualifiers that indicate semantic proximity
    LOCATION_QUALIFIERS = {
        'front': ['front', 'entrance', 'entry', 'main'],
        'back': ['back', 'rear', 'backyard', 'back yard', 'backyard'],
        'side': ['side', 'lateral'],
        'left': ['left'],
        'right': ['right'],
        'indoor': ['indoor', 'inside', 'interior'],
        'outdoor': ['outdoor', 'outside', 'exterior', 'yard', 'garden', 'patio', 'deck', 'porch']
    }
    
    # Incompatible location pairs
    INCOMPATIBLE_PAIRS = [
        ('front', 'back'),
        ('front', 'backyard'),
        ('back', 'front'),
        ('indoor', 'outdoor'),  # Unless explicitly allowed
        ('outdoor', 'indoor'),
    ]
    
    def __init__(self, db_session=None, home_id: str = 'default', home_type: str | None = None):
        """
        Initialize spatial proximity validator.
        
        Args:
            db_session: Optional database session for loading home-specific rules (Phase 2)
            home_id: Home ID for loading home-specific rules (default: 'default')
            home_type: Optional home type classification for spatial tolerance adjustment
        """
        self.db_session = db_session
        self.home_id = home_id
        self.home_type = home_type
        self._home_rules_cache = None
        self._spatial_tolerance = self._get_spatial_tolerance()
        
        # Initialize real-world rules validator (Phase 2)
        self.real_world_validator = RealWorldRulesValidator()
    
    def _get_spatial_tolerance(self) -> float:
        """
        Get spatial tolerance based on home type.
        
        Returns:
            Tolerance multiplier (0.8 = stricter, 1.2 = more lenient)
        """
        if not self.home_type:
            return 1.0
        
        tolerances = {
            'apartment': 0.8,  # Stricter (smaller spaces)
            'multi-story': 1.2,  # More lenient (cross-floor OK)
            'standard_home': 1.0,  # Default
            'security_focused': 0.9,  # Slightly stricter
            'studio': 0.75,  # Very strict (minimal space)
        }
        return tolerances.get(self.home_type, 1.0)
    
    def extract_location_qualifiers(self, device_name: str, entity_id: str) -> set[str]:
        """
        Extract location qualifiers from device name or entity ID.
        
        Args:
            device_name: Friendly name of the device
            entity_id: Entity ID of the device
            
        Returns:
            Set of location qualifier types found (e.g., {'front', 'outdoor'})
        """
        # Combine device name and entity ID for analysis
        text = f"{device_name} {entity_id}".lower()
        qualifiers = set()
        
        # Check each qualifier type and its keywords
        for qualifier_type, keywords in self.LOCATION_QUALIFIERS.items():
            for keyword in keywords:
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, text):
                    qualifiers.add(qualifier_type)
        
        return qualifiers
    
    async def _load_home_rules(self) -> list:
        """
        Load home-specific rules from database.
        
        Returns:
            List of home layout rules
        """
        if self._home_rules_cache is not None:
            return self._home_rules_cache
        
        if not self.db_session:
            self._home_rules_cache = []
            return []
        
        try:
            from ..database.models import HomeLayoutRule
            from sqlalchemy import select
            
            # Load rules for this home (or default)
            query = select(HomeLayoutRule).where(
                (HomeLayoutRule.home_id == self.home_id) | 
                (HomeLayoutRule.home_id == 'default')
            )
            
            result = await self.db_session.execute(query)
            rules = result.scalars().all()
            
            self._home_rules_cache = list(rules)
            logger.debug(f"Loaded {len(self._home_rules_cache)} home layout rules")
            
            return self._home_rules_cache
        except Exception as e:
            logger.warning(f"Failed to load home rules: {e}")
            self._home_rules_cache = []
            return []
    
    def _is_cross_floor(self, device1: dict, device2: dict) -> bool:
        """
        Check if devices are on different floors (for multi-story homes).
        
        Args:
            device1: First device dict
            device2: Second device dict
        
        Returns:
            True if devices appear to be on different floors
        """
        # Extract floor indicators from names/entity IDs
        name1 = device1.get('friendly_name', device1.get('entity_id', '')).lower()
        name2 = device2.get('friendly_name', device2.get('entity_id', '')).lower()
        
        floor_indicators = {
            'upstairs': ['upstairs', 'upper', 'second', '2nd', 'third', '3rd'],
            'downstairs': ['downstairs', 'lower', 'first', '1st', 'ground', 'basement']
        }
        
        floor1 = None
        floor2 = None
        
        for floor_type, keywords in floor_indicators.items():
            if any(keyword in name1 for keyword in keywords):
                floor1 = floor_type
            if any(keyword in name2 for keyword in keywords):
                floor2 = floor_type
        
        # If both have floor indicators and they're different, it's cross-floor
        if floor1 and floor2 and floor1 != floor2:
            return True
        
        return False
    
    def _check_home_layout_rules(
        self,
        device1: dict,
        device2: dict,
        home_rules: list
    ) -> Tuple[Optional[bool], Optional[str]]:
        """
        Check device pair against home layout rules.
        
        Args:
            device1: First device dict
            device2: Second device dict
            home_rules: List of HomeLayoutRule objects
            
        Returns:
            Tuple of (is_valid, reason) or (None, None) if no rule matched
        """
        name1 = device1.get('friendly_name', device1.get('entity_id', ''))
        name2 = device2.get('friendly_name', device2.get('entity_id', ''))
        entity_id1 = device1.get('entity_id', '')
        entity_id2 = device2.get('entity_id', '')
        
        text1 = f"{name1} {entity_id1}".lower()
        text2 = f"{name2} {entity_id2}".lower()
        
        for rule in home_rules:
            # Check if device1 matches pattern1
            pattern1 = rule.device1_pattern.lower()
            pattern2 = rule.device2_pattern.lower()
            
            # Simple pattern matching (can be enhanced with regex)
            matches1 = pattern1 in text1 or pattern1.replace('*', '') in text1
            matches2 = pattern2 in text2 or pattern2.replace('*', '') in text2
            
            if matches1 and matches2:
                if rule.relationship == 'incompatible':
                    return (False, f"home_rule_incompatible_{rule.id}")
                elif rule.relationship == 'compatible':
                    return (True, f"home_rule_compatible_{rule.id}")
        
        return (None, None)
    
    async def are_semantically_proximate(
        self, 
        device1: dict, 
        device2: dict
    ) -> Tuple[bool, str]:
        """
        Check if two devices are semantically proximate.
        
        Priority order:
        1. Home-specific rules (highest priority)
        2. Real-world rules (medium priority)
        3. Semantic qualifiers (fallback)
        
        Args:
            device1: First device dict with 'friendly_name' and 'entity_id'
            device2: Second device dict with 'friendly_name' and 'entity_id'
        
        Returns:
            Tuple of (is_valid, reason) where:
            - is_valid: True if devices are semantically compatible
            - reason: Explanation of the validation result
        """
        # Priority 1: Check home-specific rules
        if self.db_session:
            home_rules = await self._load_home_rules()
            if home_rules:
                is_valid, reason = self._check_home_layout_rules(device1, device2, home_rules)
                if is_valid is not None:
                    return (is_valid, reason)
        
        # Priority 2: Check real-world rules
        is_valid, reason = self.real_world_validator.validate_device_pair(device1, device2)
        if reason is not None:  # Rule matched
            return (is_valid, reason)
        
        # Priority 3: Check semantic qualifiers (fallback)
        name1 = device1.get('friendly_name', device1.get('entity_id', ''))
        name2 = device2.get('friendly_name', device2.get('entity_id', ''))
        entity_id1 = device1.get('entity_id', '')
        entity_id2 = device2.get('entity_id', '')
        
        # Extract location qualifiers
        qualifiers1 = self.extract_location_qualifiers(name1, entity_id1)
        qualifiers2 = self.extract_location_qualifiers(name2, entity_id2)
        
        # Apply home type tolerance to cross-floor relationships
        if self.home_type == 'multi-story':
            # Allow cross-floor relationships for multi-story homes
            if self._is_cross_floor(device1, device2):
                return (True, "cross_floor_allowed_multi_story")
        
        # If no qualifiers, assume compatible (can't determine)
        if not qualifiers1 and not qualifiers2:
            return (True, "no_location_qualifiers")
        
        # If one has qualifiers and other doesn't, check if they're compatible
        if qualifiers1 and not qualifiers2:
            # Device 2 might be generic (e.g., "light" without location)
            # Allow if device 1 is indoor and device 2 is in same area
            if 'outdoor' in qualifiers1:
                return (False, "outdoor_device_without_location")
            return (True, "one_device_generic")
        
        if qualifiers2 and not qualifiers1:
            if 'outdoor' in qualifiers2:
                return (False, "outdoor_device_without_location")
            return (True, "one_device_generic")
        
        # Both have qualifiers - check compatibility
        # Check for incompatible pairs
        for qual1 in qualifiers1:
            for qual2 in qualifiers2:
                if (qual1, qual2) in self.INCOMPATIBLE_PAIRS:
                    return (False, f"incompatible_locations_{qual1}_{qual2}")
        
        # Check for matching qualifiers (strong match)
        if qualifiers1 & qualifiers2:  # Intersection
            return (True, "matching_location_qualifiers")
        
        # Apply spatial tolerance for home type
        # For apartments/studios, be stricter about location matching
        if self._spatial_tolerance < 1.0:
            # Stricter matching required
            if not (qualifiers1 & qualifiers2):
                return (False, f"strict_spatial_tolerance_{self.home_type}")
        
        # If both have qualifiers but don't match, check if they're in same area
        # (e.g., "front door" and "front porch" - different qualifiers but same area)
        area1 = device1.get('area_id', '')
        area2 = device2.get('area_id', '')
        if area1 and area2 and area1 == area2:
            # Same area but different qualifiers - might be valid (e.g., "front door" + "front porch light")
            # Check if qualifiers are related (e.g., both front-related)
            front_related = {'front', 'entrance', 'entry', 'main'}
            back_related = {'back', 'rear', 'backyard'}
            
            has_front1 = bool(qualifiers1 & front_related)
            has_front2 = bool(qualifiers2 & front_related)
            has_back1 = bool(qualifiers1 & back_related)
            has_back2 = bool(qualifiers2 & back_related)
            
            # If both are front-related or both are back-related, allow
            if (has_front1 and has_front2) or (has_back1 and has_back2):
                return (True, "same_area_related_qualifiers")
            
            # Same area but unrelated qualifiers - might still be valid (conservative approach)
            return (True, "same_area_different_qualifiers")
        
        # Different qualifiers and different areas - likely incompatible
        return (False, "different_location_qualifiers_and_areas")

