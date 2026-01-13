"""
Device Capability Analyzer Module

Phase 1.3: Integrate device intelligence service capabilities for capability-based synergy detection.

Analyzes device capabilities to discover synergy opportunities based on device features,
such as dimmable lights, color control, scheduling, etc.
"""

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class DeviceCapabilityAnalyzer:
    """
    Analyzes device capabilities for capability-based synergy detection.
    
    Integrates with device-intelligence-service to fetch device capabilities
    and suggests synergies based on capability compatibility.
    
    Attributes:
        base_url: Device intelligence service base URL
        enabled: Whether capability analysis is enabled
        timeout: HTTP request timeout in seconds
        _cache: Internal cache for device capabilities
    """
    
    def __init__(
        self,
        base_url: str = "http://device-intelligence-service:8028",
        enabled: bool = True,
        timeout: float = 5.0
    ):
        """
        Initialize device capability analyzer.
        
        Args:
            base_url: Device intelligence service base URL
            enabled: Whether capability analysis is enabled
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.enabled = enabled
        self.timeout = timeout
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client.
        
        Returns:
            httpx.AsyncClient instance
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self._http_client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def analyze_device_capabilities(
        self,
        device_id: str
    ) -> list[dict[str, Any]]:
        """
        Fetch and parse capabilities for a device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            List of capability dictionaries, or empty list if device not found or service unavailable
        """
        if not self.enabled:
            return []
        
        # Check cache first
        if device_id in self._cache:
            return self._cache[device_id]
        
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/api/devices/{device_id}/capabilities"
            )
            response.raise_for_status()
            
            data = response.json()
            # Handle response format (list of DeviceCapabilityResponse)
            if isinstance(data, list):
                capabilities = data
            elif isinstance(data, dict) and "capabilities" in data:
                capabilities = data["capabilities"]
            else:
                logger.warning(f"Unexpected capabilities response format for device {device_id}: {type(data)}")
                capabilities = []
            
            # Cache capabilities
            self._cache[device_id] = capabilities
            return capabilities
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Device not found - return empty list
                logger.debug(f"Device {device_id} not found in device intelligence service")
                return []
            logger.warning(f"⚠️ Device Intelligence Service error for capabilities ({device_id}): {e.response.status_code}")
            return []
        except httpx.RequestError as e:
            logger.warning(f"⚠️ Device Intelligence Service unavailable for capabilities ({device_id}): {e}")
            return []
        except Exception as e:
            logger.warning(f"⚠️ Error getting device capabilities for {device_id}: {e}")
            return []
    
    def match_capabilities(
        self,
        device1_capabilities: list[dict[str, Any]],
        device2_capabilities: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Check capability compatibility between two devices.
        
        Args:
            device1_capabilities: List of capability dictionaries for device 1
            device2_capabilities: List of capability dictionaries for device 2
            
        Returns:
            Dictionary with:
            - compatible: bool - Whether devices are compatible
            - match_score: float - Compatibility score (0.0-1.0)
            - matching_capabilities: list - List of matching capability pairs
            - rationale: str - Explanation of compatibility
        """
        if not device1_capabilities or not device2_capabilities:
            return {
                'compatible': False,
                'match_score': 0.0,
                'matching_capabilities': [],
                'rationale': 'One or both devices have no capabilities'
            }
        
        # Extract capability types and names
        device1_types = {cap.get('capability_type', '') for cap in device1_capabilities}
        device1_names = {cap.get('capability_name', '') for cap in device1_capabilities}
        device2_types = {cap.get('capability_type', '') for cap in device2_capabilities}
        device2_names = {cap.get('capability_name', '') for cap in device2_capabilities}
        
        # Common compatibility patterns
        matching_pairs = []
        match_score = 0.0
        
        # Pattern 1: Both support dimming (light + light, light + switch)
        if any('brightness' in name.lower() or 'dimmable' in name.lower() 
               for name in device1_names) and \
           any('brightness' in name.lower() or 'dimmable' in name.lower() 
               for name in device2_names):
            matching_pairs.append(('dimmable', 'dimmable'))
            match_score += 0.3
        
        # Pattern 2: Both support color control (color lights)
        if any('color' in name.lower() or 'rgb' in name.lower() 
               for name in device1_names) and \
           any('color' in name.lower() or 'rgb' in name.lower() 
               for name in device2_names):
            matching_pairs.append(('color_control', 'color_control'))
            match_score += 0.3
        
        # Pattern 3: Scheduling capabilities
        if any('schedule' in name.lower() or 'timer' in name.lower() 
               for name in device1_names) and \
           any('schedule' in name.lower() or 'timer' in name.lower() 
               for name in device2_names):
            matching_pairs.append(('scheduling', 'scheduling'))
            match_score += 0.2
        
        # Pattern 4: Scene support
        if any('scene' in name.lower() for name in device1_names) and \
           any('scene' in name.lower() for name in device2_names):
            matching_pairs.append(('scene', 'scene'))
            match_score += 0.2
        
        # Normalize match score to 0.0-1.0
        match_score = min(1.0, match_score)
        
        compatible = match_score >= 0.3  # Threshold for compatibility
        
        rationale = f"Capability match score: {match_score:.2f}"
        if matching_pairs:
            rationale += f". Matching capabilities: {', '.join(pair[0] for pair in matching_pairs)}"
        
        return {
            'compatible': compatible,
            'match_score': match_score,
            'matching_capabilities': matching_pairs,
            'rationale': rationale
        }
    
    async def suggest_capability_synergy(
        self,
        device1_id: str,
        device2_id: str,
        device1_capabilities: Optional[list[dict[str, Any]]] = None,
        device2_capabilities: Optional[list[dict[str, Any]]] = None
    ) -> Optional[dict[str, Any]]:
        """
        Suggest capability-based synergy between two devices.
        
        Args:
            device1_id: First device identifier
            device2_id: Second device identifier
            device1_capabilities: Optional pre-fetched capabilities for device 1
            device2_capabilities: Optional pre-fetched capabilities for device 2
            
        Returns:
            Synergy dictionary if compatible, None otherwise
        """
        # Fetch capabilities if not provided
        if device1_capabilities is None:
            device1_capabilities = await self.analyze_device_capabilities(device1_id)
        if device2_capabilities is None:
            device2_capabilities = await self.analyze_device_capabilities(device2_id)
        
        # Match capabilities
        match_result = self.match_capabilities(device1_capabilities, device2_capabilities)
        
        if not match_result['compatible']:
            return None
        
        # Create synergy suggestion
        import uuid
        synergy = {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'device_pair',
            'devices': [device1_id, device2_id],
            'trigger_entity': device1_id,
            'action_entity': device2_id,
            'impact_score': 0.5 + (match_result['match_score'] * 0.3),  # 0.5-0.8 range
            'confidence': 0.6 + (match_result['match_score'] * 0.2),  # 0.6-0.8 range
            'complexity': 'low',
            'rationale': f"Capability-based synergy: {match_result['rationale']}",
            'synergy_depth': 2,
            'chain_devices': [device1_id, device2_id],
            'context_metadata': {
                'detection_method': 'capability_analysis',
                'capability_match_score': match_result['match_score'],
                'matching_capabilities': match_result['matching_capabilities']
            }
        }
        
        return synergy
    
    def clear_cache(self) -> None:
        """Clear capability cache."""
        self._cache.clear()
