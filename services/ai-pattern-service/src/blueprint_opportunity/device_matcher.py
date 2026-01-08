"""Device-to-blueprint matching algorithm."""

import logging
from typing import Any, Optional

from .schemas import DeviceSignature, BlueprintSummary

logger = logging.getLogger(__name__)


class DeviceMatcher:
    """
    Matches user devices to blueprint requirements.
    
    Scoring components:
    - Required domains coverage: 40%
    - Required device classes coverage: 30%
    - Same area bonus: 20%
    - Community rating bonus: 10%
    """
    
    # Scoring weights
    DOMAIN_WEIGHT = 0.40
    DEVICE_CLASS_WEIGHT = 0.30
    SAME_AREA_WEIGHT = 0.20
    COMMUNITY_RATING_WEIGHT = 0.10
    
    def __init__(self):
        """Initialize device matcher."""
        pass
    
    def calculate_fit_score(
        self,
        blueprint: BlueprintSummary,
        devices: list[DeviceSignature],
        same_area: bool = False,
    ) -> float:
        """
        Calculate how well user's devices match blueprint requirements.
        
        Args:
            blueprint: Blueprint to score
            devices: User's available devices
            same_area: Whether all matched devices are in the same area
            
        Returns:
            Fit score between 0.0 and 1.0
        """
        score = 0.0
        
        # Extract user's available domains and device classes
        user_domains = {d.domain for d in devices}
        user_device_classes = {d.device_class for d in devices if d.device_class}
        
        # Required domains coverage (40%)
        required_domains = set(blueprint.required_domains)
        if required_domains:
            matched_domains = required_domains & user_domains
            domain_coverage = len(matched_domains) / len(required_domains)
            score += domain_coverage * self.DOMAIN_WEIGHT
        else:
            score += self.DOMAIN_WEIGHT  # No requirements = full score
        
        # Required device classes coverage (30%)
        required_classes = set(blueprint.required_device_classes)
        if required_classes:
            matched_classes = required_classes & user_device_classes
            class_coverage = len(matched_classes) / len(required_classes)
            score += class_coverage * self.DEVICE_CLASS_WEIGHT
        else:
            score += self.DEVICE_CLASS_WEIGHT  # No requirements = full score
        
        # Same area bonus (20%)
        if same_area:
            score += self.SAME_AREA_WEIGHT
        else:
            score += self.SAME_AREA_WEIGHT * 0.5  # Partial score for different areas
        
        # Community rating bonus (10%)
        score += blueprint.community_rating * self.COMMUNITY_RATING_WEIGHT
        
        return min(1.0, score)
    
    def find_matching_devices(
        self,
        blueprint: BlueprintSummary,
        devices: list[DeviceSignature],
    ) -> list[DeviceSignature]:
        """
        Find devices that match blueprint requirements.
        
        Args:
            blueprint: Blueprint to match
            devices: User's available devices
            
        Returns:
            List of matching devices
        """
        matched = []
        
        required_domains = set(blueprint.required_domains)
        required_classes = set(blueprint.required_device_classes)
        
        for device in devices:
            # Check domain match
            if device.domain in required_domains:
                matched.append(device)
                continue
            
            # Check device class match
            if device.device_class and device.device_class in required_classes:
                matched.append(device)
        
        return matched
    
    def check_same_area(
        self,
        devices: list[DeviceSignature],
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if all devices are in the same area.
        
        Returns:
            Tuple of (same_area, area_id, area_name)
        """
        if not devices:
            return False, None, None
        
        areas = {d.area_id for d in devices if d.area_id}
        
        if len(areas) == 1:
            area_id = areas.pop()
            area_name = next(
                (d.area_name for d in devices if d.area_id == area_id and d.area_name),
                None
            )
            return True, area_id, area_name
        
        return False, None, None
    
    def rank_blueprints(
        self,
        blueprints: list[BlueprintSummary],
        devices: list[DeviceSignature],
        min_fit_score: float = 0.6,
    ) -> list[tuple[BlueprintSummary, float, list[DeviceSignature], bool]]:
        """
        Rank blueprints by fit score.
        
        Args:
            blueprints: List of blueprints to rank
            devices: User's available devices
            min_fit_score: Minimum fit score threshold
            
        Returns:
            List of (blueprint, fit_score, matched_devices, same_area) sorted by score
        """
        results = []
        
        for blueprint in blueprints:
            matched_devices = self.find_matching_devices(blueprint, devices)
            
            if not matched_devices:
                continue
            
            same_area, _, _ = self.check_same_area(matched_devices)
            fit_score = self.calculate_fit_score(blueprint, matched_devices, same_area)
            
            if fit_score >= min_fit_score:
                results.append((blueprint, fit_score, matched_devices, same_area))
        
        # Sort by fit score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def group_devices_by_area(
        self,
        devices: list[DeviceSignature],
    ) -> dict[Optional[str], list[DeviceSignature]]:
        """
        Group devices by area.
        
        Args:
            devices: List of devices
            
        Returns:
            Dictionary mapping area_id to list of devices
        """
        groups: dict[Optional[str], list[DeviceSignature]] = {}
        
        for device in devices:
            area_id = device.area_id
            if area_id not in groups:
                groups[area_id] = []
            groups[area_id].append(device)
        
        return groups
    
    def get_matching_domains(
        self,
        blueprint: BlueprintSummary,
        devices: list[DeviceSignature],
    ) -> list[str]:
        """Get list of domains that match blueprint requirements."""
        required_domains = set(blueprint.required_domains)
        user_domains = {d.domain for d in devices}
        return list(required_domains & user_domains)
    
    def get_matching_device_classes(
        self,
        blueprint: BlueprintSummary,
        devices: list[DeviceSignature],
    ) -> list[str]:
        """Get list of device classes that match blueprint requirements."""
        required_classes = set(blueprint.required_device_classes)
        user_classes = {d.device_class for d in devices if d.device_class}
        return list(required_classes & user_classes)
