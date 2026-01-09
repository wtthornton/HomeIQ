"""
Device Validation Service for Proactive Agent Service

Validates that suggestions only reference devices that exist in Home Assistant.
Prevents LLM hallucination of non-existent devices.

Epic: Proactive Suggestions Device Validation
Story: Device Existence Validation (P0)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of device validation."""
    
    is_valid: bool
    suggestion_text: str
    mentioned_devices: list[str] = field(default_factory=list)
    invalid_devices: list[str] = field(default_factory=list)
    reason: str | None = None


class DeviceValidationService:
    """
    Validates that suggestions reference only existing devices.
    
    Fetches device inventory from ha-ai-agent-service and validates
    suggestion text against actual devices in Home Assistant.
    
    This prevents LLM hallucination by:
    1. Providing explicit device list to constrain LLM
    2. Post-generation validation to catch any hallucinated devices
    """
    
    # Patterns to extract device mentions from suggestion text
    DEVICE_PATTERNS = [
        # "Smart X" pattern (e.g., "Smart Humidifier", "Smart Thermostat")
        r'\bSmart\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
        
        # "your X" pattern (e.g., "your Thermostat", "your Living Room Light")
        r'\byour\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
        
        # "the X" with device keywords
        r'\bthe\s+([\w\s]+(?:light|switch|sensor|thermostat|fan|lock|camera|speaker|humidifier|dehumidifier|plug|outlet|shade|blind|curtain|door|garage|ac|heater|hvac)s?)\b',
        
        # "set/turn/adjust X" pattern
        r'\b(?:set|turn|adjust|activate|enable|disable)\s+(?:the\s+|your\s+)?([\w\s]+(?:light|switch|sensor|thermostat|fan|lock|camera|speaker|humidifier|plug|shade)s?)\b',
        
        # Quoted names
        r'"([^"]+)"',
        r"'([^']+)'",
    ]
    
    # Device type keywords to check for domain existence
    DEVICE_TYPE_KEYWORDS = {
        "humidifier": ["humidifier", "humidity"],
        "dehumidifier": ["dehumidifier"],
        "climate": ["thermostat", "hvac", "heating", "cooling", "ac", "air conditioning"],
        "light": ["light", "lamp", "bulb"],
        "switch": ["switch", "plug", "outlet"],
        "fan": ["fan"],
        "lock": ["lock"],
        "camera": ["camera"],
        "cover": ["shade", "blind", "curtain", "garage door"],
        "media_player": ["speaker", "tv", "media"],
    }
    
    def __init__(
        self,
        ha_agent_url: str = "http://ha-ai-agent-service:8030",
        cache_ttl_seconds: int = 300,  # 5 minutes
    ):
        """
        Initialize DeviceValidationService.
        
        Args:
            ha_agent_url: URL for HA AI Agent service
            cache_ttl_seconds: TTL for device inventory cache
        """
        self.ha_agent_url = ha_agent_url.rstrip("/")
        self.cache_ttl_seconds = cache_ttl_seconds
        
        # Cache for device inventory
        self._device_cache: list[dict[str, Any]] | None = None
        self._cache_expires_at: datetime | None = None
        
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info(
            f"DeviceValidationService initialized "
            f"(ha_agent_url={ha_agent_url}, cache_ttl={cache_ttl_seconds}s)"
        )
    
    async def get_device_inventory(self) -> list[dict[str, Any]]:
        """
        Fetch all devices from Home Assistant via ha-ai-agent-service.
        
        Uses caching to avoid repeated API calls.
        
        Returns:
            List of device dicts with keys: entity_id, friendly_name, domain
        """
        # Check cache
        if self._device_cache is not None and self._cache_expires_at:
            if datetime.now() < self._cache_expires_at:
                logger.debug(f"Using cached device inventory ({len(self._device_cache)} devices)")
                return self._device_cache
        
        try:
            # Fetch from ha-ai-agent-service
            logger.info("Fetching device inventory from ha-ai-agent-service...")
            
            # Use /api/v1/context endpoint (not tier1)
            response = await self.http_client.get(
                f"{self.ha_agent_url}/api/v1/context"
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch device inventory: {response.status_code}")
                return self._device_cache or []
            
            data = response.json()
            context = data.get("context", "")
            
            # Parse devices from context
            devices = self._parse_devices_from_context(context)
            
            # Update cache
            self._device_cache = devices
            self._cache_expires_at = datetime.now() + timedelta(seconds=self.cache_ttl_seconds)
            
            logger.info(f"Device inventory updated: {len(devices)} devices")
            return devices
            
        except Exception as e:
            logger.error(f"Error fetching device inventory: {e}", exc_info=True)
            return self._device_cache or []
    
    def _parse_devices_from_context(self, context: str) -> list[dict[str, Any]]:
        """
        Parse device information from tier1 context string.
        
        Args:
            context: Raw context string from ha-ai-agent-service
            
        Returns:
            List of device dictionaries
        """
        devices = []
        
        # Look for entity patterns in context
        # Format: entity_id (friendly_name) or entity_id: friendly_name
        entity_pattern = r'([\w]+\.[\w_]+)(?:\s*[:\(]\s*([^\)\n]+))?'
        
        for match in re.finditer(entity_pattern, context):
            entity_id = match.group(1)
            friendly_name = match.group(2) or entity_id.split(".")[-1].replace("_", " ").title()
            domain = entity_id.split(".")[0]
            
            devices.append({
                "entity_id": entity_id,
                "friendly_name": friendly_name.strip(),
                "domain": domain,
            })
        
        # Deduplicate by entity_id
        seen = set()
        unique_devices = []
        for device in devices:
            if device["entity_id"] not in seen:
                seen.add(device["entity_id"])
                unique_devices.append(device)
        
        return unique_devices
    
    async def validate_suggestion(
        self,
        suggestion_text: str,
    ) -> ValidationResult:
        """
        Validate that a suggestion only references existing devices.
        
        Args:
            suggestion_text: The suggestion prompt text
            
        Returns:
            ValidationResult with validation status and details
        """
        # Get device inventory
        devices = await self.get_device_inventory()
        
        if not devices:
            logger.warning("No device inventory available - skipping validation")
            return ValidationResult(
                is_valid=True,
                suggestion_text=suggestion_text,
                reason="Device inventory unavailable - validation skipped",
            )
        
        # Extract device mentions from suggestion
        mentioned_devices = self.extract_device_mentions(suggestion_text)
        
        if not mentioned_devices:
            # No specific devices mentioned - likely generic suggestion
            return ValidationResult(
                is_valid=True,
                suggestion_text=suggestion_text,
                mentioned_devices=[],
                reason="No specific devices mentioned",
            )
        
        # Build set of known device names (lowercase for comparison)
        known_names = set()
        for device in devices:
            known_names.add(device["friendly_name"].lower())
            known_names.add(device["entity_id"].lower())
            # Also add simplified versions
            name = device["friendly_name"].lower()
            known_names.add(name.replace(" ", ""))
            # Add domain-based variations
            if device["domain"] in ["light", "switch", "climate", "fan"]:
                known_names.add(device["domain"])
        
        # Check each mentioned device
        invalid_devices = []
        for mentioned in mentioned_devices:
            mentioned_lower = mentioned.lower()
            
            # Check if it matches any known device
            is_known = False
            for known in known_names:
                if mentioned_lower in known or known in mentioned_lower:
                    is_known = True
                    break
            
            if not is_known:
                # Check if it's a device type that doesn't exist
                device_type = self._get_device_type_from_mention(mentioned)
                if device_type:
                    has_type = await self.has_device_type(device_type)
                    if not has_type:
                        invalid_devices.append(mentioned)
                else:
                    # Unknown device mention
                    invalid_devices.append(mentioned)
        
        if invalid_devices:
            logger.warning(
                f"Suggestion references non-existent devices: {invalid_devices}"
            )
            return ValidationResult(
                is_valid=False,
                suggestion_text=suggestion_text,
                mentioned_devices=mentioned_devices,
                invalid_devices=invalid_devices,
                reason=f"References non-existent devices: {', '.join(invalid_devices)}",
            )
        
        return ValidationResult(
            is_valid=True,
            suggestion_text=suggestion_text,
            mentioned_devices=mentioned_devices,
            invalid_devices=[],
        )
    
    def extract_device_mentions(self, text: str) -> list[str]:
        """
        Extract potential device mentions from suggestion text.
        
        Args:
            text: Suggestion text
            
        Returns:
            List of potential device name mentions
        """
        mentions = []
        
        for pattern in self.DEVICE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                mention = match.group(1) if match.lastindex else match.group(0)
                mention = mention.strip()
                if mention and len(mention) > 2:
                    mentions.append(mention)
        
        # Deduplicate while preserving order
        seen = set()
        unique_mentions = []
        for mention in mentions:
            lower = mention.lower()
            if lower not in seen:
                seen.add(lower)
                unique_mentions.append(mention)
        
        return unique_mentions
    
    def _get_device_type_from_mention(self, mention: str) -> str | None:
        """
        Determine device type from a device mention.
        
        Args:
            mention: Device mention string
            
        Returns:
            Device type/domain if identified, None otherwise
        """
        mention_lower = mention.lower()
        
        for device_type, keywords in self.DEVICE_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in mention_lower:
                    return device_type
        
        return None
    
    async def has_device_type(self, device_type: str) -> bool:
        """
        Check if a device type/domain exists in the inventory.
        
        Args:
            device_type: Domain like 'humidifier', 'climate', 'light'
            
        Returns:
            True if at least one device of this type exists
        """
        devices = await self.get_device_inventory()
        
        for device in devices:
            if device.get("domain") == device_type:
                return True
        
        return False
    
    async def get_device_domains(self) -> set[str]:
        """
        Get set of device domains that exist in the home.
        
        Returns:
            Set of domain strings (e.g., {'light', 'switch', 'climate'})
        """
        devices = await self.get_device_inventory()
        return {device.get("domain", "") for device in devices if device.get("domain")}
    
    async def get_device_list_for_llm(self) -> dict[str, Any]:
        """
        Get formatted device list for LLM context.
        
        Returns:
            Dictionary structured for LLM consumption with devices grouped by domain
        """
        devices = await self.get_device_inventory()
        
        # Group by domain
        by_domain: dict[str, list[str]] = {}
        for device in devices:
            domain = device.get("domain", "other")
            friendly_name = device.get("friendly_name", device.get("entity_id", "unknown"))
            
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(friendly_name)
        
        # Sort lists
        for domain in by_domain:
            by_domain[domain] = sorted(by_domain[domain])
        
        return {
            "available_devices": by_domain,
            "total_devices": len(devices),
            "device_domains_available": sorted(by_domain.keys()),
        }
    
    async def close(self) -> None:
        """Cleanup resources."""
        await self.http_client.aclose()
        logger.debug("DeviceValidationService closed")
