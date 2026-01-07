"""Ranking algorithms for Blueprint Index Service."""

import logging
from typing import Any, Optional

from ..models import IndexedBlueprint

logger = logging.getLogger(__name__)


class BlueprintRanker:
    """
    Ranking algorithms for blueprint search results.
    
    Provides methods to rank blueprints by:
    - Pattern match quality
    - Device compatibility
    - Community metrics
    - Overall relevance
    """
    
    # Scoring weights
    PATTERN_MATCH_WEIGHT = 0.4
    QUALITY_WEIGHT = 0.3
    COMMUNITY_WEIGHT = 0.2
    RECENCY_WEIGHT = 0.1
    
    def rank_for_pattern(
        self,
        blueprints: list[IndexedBlueprint],
        trigger_domain: str,
        action_domain: str,
        trigger_device_class: Optional[str] = None,
        action_device_class: Optional[str] = None,
    ) -> list[IndexedBlueprint]:
        """
        Rank blueprints for a trigger-action pattern match.
        
        Args:
            blueprints: List of candidate blueprints
            trigger_domain: Trigger entity domain
            action_domain: Action entity domain
            trigger_device_class: Optional trigger device class
            action_device_class: Optional action device class
            
        Returns:
            Blueprints sorted by pattern match relevance
        """
        scored = []
        
        for blueprint in blueprints:
            score = self._calculate_pattern_score(
                blueprint,
                trigger_domain,
                action_domain,
                trigger_device_class,
                action_device_class,
            )
            scored.append((blueprint, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [bp for bp, _ in scored]
    
    def _calculate_pattern_score(
        self,
        blueprint: IndexedBlueprint,
        trigger_domain: str,
        action_domain: str,
        trigger_device_class: Optional[str] = None,
        action_device_class: Optional[str] = None,
    ) -> float:
        """
        Calculate pattern match score for a blueprint.
        
        Scoring components:
        - Domain match: 40%
        - Device class match: 30%
        - Quality score: 20%
        - Community rating: 10%
        
        Returns:
            Score between 0.0 and 1.0
        """
        score = 0.0
        
        # Domain match (40%)
        domain_score = 0.0
        required_domains = blueprint.required_domains or []
        
        if trigger_domain in required_domains:
            domain_score += 0.5
        if action_domain in required_domains:
            domain_score += 0.5
        
        # Check action services for action domain
        action_services = blueprint.action_services or []
        for service in action_services:
            if service.startswith(f"{action_domain}."):
                domain_score = min(1.0, domain_score + 0.25)
                break
        
        score += domain_score * 0.4
        
        # Device class match (30%)
        device_class_score = 0.0
        required_device_classes = blueprint.required_device_classes or []
        
        if trigger_device_class:
            if trigger_device_class in required_device_classes:
                device_class_score += 0.6
            elif not required_device_classes:
                # No specific device class required, neutral
                device_class_score += 0.3
        else:
            device_class_score += 0.4  # Partial score for no specific requirement
        
        if action_device_class:
            if action_device_class in required_device_classes:
                device_class_score += 0.4
        else:
            device_class_score += 0.2
        
        score += min(1.0, device_class_score) * 0.3
        
        # Quality score (20%)
        quality = blueprint.quality_score or 0.5
        score += quality * 0.2
        
        # Community rating (10%)
        community = blueprint.community_rating or 0.0
        score += community * 0.1
        
        return min(1.0, score)
    
    def calculate_fit_score(
        self,
        blueprint: IndexedBlueprint,
        user_domains: list[str],
        user_device_classes: list[str],
        same_area: bool = False,
    ) -> float:
        """
        Calculate how well a blueprint fits a user's device inventory.
        
        Args:
            blueprint: Blueprint to score
            user_domains: Domains available in user's inventory
            user_device_classes: Device classes available
            same_area: Whether devices are in the same area
            
        Returns:
            Fit score between 0.0 and 1.0
        """
        score = 0.0
        
        # Required domains coverage (40%)
        required_domains = blueprint.required_domains or []
        if required_domains:
            matched = sum(1 for d in required_domains if d in user_domains)
            domain_coverage = matched / len(required_domains)
            score += domain_coverage * 0.4
        else:
            score += 0.4  # No requirements = full score
        
        # Required device classes coverage (30%)
        required_classes = blueprint.required_device_classes or []
        if required_classes:
            matched = sum(1 for c in required_classes if c in user_device_classes)
            class_coverage = matched / len(required_classes)
            score += class_coverage * 0.3
        else:
            score += 0.3  # No requirements = full score
        
        # Same area bonus (20%)
        if same_area:
            score += 0.2
        else:
            score += 0.1  # Partial score
        
        # Community rating bonus (10%)
        community = blueprint.community_rating or 0.0
        score += community * 0.1
        
        return min(1.0, score)
    
    def rank_by_fit(
        self,
        blueprints: list[IndexedBlueprint],
        user_domains: list[str],
        user_device_classes: list[str],
        same_area: bool = False,
        min_fit_score: float = 0.6,
    ) -> list[tuple[IndexedBlueprint, float]]:
        """
        Rank blueprints by fit score and filter by minimum threshold.
        
        Args:
            blueprints: List of candidate blueprints
            user_domains: User's available domains
            user_device_classes: User's available device classes
            same_area: Whether devices are in the same area
            min_fit_score: Minimum fit score threshold
            
        Returns:
            List of (blueprint, fit_score) tuples sorted by score
        """
        scored = []
        
        for blueprint in blueprints:
            fit_score = self.calculate_fit_score(
                blueprint,
                user_domains,
                user_device_classes,
                same_area,
            )
            
            if fit_score >= min_fit_score:
                scored.append((blueprint, fit_score))
        
        # Sort by fit score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored
