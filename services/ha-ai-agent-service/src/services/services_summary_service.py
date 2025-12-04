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

            # 2025 Pattern: Focus on critical services with 2025 format
            critical_services = {
                "light": ["turn_on", "turn_off", "toggle"],
                "scene": ["create", "turn_on", "reload"],
                "automation": ["trigger", "toggle", "reload"],
                "script": ["turn_on", "reload"],
            }
            
            summary_parts = []
            
            # Process critical services first with 2025 format
            for domain in sorted(critical_services.keys()):
                if domain not in services_data:
                    logger.debug(f"Domain {domain} not in services_data")
                    continue
                    
                domain_services = services_data[domain]
                if not isinstance(domain_services, dict):
                    logger.warning(f"Domain {domain} services is not a dict: {type(domain_services)}")
                    continue
                    
                service_names = critical_services[domain]
                
                domain_parts = []
                for service_name in service_names:
                    if service_name not in domain_services:
                        logger.debug(f"Service {domain}.{service_name} not found")
                        continue
                        
                    service_info = domain_services[service_name]
                    if isinstance(service_info, dict):
                        formatted = self._format_service_2025(domain, service_name, service_info)
                        if formatted:
                            domain_parts.append(formatted)
                            logger.debug(f"Formatted {domain}.{service_name}")
                    else:
                        logger.warning(f"Service {domain}.{service_name} info is not a dict: {type(service_info)}")
                
                if domain_parts:
                    summary_parts.append("\n".join(domain_parts))
                    logger.debug(f"Added {len(domain_parts)} services for domain {domain}")
            
            # Add other domains (limit to top 10 most common)
            other_domains = [d for d in sorted(services_data.keys()) if d not in critical_services]
            for domain in other_domains[:10]:
                domain_services = services_data[domain]
                if isinstance(domain_services, dict):
                    service_names = list(domain_services.keys())[:5]  # Limit to 5 services per domain
                    
                    if service_names:
                        services_str = ", ".join(service_names)
                        summary_parts.append(f"{domain}: {services_str}")

            summary = "\n".join(summary_parts)
            
            if not summary:
                logger.warning("⚠️ Services summary is empty after formatting. Services data keys: " + 
                             str(list(services_data.keys())[:10] if isinstance(services_data, dict) else 'N/A'))
                # Use fallback if formatting produced empty result
                return await self._get_fallback_services_summary()

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
        
        # Format parameters
        param_parts = []
        for param_name, param_info in fields.items():
            if param_name == "target":
                continue
                
            if not isinstance(param_info, dict):
                continue
                
            param_type = param_info.get("type", "unknown")
            required = param_info.get("required", False)
            default = param_info.get("default")
            param_desc = param_info.get("description", "")
            
            # Get selector info for better type detection
            selector = param_info.get("selector", {})
            if isinstance(selector, dict):
                selector_type = selector.get("type", "")
                if selector_type == "color_rgb":
                    param_type = "list[int] (0-255 each)"
                elif selector_type == "number":
                    min_val = selector.get("min", "")
                    max_val = selector.get("max", "")
                    if min_val is not None and max_val is not None:
                        param_type = f"int ({min_val}-{max_val})"
                    elif min_val is not None:
                        param_type = f"int (min: {min_val})"
                    elif max_val is not None:
                        param_type = f"int (max: {max_val})"
                elif selector_type == "select":
                    # Extract enum values from select selector
                    options = selector.get("options", [])
                    if isinstance(options, list) and options:
                        if len(options) <= 5:
                            options_str = ", ".join(str(opt) for opt in options)
                            param_type = f"string (enum: {options_str})"
                        else:
                            options_preview = ", ".join(str(opt) for opt in options[:3])
                            param_type = f"string (enum: {options_preview}, ... {len(options)} total)"
                    elif isinstance(options, dict):
                        # Options might be a dict with value/label pairs
                        option_values = list(options.keys())[:5] if isinstance(options, dict) else []
                        if option_values:
                            options_str = ", ".join(str(opt) for opt in option_values)
                            param_type = f"string (enum: {options_str})"
                elif selector_type == "text":
                    # Text selector - keep as string
                    pass
            
            param_str = f"      {param_name}: {param_type}"
            if required:
                param_str += " (required)"
            if default is not None:
                param_str += f" (default: {default})"
            if param_desc and len(param_desc) < 50:
                param_str += f" - {param_desc}"
            
            # Special handling for effect parameter - try to get enum values from selector
            if param_name == "effect" and isinstance(selector, dict):
                options = selector.get("options", [])
                if isinstance(options, list) and len(options) > 5:
                    # For effect, show more examples if available
                    effect_preview = ", ".join(str(opt) for opt in options[:8])
                    param_str += f" [examples: {effect_preview}, ... {len(options)} total]"
            
            param_parts.append(param_str)
        
        # Build service format
        service_format = f"{domain}.{service}:"
        if target_options:
            service_format += f"\n    target: {', '.join(target_options)}"
        else:
            service_format += "\n    target: N/A"
        
        service_format += "\n    data:"
        if param_parts:
            service_format += "\n" + "\n".join(param_parts)
        else:
            service_format += "\n      (no additional parameters)"
        
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

