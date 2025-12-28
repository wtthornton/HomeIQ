"""
Home Assistant Version Detection Service

Detects Home Assistant version and capabilities for version-aware YAML generation.
"""

import logging
from typing import Any
from datetime import datetime, timedelta, timezone

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings

logger = logging.getLogger(__name__)


class HAVersionService:
    """
    Service for detecting Home Assistant version and capabilities.
    
    Features:
    - Query HA /api/config endpoint for version
    - Cache version information
    - Map version to feature support matrix
    """
    
    def __init__(self, ha_base_url: str | None = None, ha_token: str | None = None):
        """
        Initialize HA version service.
        
        Args:
            ha_base_url: Home Assistant base URL (defaults to settings.ha_url)
            ha_token: Home Assistant access token (defaults to settings.ha_token)
        """
        self.ha_base_url = (ha_base_url or settings.ha_url or "").rstrip('/')
        self.ha_token = ha_token or settings.ha_token
        
        # Cache for version information
        self._version_cache: dict[str, Any] | None = None
        self._cache_expiry: datetime | None = None
        self._cache_ttl = timedelta(hours=1)  # Cache for 1 hour
        
        # Feature support matrix by version
        self._feature_support = {
            "2025.10": {
                "initial_state_required": True,
                "singular_trigger_action": True,  # trigger: not triggers:
                "singular_action": True,  # action: not actions:
                "error_handling": True,  # error: continue instead of continue_on_error
                "blueprints": True,
                "variables": True,
                "trigger_variables": True,
            },
            "2025.1": {
                "initial_state_required": True,
                "singular_trigger_action": True,
                "singular_action": True,
                "error_handling": True,
                "blueprints": True,
                "variables": True,
                "trigger_variables": True,
            },
            "2024.12": {
                "initial_state_required": False,
                "singular_trigger_action": False,  # Uses triggers: and actions:
                "singular_action": False,
                "error_handling": False,  # Uses continue_on_error
                "blueprints": True,
                "variables": True,
                "trigger_variables": False,
            },
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def get_version(self, use_cache: bool = True) -> str | None:
        """
        Get Home Assistant version.
        
        Args:
            use_cache: Whether to use cached version (default: True)
        
        Returns:
            Version string (e.g., "2025.10.3") or None if unavailable
        """
        # Check cache
        if use_cache and self._version_cache and self._cache_expiry:
            if datetime.now(timezone.utc) < self._cache_expiry:
                return self._version_cache.get("version")
        
        if not self.ha_base_url or not self.ha_token:
            logger.warning("HA base URL or token not configured")
            return None
        
        try:
            url = f"{self.ha_base_url}/api/config"
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                config = response.json()
                
                version = config.get("version")
                
                # Update cache
                self._version_cache = {"version": version, "config": config}
                self._cache_expiry = datetime.now(timezone.utc) + self._cache_ttl
                
                logger.info(f"Detected Home Assistant version: {version}")
                return version
        
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch HA version: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching HA version: {e}")
            return None
    
    async def get_major_minor_version(self, use_cache: bool = True) -> str | None:
        """
        Get major.minor version (e.g., "2025.10" from "2025.10.3").
        
        Args:
            use_cache: Whether to use cached version (default: True)
        
        Returns:
            Major.minor version string or None
        """
        version = await self.get_version(use_cache=use_cache)
        if not version:
            return None
        
        # Extract major.minor (e.g., "2025.10" from "2025.10.3")
        parts = version.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return version
    
    def supports_feature(self, feature: str, version: str | None = None) -> bool:
        """
        Check if a version supports a specific feature.
        
        Args:
            feature: Feature name (e.g., "initial_state_required", "singular_trigger_action")
            version: Version to check (default: uses cached version)
        
        Returns:
            True if feature is supported, False otherwise
        """
        if version is None:
            # Use cached version if available
            if self._version_cache:
                version = self._version_cache.get("version")
            else:
                logger.warning("No version available for feature check")
                return False
        
        if not version:
            return False
        
        # Extract major.minor version
        major_minor = self._get_major_minor(version)
        
        # Check feature support
        if major_minor in self._feature_support:
            return self._feature_support[major_minor].get(feature, False)
        
        # Default: assume newer versions support all features
        # For older versions, check if any known version supports it
        for v, features in self._feature_support.items():
            if features.get(feature, False):
                # Feature exists in some version, check if our version is newer
                if self._compare_versions(major_minor, v) >= 0:
                    return True
        
        return False
    
    def _get_major_minor(self, version: str) -> str:
        """Extract major.minor version from full version string."""
        parts = version.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return version
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.
        
        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
        v1_parts = [int(x) for x in v1.split(".")]
        v2_parts = [int(x) for x in v2.split(".")]
        
        # Pad with zeros to same length
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for p1, p2 in zip(v1_parts, v2_parts):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        
        return 0
    
    async def get_capabilities(self, use_cache: bool = True) -> dict[str, Any]:
        """
        Get Home Assistant capabilities for the current version.
        
        Args:
            use_cache: Whether to use cached information (default: True)
        
        Returns:
            Dictionary of capabilities
        """
        version = await self.get_major_minor_version(use_cache=use_cache)
        if not version:
            return {}
        
        if version in self._feature_support:
            return self._feature_support[version].copy()
        
        # Default capabilities for unknown versions
        return {
            "initial_state_required": True,
            "singular_trigger_action": True,
            "singular_action": True,
            "error_handling": True,
            "blueprints": True,
            "variables": True,
            "trigger_variables": True,
        }
    
    def clear_cache(self):
        """Clear version cache."""
        self._version_cache = None
        self._cache_expiry = None
        logger.debug("HA version cache cleared")

