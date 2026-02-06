"""Suggestion scorer with 2025 scoring pattern for blueprint suggestions."""

import logging
from datetime import datetime
from typing import Any, Optional

from ..config import settings
from .external_schemas import BlueprintSummary, DeviceSignature, UserProfile

try:
    from blueprint_opportunity.device_matcher import DeviceMatcher
    DEVICE_MATCHER_AVAILABLE = True
except ImportError:
    DEVICE_MATCHER_AVAILABLE = False
    DeviceMatcher = None

logger = logging.getLogger(__name__)

if not DEVICE_MATCHER_AVAILABLE:
    logger.warning("DeviceMatcher not available, using fallback scoring")


class SuggestionScorer:
    """
    Scores blueprint suggestions using 2025 pattern.
    
    Enhanced scoring combines:
    - DeviceMatcher scoring (50%): domain, device_class, area matching, temporal, user profile
    - Blueprint quality score (15%): blueprint quality_score (0.0-1.0)
    - Community rating (10%): blueprint community_rating (0.0-1.0)
    - Temporal relevance (10%): already in DeviceMatcher
    - User profile match (10%): already in DeviceMatcher
    - Complexity bonus (5%): simpler blueprints get bonus
    """
    
    def __init__(self, enable_wyze_scoring: bool = True):
        """Initialize suggestion scorer."""
        self.enable_wyze_scoring = enable_wyze_scoring
        if DEVICE_MATCHER_AVAILABLE:
            self.device_matcher = DeviceMatcher(enable_wyze_scoring=enable_wyze_scoring)
        else:
            self.device_matcher = None
            logger.warning("DeviceMatcher not available, scoring will be limited")
    
    def calculate_suggestion_score(
        self,
        blueprint: dict[str, Any],
        devices: list[dict[str, Any]],
        user_profile: Optional[dict[str, Any]] = None,
        current_time: Optional[datetime] = None,
    ) -> float:
        """
        Calculate comprehensive suggestion score for a blueprint-device combination.
        
        Args:
            blueprint: Blueprint dictionary with fields: id, name, required_domains, 
                       required_device_classes, quality_score, community_rating, complexity
            devices: List of device dictionaries from data-api
            user_profile: Optional user profile dictionary
            current_time: Optional current datetime for temporal relevance
            
        Returns:
            Score between 0.0 and 1.0
        """
        if not self.device_matcher:
            # Fallback scoring without DeviceMatcher
            return self._calculate_fallback_score(blueprint, devices)
        
        # Convert blueprint dict to BlueprintSummary
        blueprint_summary = self._dict_to_blueprint_summary(blueprint)
        
        # Convert device dicts to DeviceSignature
        device_signatures = [self._dict_to_device_signature(d) for d in devices]
        
        # Calculate same_area bonus
        area_ids = {d.get("area_id") for d in devices if d.get("area_id")}
        same_area = len(area_ids) <= 1
        
        # Convert user profile if provided
        user_profile_obj = None
        if user_profile:
            user_profile_obj = self._dict_to_user_profile(user_profile)
        
        # Get device match score from DeviceMatcher (includes temporal and profile)
        device_match_score = self.device_matcher.calculate_fit_score(
            blueprint=blueprint_summary,
            devices=device_signatures,
            same_area=same_area,
            current_time=current_time or datetime.now(),
            user_profile=user_profile_obj,
        )
        
        # Extract blueprint-specific scores
        blueprint_quality_score = float(blueprint.get("quality_score", 0.5))
        community_rating = float(blueprint.get("community_rating", 0.0))
        complexity = str(blueprint.get("complexity", "medium")).lower()
        
        # Calculate complexity bonus
        complexity_bonus = self._calculate_complexity_bonus(complexity)
        
        # Calculate final score with normalized weights from config.
        # temporal_relevance and user_profile weights are already included in
        # device_match_score via DeviceMatcher, so we only apply the remaining 4
        # weights and normalize them to sum to 1.0.
        applied_weight_sum = (
            settings.device_match_weight
            + settings.blueprint_quality_weight
            + settings.community_rating_weight
            + settings.complexity_bonus_weight
        )
        norm = 1.0 / applied_weight_sum if applied_weight_sum > 0 else 1.0

        final_score = (
            device_match_score * settings.device_match_weight * norm +
            blueprint_quality_score * settings.blueprint_quality_weight * norm +
            community_rating * settings.community_rating_weight * norm +
            complexity_bonus * settings.complexity_bonus_weight * norm
        )
        
        return min(1.0, max(0.0, final_score))
    
    def _calculate_complexity_bonus(self, complexity: str) -> float:
        """Calculate complexity bonus (simpler = better)."""
        complexity_lower = complexity.lower()
        if complexity_lower == "simple":
            return 1.0  # Full bonus
        elif complexity_lower == "medium":
            return 0.4  # Partial bonus
        else:
            return 0.0  # No bonus for high complexity
    
    def _calculate_fallback_score(
        self,
        blueprint: dict[str, Any],
        devices: list[dict[str, Any]],
    ) -> float:
        """Fallback scoring when DeviceMatcher is not available."""
        score = 0.0
        
        # Basic domain matching (50%)
        required_domains = set(blueprint.get("required_domains", []))
        device_domains = {d.get("domain") for d in devices if d.get("domain")}
        if required_domains:
            matched_domains = required_domains & device_domains
            domain_coverage = len(matched_domains) / len(required_domains)
            score += domain_coverage * 0.5
        else:
            score += 0.5
        
        # Blueprint quality (30%)
        quality_score = float(blueprint.get("quality_score", 0.5))
        score += quality_score * 0.3
        
        # Community rating (20%)
        community_rating = float(blueprint.get("community_rating", 0.0))
        score += community_rating * 0.2
        
        return min(1.0, score)
    
    def _dict_to_blueprint_summary(self, blueprint_dict: dict[str, Any]) -> Any:
        """Convert blueprint dict to BlueprintSummary object."""
        if not DEVICE_MATCHER_AVAILABLE:
            return blueprint_dict
        
        return BlueprintSummary(
            id=blueprint_dict.get("id", ""),
            name=blueprint_dict.get("name", ""),
            description=blueprint_dict.get("description"),
            source_url=blueprint_dict.get("source_url", ""),
            source_type=blueprint_dict.get("source_type", "unknown"),
            domain=blueprint_dict.get("domain", "automation"),
            use_case=blueprint_dict.get("use_case"),
            required_domains=blueprint_dict.get("required_domains", []),
            required_device_classes=blueprint_dict.get("required_device_classes", []),
            community_rating=float(blueprint_dict.get("community_rating", 0.0)),
            quality_score=float(blueprint_dict.get("quality_score", 0.5)),
            stars=int(blueprint_dict.get("stars", 0)),
            complexity=blueprint_dict.get("complexity", "medium"),
            author=blueprint_dict.get("author"),
        )
    
    def _dict_to_device_signature(self, device_dict: dict[str, Any]) -> Any:
        """Convert device/entity dict to DeviceSignature object."""
        if not DEVICE_MATCHER_AVAILABLE:
            return device_dict
        
        # Handle both entity and device dicts
        entity_id = device_dict.get("entity_id") or device_dict.get("id", "")
        domain = device_dict.get("domain", "")
        
        return DeviceSignature(
            entity_id=entity_id,
            domain=domain,
            device_class=device_dict.get("device_class"),
            area_id=device_dict.get("area_id"),
            area_name=device_dict.get("area_name"),
            device_id=device_dict.get("device_id"),
            friendly_name=device_dict.get("friendly_name") or device_dict.get("name"),
            manufacturer=device_dict.get("manufacturer"),
            model=device_dict.get("model"),
            integration=device_dict.get("integration") or device_dict.get("platform"),
        )
    
    def _dict_to_user_profile(self, profile_dict: dict[str, Any]) -> Any:
        """Convert user profile dict to UserProfile object."""
        if not DEVICE_MATCHER_AVAILABLE:
            return None
        
        return UserProfile(
            preferred_domains=profile_dict.get("preferred_domains", []),
            preferred_use_cases=profile_dict.get("preferred_use_cases", []),
            prefers_simple_automations=profile_dict.get("prefers_simple_automations", True),
            prefers_energy_saving=profile_dict.get("prefers_energy_saving", False),
            prefers_security_focused=profile_dict.get("prefers_security_focused", False),
            deployed_blueprint_ids=profile_dict.get("deployed_blueprint_ids", []),
            dismissed_blueprint_ids=profile_dict.get("dismissed_blueprint_ids", []),
            has_presence_detection=profile_dict.get("has_presence_detection", False),
            has_voice_assistant=profile_dict.get("has_voice_assistant", False),
            home_type=profile_dict.get("home_type", "house"),
            active_hours_start=profile_dict.get("active_hours_start", 6),
            active_hours_end=profile_dict.get("active_hours_end", 22),
        )
