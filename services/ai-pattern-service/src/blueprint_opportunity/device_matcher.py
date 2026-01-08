"""Device-to-blueprint matching algorithm with Wyze pattern integration.

Enhanced January 2026:
- Added temporal relevance scoring (seasonal/time-of-day awareness)
- Added user profile matching (preferences, usage history)
- Improved scoring weights for better recommendations
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import httpx

from .schemas import DeviceSignature, BlueprintSummary

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile for personalized blueprint recommendations."""
    
    # Usage preferences
    preferred_domains: list[str] = field(default_factory=list)
    preferred_use_cases: list[str] = field(default_factory=list)
    
    # Automation preferences
    prefers_simple_automations: bool = True
    prefers_energy_saving: bool = False
    prefers_security_focused: bool = False
    
    # Usage history
    deployed_blueprint_ids: list[str] = field(default_factory=list)
    dismissed_blueprint_ids: list[str] = field(default_factory=list)
    
    # Home characteristics
    has_presence_detection: bool = False
    has_voice_assistant: bool = False
    home_type: str = "house"  # house, apartment, condo
    
    # Time preferences
    active_hours_start: int = 6  # 6 AM
    active_hours_end: int = 22   # 10 PM


class DeviceMatcher:
    """
    Matches user devices to blueprint requirements.
    
    Scoring components (enhanced January 2026):
    - Required domains coverage: 25% (was 30%)
    - Required device classes coverage: 20% (was 25%)
    - Same area bonus: 12% (was 15%)
    - Community rating bonus: 8% (was 10%)
    - Wyze pattern score: 15% (was 20%)
    - Temporal relevance: 10% (NEW - seasonal/time awareness)
    - User profile match: 10% (NEW - personalization)
    """
    
    # Enhanced scoring weights (January 2026)
    DOMAIN_WEIGHT = 0.25           # Was 0.30
    DEVICE_CLASS_WEIGHT = 0.20     # Was 0.25
    SAME_AREA_WEIGHT = 0.12        # Was 0.15
    COMMUNITY_RATING_WEIGHT = 0.08 # Was 0.10
    WYZE_PATTERN_WEIGHT = 0.15     # Was 0.20
    TEMPORAL_WEIGHT = 0.10         # NEW - seasonal/time relevance
    PROFILE_WEIGHT = 0.10          # NEW - user profile matching
    
    # Seasonal domain relevance mapping
    SEASONAL_DOMAINS = {
        # Winter months (Dec, Jan, Feb)
        'climate': {12, 1, 2},
        'thermostat': {12, 1, 2},
        'heater': {12, 1, 2},
        # Summer months (Jun, Jul, Aug)
        'fan': {6, 7, 8},
        'air_conditioner': {6, 7, 8},
        'cover': {6, 7, 8},  # Blinds/shades for sun
        # Dark months (Nov, Dec, Jan, Feb)
        'light': {11, 12, 1, 2},
        # Holiday months
        'scene': {11, 12},  # Holiday scenes
    }
    
    # Use case seasonal relevance
    SEASONAL_USE_CASES = {
        'heating': {10, 11, 12, 1, 2, 3},
        'cooling': {5, 6, 7, 8, 9},
        'lighting': {10, 11, 12, 1, 2},
        'holiday': {11, 12},
        'vacation': {6, 7, 8},
        'energy_saving': {6, 7, 8, 12, 1, 2},  # Peak usage months
    }
    
    # Rule recommendation service URL
    RULE_REC_SERVICE_URL = os.getenv(
        "RULE_RECOMMENDATION_SERVICE_URL",
        "http://rule-recommendation-ml:8035"
    )
    
    def __init__(self, enable_wyze_scoring: bool = True):
        """
        Initialize device matcher.
        
        Args:
            enable_wyze_scoring: Whether to enable Wyze ML pattern scoring.
                                Disable for faster scoring without ML.
        """
        self.enable_wyze_scoring = enable_wyze_scoring
        self._http_client: Optional[httpx.AsyncClient] = None
        self._wyze_service_available: Optional[bool] = None
        
        # Cache for Wyze pattern scores (pattern -> score)
        self._wyze_pattern_cache: dict[str, float] = {}
        self._popular_patterns: Optional[list[tuple[str, float]]] = None
    
    def calculate_fit_score(
        self,
        blueprint: BlueprintSummary,
        devices: list[DeviceSignature],
        same_area: bool = False,
        wyze_pattern_score: Optional[float] = None,
        current_time: Optional[datetime] = None,
        user_profile: Optional[UserProfile] = None,
    ) -> float:
        """
        Calculate how well user's devices match blueprint requirements.
        
        Enhanced with temporal relevance and user profile matching (January 2026).
        
        Args:
            blueprint: Blueprint to score
            devices: User's available devices
            same_area: Whether all matched devices are in the same area
            wyze_pattern_score: Optional pre-computed Wyze pattern score (0.0-1.0)
            current_time: Current datetime for temporal relevance (uses now if None)
            user_profile: User profile for personalized scoring
            
        Returns:
            Fit score between 0.0 and 1.0
        """
        score = 0.0
        
        # Extract user's available domains and device classes
        user_domains = {d.domain for d in devices}
        user_device_classes = {d.device_class for d in devices if d.device_class}
        
        # Required domains coverage (25%)
        required_domains = set(blueprint.required_domains)
        if required_domains:
            matched_domains = required_domains & user_domains
            domain_coverage = len(matched_domains) / len(required_domains)
            score += domain_coverage * self.DOMAIN_WEIGHT
        else:
            score += self.DOMAIN_WEIGHT  # No requirements = full score
        
        # Required device classes coverage (20%)
        required_classes = set(blueprint.required_device_classes)
        if required_classes:
            matched_classes = required_classes & user_device_classes
            class_coverage = len(matched_classes) / len(required_classes)
            score += class_coverage * self.DEVICE_CLASS_WEIGHT
        else:
            score += self.DEVICE_CLASS_WEIGHT  # No requirements = full score
        
        # Same area bonus (12%)
        if same_area:
            score += self.SAME_AREA_WEIGHT
        else:
            score += self.SAME_AREA_WEIGHT * 0.5  # Partial score for different areas
        
        # Community rating bonus (8%)
        score += blueprint.community_rating * self.COMMUNITY_RATING_WEIGHT
        
        # Wyze pattern score (15%)
        if self.enable_wyze_scoring:
            if wyze_pattern_score is not None:
                score += wyze_pattern_score * self.WYZE_PATTERN_WEIGHT
            else:
                pattern_score = self._get_cached_wyze_score(
                    list(required_domains),
                    list(user_domains)
                )
                score += pattern_score * self.WYZE_PATTERN_WEIGHT
        else:
            # Redistribute Wyze weight to other components
            redistribution_factor = 1.0 / (1.0 - self.WYZE_PATTERN_WEIGHT)
            score = score * redistribution_factor * (1.0 - self.TEMPORAL_WEIGHT - self.PROFILE_WEIGHT)
        
        # NEW: Temporal relevance score (10%)
        temporal_score = self._calculate_temporal_score(
            blueprint, 
            current_time or datetime.now()
        )
        score += temporal_score * self.TEMPORAL_WEIGHT
        
        # NEW: User profile match score (10%)
        if user_profile:
            profile_score = self._calculate_profile_score(blueprint, user_profile)
            score += profile_score * self.PROFILE_WEIGHT
        else:
            # Neutral score when no profile available
            score += 0.5 * self.PROFILE_WEIGHT
        
        return min(1.0, score)
    
    def _calculate_temporal_score(
        self,
        blueprint: BlueprintSummary,
        current_time: datetime,
    ) -> float:
        """
        Calculate temporal relevance score based on season and time of day.
        
        Boosts score for seasonally relevant blueprints:
        - Climate blueprints score higher in extreme weather months
        - Lighting blueprints score higher in winter (shorter days)
        - Holiday blueprints score higher in Nov/Dec
        
        Args:
            blueprint: Blueprint to score
            current_time: Current datetime
            
        Returns:
            Temporal relevance score between 0.0 and 1.0
        """
        month = current_time.month
        hour = current_time.hour
        
        score = 0.5  # Neutral baseline
        
        # Check domain seasonal relevance
        for domain in blueprint.required_domains:
            domain_lower = domain.lower()
            if domain_lower in self.SEASONAL_DOMAINS:
                if month in self.SEASONAL_DOMAINS[domain_lower]:
                    score = max(score, 0.9)  # High relevance
                    break
        
        # Check use case seasonal relevance
        use_case = (blueprint.use_case or "").lower()
        for use_case_key, months in self.SEASONAL_USE_CASES.items():
            if use_case_key in use_case:
                if month in months:
                    score = max(score, 0.85)
                    break
        
        # Time-of-day relevance for lighting
        if any(d.lower() in ['light', 'scene'] for d in blueprint.required_domains):
            # Boost lighting blueprints during evening hours
            if 17 <= hour <= 22:  # 5 PM to 10 PM
                score = max(score, 0.8)
        
        # Morning routine relevance
        if 'morning' in use_case or 'wake' in use_case:
            if 5 <= hour <= 9:
                score = max(score, 0.85)
        
        # Night/sleep routine relevance
        if 'night' in use_case or 'sleep' in use_case or 'bedtime' in use_case:
            if 20 <= hour <= 23 or 0 <= hour <= 2:
                score = max(score, 0.85)
        
        return score
    
    def _calculate_profile_score(
        self,
        blueprint: BlueprintSummary,
        profile: UserProfile,
    ) -> float:
        """
        Calculate user profile match score.
        
        Considers:
        - User's preferred domains and use cases
        - Automation complexity preferences
        - Previously deployed/dismissed blueprints
        - Home characteristics
        
        Args:
            blueprint: Blueprint to score
            profile: User profile
            
        Returns:
            Profile match score between 0.0 and 1.0
        """
        score = 0.5  # Neutral baseline
        
        # Check if blueprint was previously dismissed (strong negative signal)
        if blueprint.id in profile.dismissed_blueprint_ids:
            return 0.1  # Very low score for dismissed blueprints
        
        # Check if similar blueprint already deployed (slight negative - avoid duplicates)
        if blueprint.id in profile.deployed_blueprint_ids:
            return 0.3  # Lower score to avoid re-recommending
        
        # Domain preference match
        if profile.preferred_domains:
            domain_overlap = set(blueprint.required_domains) & set(profile.preferred_domains)
            if domain_overlap:
                score = max(score, 0.7 + 0.1 * len(domain_overlap))
        
        # Use case preference match
        use_case = (blueprint.use_case or "").lower()
        for preferred in profile.preferred_use_cases:
            if preferred.lower() in use_case:
                score = max(score, 0.8)
                break
        
        # Complexity preference
        complexity = (blueprint.complexity or "medium").lower()
        if profile.prefers_simple_automations:
            if complexity == "simple":
                score = max(score, 0.75)
            elif complexity == "complex":
                score = min(score, 0.5)  # Penalize complex automations
        
        # Energy saving preference
        if profile.prefers_energy_saving:
            if 'energy' in use_case or 'power' in use_case or 'saving' in use_case:
                score = max(score, 0.85)
        
        # Security preference
        if profile.prefers_security_focused:
            if any(d in ['lock', 'alarm_control_panel', 'camera', 'motion'] 
                   for d in blueprint.required_domains):
                score = max(score, 0.85)
            if 'security' in use_case or 'alert' in use_case:
                score = max(score, 0.85)
        
        # Presence detection bonus
        if profile.has_presence_detection:
            if 'presence' in use_case or 'away' in use_case or 'home' in use_case:
                score = max(score, 0.8)
        
        # Voice assistant bonus
        if profile.has_voice_assistant:
            if 'voice' in use_case or 'assistant' in use_case:
                score = max(score, 0.75)
        
        return min(1.0, score)
    
    def _get_cached_wyze_score(
        self,
        trigger_domains: list[str],
        action_domains: list[str],
    ) -> float:
        """
        Get Wyze pattern score from cache.
        
        This synchronous method uses cached data. For fresh scores,
        use the async method get_wyze_pattern_score().
        """
        if not trigger_domains or not action_domains:
            return 0.0
        
        best_score = 0.0
        
        # Check cache for matching patterns
        for trigger in trigger_domains:
            for action in action_domains:
                pattern = f"{trigger}_to_{action}"
                if pattern in self._wyze_pattern_cache:
                    best_score = max(best_score, self._wyze_pattern_cache[pattern])
        
        # If no cache hit, try popular patterns
        if best_score == 0.0 and self._popular_patterns:
            all_domains = set(trigger_domains) | set(action_domains)
            for pattern, popularity in self._popular_patterns[:50]:
                parts = pattern.split("_to_")
                if len(parts) == 2:
                    if parts[0] in all_domains or parts[1] in all_domains:
                        # Scale popularity to 0-1 range
                        best_score = max(best_score, min(1.0, popularity / 10000))
        
        return best_score
    
    async def get_wyze_pattern_score(
        self,
        trigger_domains: list[str],
        user_domains: list[str],
    ) -> float:
        """
        Get ML-based pattern score from Wyze Rule Recommendation service.
        
        Args:
            trigger_domains: Blueprint trigger domains
            user_domains: User's available device domains
            
        Returns:
            Pattern score between 0.0 and 1.0
        """
        if not self.enable_wyze_scoring:
            return 0.0
        
        # Check if service is available
        if self._wyze_service_available is False:
            return self._get_cached_wyze_score(trigger_domains, user_domains)
        
        try:
            # Lazy initialize HTTP client
            if self._http_client is None:
                self._http_client = httpx.AsyncClient(timeout=5.0)
            
            # Request device-based recommendations
            params = {"device_domains": user_domains, "limit": 20}
            response = await self._http_client.get(
                f"{self.RULE_REC_SERVICE_URL}/api/v1/rule-recommendations",
                params=params,
            )
            
            if response.status_code != 200:
                self._wyze_service_available = False
                logger.warning(
                    f"Wyze service returned {response.status_code}, disabling"
                )
                return 0.0
            
            self._wyze_service_available = True
            data = response.json()
            
            # Calculate pattern match score
            best_score = 0.0
            for rec in data.get("recommendations", []):
                trigger = rec.get("trigger_domain", "")
                if trigger in trigger_domains:
                    score = rec.get("score", 0.0)
                    best_score = max(best_score, min(1.0, score))
                    
                    # Cache the result
                    pattern = rec.get("rule_pattern", "")
                    if pattern:
                        self._wyze_pattern_cache[pattern] = score
            
            return best_score
            
        except httpx.TimeoutException:
            logger.warning("Wyze service timeout, using cached scores")
            return self._get_cached_wyze_score(trigger_domains, user_domains)
        except Exception as e:
            logger.warning(f"Error calling Wyze service: {e}")
            self._wyze_service_available = False
            return self._get_cached_wyze_score(trigger_domains, user_domains)
    
    async def refresh_popular_patterns(self) -> None:
        """Refresh the cache of popular patterns from Wyze service."""
        if not self.enable_wyze_scoring:
            return
        
        try:
            if self._http_client is None:
                self._http_client = httpx.AsyncClient(timeout=5.0)
            
            response = await self._http_client.get(
                f"{self.RULE_REC_SERVICE_URL}/api/v1/rule-recommendations/popular",
                params={"limit": 100},
            )
            
            if response.status_code == 200:
                data = response.json()
                self._popular_patterns = [
                    (rec["rule_pattern"], rec["score"])
                    for rec in data.get("recommendations", [])
                ]
                
                # Also cache these patterns
                for pattern, score in self._popular_patterns:
                    self._wyze_pattern_cache[pattern] = min(1.0, score / 10000)
                
                logger.info(f"Refreshed {len(self._popular_patterns)} popular patterns")
                self._wyze_service_available = True
            else:
                logger.warning(f"Failed to refresh popular patterns: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Error refreshing popular patterns: {e}")
    
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
        Rank blueprints by fit score (synchronous version).
        
        For better Wyze ML scoring, use rank_blueprints_async() instead.
        
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
    
    async def rank_blueprints_async(
        self,
        blueprints: list[BlueprintSummary],
        devices: list[DeviceSignature],
        min_fit_score: float = 0.6,
    ) -> list[tuple[BlueprintSummary, float, list[DeviceSignature], bool]]:
        """
        Rank blueprints by fit score with async Wyze ML scoring.
        
        This version fetches fresh Wyze pattern scores from the ML service
        for more accurate recommendations.
        
        Args:
            blueprints: List of blueprints to rank
            devices: User's available devices
            min_fit_score: Minimum fit score threshold
            
        Returns:
            List of (blueprint, fit_score, matched_devices, same_area) sorted by score
        """
        results = []
        
        # Get user's device domains for Wyze scoring
        user_domains = list({d.domain for d in devices})
        
        # Refresh popular patterns cache
        if self.enable_wyze_scoring and self._popular_patterns is None:
            await self.refresh_popular_patterns()
        
        for blueprint in blueprints:
            matched_devices = self.find_matching_devices(blueprint, devices)
            
            if not matched_devices:
                continue
            
            same_area, _, _ = self.check_same_area(matched_devices)
            
            # Get Wyze pattern score asynchronously
            wyze_score = None
            if self.enable_wyze_scoring:
                trigger_domains = list(blueprint.required_domains)
                wyze_score = await self.get_wyze_pattern_score(trigger_domains, user_domains)
            
            fit_score = self.calculate_fit_score(
                blueprint, 
                matched_devices, 
                same_area,
                wyze_pattern_score=wyze_score
            )
            
            if fit_score >= min_fit_score:
                results.append((blueprint, fit_score, matched_devices, same_area))
        
        # Sort by fit score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
    
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
