"""
Scene Detection Module

Detects scene-based synergies where multiple devices could be controlled together.

Extracted from synergy_detector.py for better maintainability.
"""

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


# Configuration constants
MAX_SCENE_SYNERGIES = 50  # Maximum scene-based synergies to generate
MIN_DEVICES_FOR_AREA_SCENE = 3  # Minimum devices to suggest area-based scene
MIN_DEVICES_FOR_DOMAIN_SCENE = 5  # Minimum devices to suggest domain-based scene
MAX_DEVICES_PER_SCENE = 10  # Maximum devices to include in a scene suggestion


# Domains that can be controlled in scenes
ACTIONABLE_DOMAINS = {'light', 'switch', 'climate', 'media_player', 'cover', 'fan'}


class SceneDetector:
    """
    Detects scene-based synergies.
    
    Finds devices that could be grouped into scenes based on:
    1. Devices in the same area (suggest creating area scenes)
    2. Devices of the same domain (suggest creating domain scenes)
    
    Attributes:
        max_synergies: Maximum number of scene synergies to generate
    """
    
    def __init__(self, max_synergies: int = MAX_SCENE_SYNERGIES):
        """
        Initialize scene detector.
        
        Args:
            max_synergies: Maximum number of synergies to generate
        """
        self.max_synergies = max_synergies
    
    def _group_devices_by_area(
        self,
        entities: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        """
        Group actionable devices by area.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            Dictionary mapping area_id to list of entity_ids
        """
        area_devices: dict[str, list[str]] = {}
        
        for entity in entities:
            entity_id = entity.get('entity_id', '')
            domain = entity_id.split('.')[0] if '.' in entity_id else ''
            area_id = entity.get('area_id')
            
            if domain in ACTIONABLE_DOMAINS and area_id:
                if area_id not in area_devices:
                    area_devices[area_id] = []
                area_devices[area_id].append(entity_id)
        
        return area_devices
    
    def _group_devices_by_domain(
        self,
        entities: list[dict[str, Any]]
    ) -> dict[str, list[str]]:
        """
        Group actionable devices by domain.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            Dictionary mapping domain to list of entity_ids
        """
        domain_devices: dict[str, list[str]] = {}
        
        for entity in entities:
            entity_id = entity.get('entity_id', '')
            domain = entity_id.split('.')[0] if '.' in entity_id else ''
            
            if domain in ACTIONABLE_DOMAINS:
                if domain not in domain_devices:
                    domain_devices[domain] = []
                domain_devices[domain].append(entity_id)
        
        return domain_devices
    
    def _find_existing_scenes(
        self,
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Find existing scene entities.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of scene entity dictionaries
        """
        return [e for e in entities if e.get('entity_id', '').startswith('scene.')]
    
    def _has_existing_area_scene(
        self,
        area_id: str,
        scene_entities: list[dict[str, Any]]
    ) -> bool:
        """
        Check if area already has a scene.
        
        Args:
            area_id: Area identifier
            scene_entities: List of existing scene entities
            
        Returns:
            True if area has existing scene
        """
        area_lower = area_id.lower()
        return any(
            area_lower in s.get('entity_id', '').lower()
            for s in scene_entities
        )
    
    def _has_existing_domain_scene(
        self,
        domain: str,
        scene_entities: list[dict[str, Any]]
    ) -> bool:
        """
        Check if domain already has a global scene.
        
        Args:
            domain: Domain name (e.g., 'light')
            scene_entities: List of existing scene entities
            
        Returns:
            True if domain has existing global scene
        """
        return any(
            f"all_{domain}" in s.get('entity_id', '').lower() or
            f"{domain}_all" in s.get('entity_id', '').lower()
            for s in scene_entities
        )
    
    def _create_area_scene_synergy(
        self,
        area_id: str,
        devices: list[str]
    ) -> dict[str, Any]:
        """
        Create an area-based scene synergy.
        
        Args:
            area_id: Area identifier
            devices: List of device entity_ids in the area
            
        Returns:
            Scene-based synergy dictionary
        """
        if not devices:
            raise ValueError(f"Cannot create scene synergy for area {area_id}: devices list is empty")
        
        devices_to_include = devices[:MAX_DEVICES_PER_SCENE]
        
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'scene_based',
            'devices': devices_to_include,
            'trigger_entity': f"scene.{area_id}_all",
            'action_entity': devices[0],
            'area': area_id,
            'impact_score': min(0.9, 0.5 + len(devices) * 0.1),
            'confidence': 0.80,  # Higher confidence for area-based
            'complexity': 'low',
            'rationale': f"Scene opportunity: {len(devices)} devices in {area_id} could be controlled together",
            'synergy_depth': len(devices_to_include),
            'chain_devices': devices_to_include,
            'context_metadata': {
                'scene_type': 'area_based',
                'suggested_scene_name': f"{area_id.replace('_', ' ').title()} All",
                'device_count': len(devices),
                'device_domains': list(set(d.split('.')[0] for d in devices))
            }
        }
    
    def _create_domain_scene_synergy(
        self,
        domain: str,
        devices: list[str]
    ) -> dict[str, Any]:
        """
        Create a domain-based scene synergy.
        
        Args:
            domain: Domain name (e.g., 'light')
            devices: List of device entity_ids of this domain
            
        Returns:
            Scene-based synergy dictionary
        """
        if not devices:
            raise ValueError(f"Cannot create scene synergy for domain {domain}: devices list is empty")
        
        devices_to_include = devices[:MAX_DEVICES_PER_SCENE]
        
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'scene_based',
            'devices': devices_to_include,
            'trigger_entity': f"scene.all_{domain}s",
            'action_entity': devices[0],
            'area': None,
            'impact_score': min(0.85, 0.4 + len(devices) * 0.05),
            'confidence': 0.70,  # Lower confidence for domain-based
            'complexity': 'low',
            'rationale': f"Scene opportunity: {len(devices)} {domain} devices could be controlled together",
            'synergy_depth': len(devices_to_include),
            'chain_devices': devices_to_include,
            'context_metadata': {
                'scene_type': 'domain_based',
                'suggested_scene_name': f"All {domain.title()}s",
                'device_count': len(devices),
                'domain': domain
            }
        }
    
    async def detect_scene_based_synergies(
        self,
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Detect scene-based synergies.
        
        Finds devices that could be grouped into scenes based on:
        1. Devices in the same area (suggest creating area scenes)
        2. Devices of the same domain (suggest creating domain scenes)
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of scene-based synergy opportunities
        """
        logger.info("   → Detecting scene-based synergies...")
        synergies: list[dict[str, Any]] = []
        
        # Find existing scenes
        scene_entities = self._find_existing_scenes(entities)
        logger.info(f"      Found {len(scene_entities)} existing scenes")
        
        # Group devices
        area_devices = self._group_devices_by_area(entities)
        domain_devices = self._group_devices_by_domain(entities)
        
        # Strategy 1: Create area-based scene synergies
        for area_id, devices in area_devices.items():
            if len(synergies) >= self.max_synergies:
                break
            
            if len(devices) >= MIN_DEVICES_FOR_AREA_SCENE:
                if not self._has_existing_area_scene(area_id, scene_entities):
                    synergy = self._create_area_scene_synergy(area_id, devices)
                    synergies.append(synergy)
        
        # Strategy 2: Create domain-based scene synergies (if not enough area-based)
        if len(synergies) < self.max_synergies // 2:
            for domain, devices in domain_devices.items():
                if len(synergies) >= self.max_synergies:
                    break
                
                if len(devices) >= MIN_DEVICES_FOR_DOMAIN_SCENE:
                    if not self._has_existing_domain_scene(domain, scene_entities):
                        synergy = self._create_domain_scene_synergy(domain, devices)
                        synergies.append(synergy)
        
        logger.info(
            f"      ✅ Generated {len(synergies)} scene-based synergies "
            f"(area: {len(area_devices)}, domain: {len(domain_devices)})"
        )
        return synergies
