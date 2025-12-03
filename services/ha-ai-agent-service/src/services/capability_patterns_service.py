"""
Device Capability Patterns Service

Queries device intelligence for capability examples and formats them for context injection.
Epic AI-19: Story AI19.5
"""

import logging
from collections import defaultdict
from typing import Any

from ..clients.device_intelligence_client import DeviceIntelligenceClient
from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class CapabilityPatternsService:
    """
    Service for generating device capability patterns summary.

    Queries device-intelligence-service for capability examples and formats patterns.
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize capability patterns service.

        Args:
            settings: Application settings
            context_builder: Context builder for cache access
        """
        self.settings = settings
        self.context_builder = context_builder
        self.device_intelligence_client = DeviceIntelligenceClient(
            base_url=settings.device_intelligence_url
        )
        self._cache_key = "capability_patterns"
        self._cache_ttl = 900  # 15 minutes

    async def get_patterns(self) -> str:
        """
        Get capability patterns summary.

        Returns:
            Formatted summary like "WLED lights: effect_list (186 effects), rgb_color, brightness (0-255)"

        Raises:
            Exception: If unable to fetch capabilities
        """
        # Check cache first
        cached = await self.context_builder._get_cached_value(self._cache_key)
        if cached:
            logger.debug("✅ Using cached capability patterns")
            return cached

        try:
            # Fetch sample devices to get capability patterns
            logger.info("🔍 Fetching device capability patterns...")
            devices = await self.device_intelligence_client.get_devices(limit=50)

            if not devices:
                patterns = "No device capability patterns available"
                await self.context_builder._set_cached_value(
                    self._cache_key, patterns, self._cache_ttl
                )
                return patterns

            # Aggregate capabilities by device type/manufacturer
            capability_patterns: dict[str, dict[str, Any]] = defaultdict(lambda: {
                "capabilities": set(),
                "device_types": set()
            })

            # Sample a few devices to get patterns (focus on common types)
            # Reduced to 15 to balance detail vs context size
            sample_devices = devices[:15]  # Sample first 15 devices

            for device in sample_devices:
                device_id = device.get("device_id", "")
                manufacturer = device.get("manufacturer", "unknown")
                model = device.get("model", "")
                device_type = f"{manufacturer} {model}".strip()

                try:
                    capabilities = await self.device_intelligence_client.get_device_capabilities(device_id)
                    if capabilities:
                        # Group by device type pattern
                        key = manufacturer.lower() if manufacturer != "unknown" else "other"
                        for cap in capabilities:
                            cap_name = cap.get("capability_name", "")
                            cap_type = cap.get("capability_type", "")
                            properties = cap.get("properties", {})

                            if cap_name:
                                # Format capability with examples
                                formatted = self._format_capability(cap_name, cap_type, properties)
                                capability_patterns[key]["capabilities"].add(formatted)
                                capability_patterns[key]["device_types"].add(device_type)
                except Exception as e:
                    logger.debug(f"Could not fetch capabilities for {device_id}: {e}")
                    continue

            # Format summary
            summary_parts = []
            for device_key in sorted(capability_patterns.keys()):
                patterns_data = capability_patterns[device_key]
                if patterns_data["capabilities"]:
                    device_types = list(patterns_data["device_types"])[:3]  # Limit to 3 examples
                    device_type_str = ", ".join(device_types) if device_types else device_key
                    capabilities_str = ", ".join(sorted(patterns_data["capabilities"]))
                    summary_parts.append(f"{device_type_str}: {capabilities_str}")

            patterns = "\n".join(summary_parts) if summary_parts else "No capability patterns found"

            # Truncate if too long (max 2000 chars for enhanced version)
            if len(patterns) > 2000:
                patterns = patterns[:2000] + "... (truncated)"

            # Cache the result
            await self.context_builder._set_cached_value(
                self._cache_key, patterns, self._cache_ttl
            )

            logger.info(f"✅ Generated capability patterns ({len(patterns)} chars)")
            return patterns

        except Exception as e:
            logger.error(f"❌ Error generating capability patterns: {e}", exc_info=True)
            # Return fallback
            return "Capability patterns unavailable. Please check device-intelligence-service."

    def _format_capability(self, cap_name: str, cap_type: str, properties: dict[str, Any]) -> str:
        """
        Format capability with full example values, units, and composite details.

        Args:
            cap_name: Capability name
            cap_type: Capability type (numeric, enum, composite, binary)
            properties: Capability properties

        Returns:
            Formatted capability string with full details
        """
        # Format based on type
        if cap_type == "numeric":
            # Extract range with units if available
            unit = properties.get("unit", "")
            if "min" in properties and "max" in properties:
                range_str = f"{properties['min']}-{properties['max']}"
                if unit:
                    range_str += f" {unit}"
                return f"{cap_name} ({range_str})"
            elif "max" in properties:
                range_str = f"0-{properties['max']}"
                if unit:
                    range_str += f" {unit}"
                return f"{cap_name} ({range_str})"
            elif "min" in properties:
                range_str = f"{properties['min']}+"
                if unit:
                    range_str += f" {unit}"
                return f"{cap_name} ({range_str})"
            elif unit:
                return f"{cap_name} ({unit})"
            else:
                return cap_name
        elif cap_type == "enum":
            # Show actual enum values (limit to 8 for readability)
            if "values" in properties and isinstance(properties["values"], list):
                values = properties["values"]
                if len(values) <= 8:
                    # Show all values
                    values_str = ", ".join(str(v) for v in values)
                    return f"{cap_name} [{values_str}]"
                else:
                    # Show first 5 and count
                    values_str = ", ".join(str(v) for v in values[:5])
                    return f"{cap_name} [{values_str}, ... ({len(values)} total)]"
            elif "count" in properties:
                return f"{cap_name} ({properties['count']} options)"
            else:
                return cap_name
        elif cap_type == "composite":
            # Show components if available
            if "components" in properties:
                components = properties["components"]
                if isinstance(components, list) and len(components) <= 5:
                    components_str = ", ".join(str(c) for c in components)
                    return f"{cap_name} (composite: {components_str})"
                elif isinstance(components, list):
                    components_str = ", ".join(str(c) for c in components[:3])
                    return f"{cap_name} (composite: {components_str}, ... {len(components)} total)"
                else:
                    return f"{cap_name} (composite)"
            else:
                return cap_name
        else:
            # Binary or unknown
            return cap_name

    async def close(self):
        """Close service resources"""
        await self.device_intelligence_client.close()

