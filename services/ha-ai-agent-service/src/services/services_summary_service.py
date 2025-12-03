"""
Available Services Summary Service

Discovers all services by domain and summarizes common parameters for context injection.
Epic AI-19: Story AI19.4
Enhanced: Added full parameter schemas with types, required/optional flags, and constraints
"""

import logging
from typing import Any

from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class ServicesSummaryService:
    """
    Service for generating available services summary.

    Groups services by domain and formats service names with full parameter schemas:
    - Parameter types (string, integer, float, boolean, list, dict)
    - Required vs optional parameters
    - Parameter constraints (min/max, enum values, default values)
    - Target options (entity_id, area_id, device_id)
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize services summary service.

        Args:
            settings: Application settings
            context_builder: Context builder for cache access
        """
        self.settings = settings
        self.context_builder = context_builder
        self.ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        )
        self._cache_key = "services_summary"
        self._cache_ttl = 600  # 10 minutes

    async def get_summary(self) -> str:
        """
        Get enhanced services summary with full parameter schemas.

        Returns:
            Formatted summary with service names and full parameter information including types,
            required/optional flags, constraints, and target options

        Raises:
            Exception: If unable to fetch services
        """
        # Check cache first
        cached = await self.context_builder._get_cached_value(self._cache_key)
        if cached:
            logger.debug("✅ Using cached services summary")
            return cached

        try:
            # Fetch services from Home Assistant
            logger.info("🔧 Fetching services from Home Assistant...")
            services_data = await self.ha_client.get_services()

            if not services_data:
                summary = "No services available"
                await self.context_builder._set_cached_value(
                    self._cache_key, summary, self._cache_ttl
                )
                return summary

            # Format services by domain with enhanced parameter information
            summary_parts = []
            for domain in sorted(services_data.keys()):
                domain_services = services_data[domain]
                service_descriptions = []

                # Extract service names and add full parameter schemas
                for service_name, service_info in domain_services.items():
                    if isinstance(service_info, dict):
                        # Check for fields/parameters
                        fields = service_info.get("fields", {})
                        description = service_info.get("description", "")

                        if fields:
                            # Build full parameter schema
                            param_schema = self._format_full_parameter_schema(service_name, fields, description)
                            service_descriptions.append(param_schema)
                        else:
                            # No parameters, just service name
                            service_desc = service_name
                            if description:
                                service_desc += f" ({description})"
                            service_descriptions.append(service_desc)
                    else:
                        service_descriptions.append(service_name)

                if service_descriptions:
                    # Limit to most common services per domain to avoid overwhelming context
                    # Show all for small domains, limit to 10 for large domains
                    if len(service_descriptions) > 10:
                        # Prioritize common services (turn_on, turn_off, toggle, set_*, etc.)
                        priority_services = [s for s in service_descriptions if any(
                            keyword in s.lower() for keyword in ["turn_on", "turn_off", "toggle", "set_", "open", "close"]
                        )]
                        other_services = [s for s in service_descriptions if s not in priority_services]
                        service_descriptions = priority_services[:8] + other_services[:2]

                    services_str = ", ".join(sorted(service_descriptions))
                    summary_parts.append(f"{domain}: {services_str}")

            summary = "\n".join(summary_parts)

            # Truncate if too long (max ~3000 chars for enhanced version)
            if len(summary) > 3000:
                summary = summary[:3000] + "... (truncated)"

            # Cache the result
            await self.context_builder._set_cached_value(
                self._cache_key, summary, self._cache_ttl
            )

            logger.info(f"✅ Generated enhanced services summary ({len(summary)} chars)")
            return summary

        except Exception as e:
            logger.error(f"❌ Error generating services summary: {e}", exc_info=True)
            # Return fallback
            return "Services unavailable. Please check Home Assistant connection."

    def _format_parameter_hint(self, service_name: str, fields: dict[str, Any]) -> str:
        """
        Format parameter hint for a service (legacy method, kept for compatibility).

        Args:
            service_name: Service name (e.g., "set_brightness")
            fields: Service fields/parameters

        Returns:
            Formatted string with parameter hint
        """
        # Common parameter hints
        if "brightness_pct" in fields or "brightness" in fields:
            return f"{service_name}(brightness_pct: 0-100)"
        elif "rgb_color" in fields:
            return f"{service_name}(rgb_color: [r, g, b])"
        elif "color_temp" in fields:
            return f"{service_name}(color_temp: 153-500)"
        elif "temperature" in fields:
            return f"{service_name}(temperature: number)"
        elif "hvac_mode" in fields:
            return f"{service_name}(hvac_mode: auto|heat|cool|off)"
        else:
            # Just return service name if no special formatting needed
            return service_name

    def _format_full_parameter_schema(self, service_name: str, fields: dict[str, Any], description: str = "") -> str:
        """
        Format full parameter schema for a service with types, required/optional, and constraints.

        Args:
            service_name: Service name (e.g., "set_brightness")
            fields: Service fields/parameters dictionary
            description: Service description

        Returns:
            Formatted string with full parameter schema
        """
        # Check for target fields (entity_id, area_id, device_id)
        has_target = any(key in fields for key in ["entity_id", "area_id", "device_id"])

        # Build parameter list
        required_params = []
        optional_params = []

        for field_name, field_info in fields.items():
            if field_name in ["entity_id", "area_id", "device_id"]:
                # Target fields are handled separately
                continue

            field_type = field_info.get("type", "string")
            field_desc = field_info.get("description", "")
            default = field_info.get("default")
            required = field_info.get("required", False)

            # Build parameter description
            param_desc = f"{field_name}: {field_type}"

            # Add constraints
            if "min" in field_info and "max" in field_info:
                param_desc += f" ({field_info['min']}-{field_info['max']})"
            elif "min" in field_info:
                param_desc += f" (min: {field_info['min']})"
            elif "max" in field_info:
                param_desc += f" (max: {field_info['max']})"

            # Add enum values if available
            if "values" in field_info:
                values = field_info["values"]
                if isinstance(values, list) and len(values) <= 5:
                    param_desc += f" [{', '.join(str(v) for v in values)}]"
                elif isinstance(values, list):
                    param_desc += f" [{len(values)} options]"

            # Add default if available
            if default is not None:
                param_desc += f" (default: {default})"

            # Add description if available and short
            if field_desc and len(field_desc) < 50:
                param_desc += f" - {field_desc}"

            if required:
                required_params.append(param_desc)
            else:
                optional_params.append(param_desc)

        # Build service description
        service_desc = service_name

        # Add target information
        if has_target:
            target_options = []
            if "entity_id" in fields:
                target_options.append("entity_id")
            if "area_id" in fields:
                target_options.append("area_id")
            if "device_id" in fields:
                target_options.append("device_id")
            if target_options:
                service_desc += f" [target: {', '.join(target_options)}]"

        # Add parameters
        if required_params or optional_params:
            param_str_parts = []
            if required_params:
                param_str_parts.append(f"required: {', '.join(required_params[:3])}")  # Limit to 3 required
            if optional_params:
                param_str_parts.append(f"optional: {', '.join(optional_params[:3])}")  # Limit to 3 optional

            if param_str_parts:
                service_desc += f" ({'; '.join(param_str_parts)})"

        # Add service description if available and short
        if description and len(description) < 60:
            service_desc += f" - {description}"

        return service_desc

    async def close(self):
        """Close service resources"""
        await self.ha_client.close()

