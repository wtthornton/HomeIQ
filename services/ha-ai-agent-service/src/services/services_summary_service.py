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
        self._cache_ttl = 900  # 15 minutes (P1: Increased TTL - services change occasionally)

    async def get_summary(self, skip_truncation: bool = False) -> str:
        """
        Get enhanced services summary with full parameter schemas.

        Args:
            skip_truncation: If True, skip truncation (for debug display)

        Returns:
            Formatted summary with service names and full parameter information including types,
            required/optional flags, constraints, and target options

        Raises:
            Exception: If unable to fetch services
        """
        # Check cache first (only if not skipping truncation, as cache may be truncated)
        if not skip_truncation:
            cached = await self.context_builder._get_cached_value(self._cache_key)
            if cached:
                logger.debug("✅ Using cached services summary")
                return cached

        try:
            # Fetch services from Home Assistant
            logger.info("🔧 Fetching services from Home Assistant...")
            services_data = await self.ha_client.get_services()

            # Check if services_data is empty or None
            if not services_data or (isinstance(services_data, dict) and len(services_data) == 0):
                logger.warning("Services data is empty or None, using fallback")
                return await self._get_fallback_services_summary()

            # Handle different response formats from Home Assistant API
            # Format 1: Dict format {"light": {"turn_on": {...}, "turn_off": {...}}, ...}
            # Format 2: List format [{"domain": "light", "service": "turn_on", ...}, ...]
            # Format 3: Empty dict or unexpected format
            
            logger.debug(f"Services data type: {type(services_data)}, keys: {list(services_data.keys())[:10] if isinstance(services_data, dict) else 'N/A'}")
            
            if isinstance(services_data, list):
                # Convert list format to dict format
                logger.debug("Converting services list format to dict format")
                services_dict: dict[str, dict[str, Any]] = {}
                for service_item in services_data:
                    if isinstance(service_item, dict):
                        domain = service_item.get("domain", "unknown")
                        service_name = service_item.get("service", "")
                        if domain and service_name:
                            if domain not in services_dict:
                                services_dict[domain] = {}
                            # Extract service info (fields, description, etc.)
                            service_info = {
                                "fields": service_item.get("fields", {}),
                                "description": service_item.get("description", "")
                            }
                            services_dict[domain][service_name] = service_info
                services_data = services_dict
                logger.debug(f"Converted to dict format: {len(services_dict)} domains")
            elif isinstance(services_data, dict):
                # Check if it's the expected format or empty
                if not services_data:
                    logger.warning("Services data is empty dict")
                    # Try to provide fallback with known service patterns
                    return await self._get_fallback_services_summary()
                else:
                    # Check if it's nested format {"light": {"turn_on": {...}}}
                    # or flat format with domain keys
                    first_key = list(services_data.keys())[0] if services_data else None
                    if first_key and isinstance(services_data[first_key], dict):
                        # Expected format - services grouped by domain
                        logger.debug(f"Services in expected format: {len(services_data)} domains")
                    else:
                        logger.warning(f"Unexpected services dict structure. First key: {first_key}, type: {type(services_data.get(first_key)) if first_key else 'N/A'}")
            else:
                # Unexpected format
                logger.warning(f"Unexpected services data format: {type(services_data)}")
                return await self._get_fallback_services_summary()

            # Process ALL domains and ALL services
            summary_parts = []
            
            # Count total services for logging
            total_domains = len(services_data)
            total_services = sum(len(svcs) for svcs in services_data.values() if isinstance(svcs, dict))
            logger.info(f"📊 Processing {total_domains} domains with {total_services} total services")
            
            # Process all domains with all their services
            for domain in sorted(services_data.keys()):
                domain_services = services_data[domain]
                if not isinstance(domain_services, dict):
                    logger.warning(f"Domain {domain} services is not a dict: {type(domain_services)}")
                    continue
                
                # Format all services in this domain
                domain_parts = []
                service_count = 0
                
                for service_name in sorted(domain_services.keys()):
                    service_info = domain_services[service_name]
                    if isinstance(service_info, dict):
                        formatted = self._format_service_2025(domain, service_name, service_info)
                        if formatted:
                            domain_parts.append(formatted)
                            service_count += 1
                    else:
                        logger.debug(f"Service {domain}.{service_name} info is not a dict: {type(service_info)}")
                
                if domain_parts:
                    # Add domain header with service count
                    summary_parts.append(f"{domain} ({service_count} services):")
                    summary_parts.append("\n".join(domain_parts))
                    logger.debug(f"✅ Added {service_count} services for domain {domain}")

            summary = "\n".join(summary_parts)
            
            if not summary:
                logger.warning("⚠️ Services summary is empty after formatting. Services data keys: " + 
                             str(list(services_data.keys())[:10] if isinstance(services_data, dict) else 'N/A'))
                # Use fallback if formatting produced empty result
                return await self._get_fallback_services_summary()

            # Truncate if too long (increased limit to accommodate all services)
            # Skip truncation for debug display
            max_length = 8000 if skip_truncation else 6000  # Increased from 1500 to 6000 for all services
            original_length = len(summary)
            if not skip_truncation and len(summary) > max_length:
                truncation_msg = "\n... (truncated - too many services)"
                summary = summary[:max_length] + truncation_msg
                logger.warning(f"⚠️ Services summary truncated at {max_length} chars (original was {original_length} chars)")

            # Cache the result (only if not skipping truncation)
            if not skip_truncation:
                await self.context_builder._set_cached_value(
                    self._cache_key, summary, self._cache_ttl
                )

            logger.info(
                f"✅ Generated services summary: {total_domains} domains, "
                f"{total_services} total services ({len(summary)} chars)"
            )
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

    def _format_service_2025(self, domain: str, service: str, info: dict) -> str:
        """
        Format service with 2025 Home Assistant schema format.
        
        Args:
            domain: Service domain (e.g., "light")
            service: Service name (e.g., "turn_on")
            info: Service info dict with fields, description, etc.
            
        Returns:
            Formatted service string with 2025 format
        """
        fields = info.get("fields", {})
        description = info.get("description", "")
        
        # Extract target options (2025 pattern)
        target_fields = fields.get("target", {})
        target_selector = target_fields.get("selector", {}) if isinstance(target_fields, dict) else {}
        target_options = []
        
        # Check for entity_id, area_id, device_id in target selector
        if isinstance(target_selector, dict):
            if "entity" in target_selector.get("entity", {}):
                target_options.append("entity_id")
            if "area" in target_selector.get("area", {}):
                target_options.append("area_id")
            if "device" in target_selector.get("device", {}):
                target_options.append("device_id")
        
        # Fallback: check if target fields exist directly
        if not target_options:
            if "entity_id" in fields:
                target_options.append("entity_id")
            if "area_id" in fields:
                target_options.append("area_id")
            if "device_id" in fields:
                target_options.append("device_id")
        
        # Collect parameter names (optimized: just names for token efficiency)
        param_names = []
        for param_name, param_info in fields.items():
            if param_name == "target":
                continue
                
            if not isinstance(param_info, dict):
                continue
            
            # Add parameter name (limit to 8 params for token efficiency)
            if len(param_names) < 8:
                param_names.append(param_name)
        
        # Build service format (optimized: compact format for token efficiency)
        # Format: domain.service(target: options, data: param1, param2, ...)
        target_str = "|".join(target_options) if target_options else "N/A"
        param_str = ", ".join(param_names) if param_names else "none"
        
        service_format = f"{domain}.{service}(target: {target_str}, data: {param_str})"
        
        return service_format

    async def _get_fallback_services_summary(self) -> str:
        """
        Fallback: Provide known service patterns when API fails.
        
        Returns:
            Formatted services summary with common patterns
        """
        logger.info("Using fallback services summary with known patterns")
        
        fallback_services = """light.turn_on:
    target: entity_id, area_id, device_id
    data:
      rgb_color: list[int] (0-255 each) - RGB color values
      brightness: int (0-255) - Brightness level
      effect: string - Effect name
      transition: float - Transition duration in seconds

light.turn_off:
    target: entity_id, area_id, device_id
    data:
      transition: float - Transition duration in seconds

scene.create:
    target: N/A
    data:
      scene_id: string (required) - Unique scene identifier
      snapshot_entities: list[string] (required) - Entity IDs to snapshot

scene.turn_on:
    target:
      entity_id: string - Scene entity ID

automation.trigger:
    target:
      entity_id: string - Automation entity ID"""
        
        await self.context_builder._set_cached_value(
            self._cache_key, fallback_services, self._cache_ttl
        )
        
        return fallback_services

    async def close(self):
        """Close service resources"""
        await self.ha_client.close()

