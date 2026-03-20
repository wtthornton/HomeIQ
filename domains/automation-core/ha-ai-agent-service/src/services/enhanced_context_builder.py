"""
Enhanced Context Builder Service

Provides area-focused entity context for automation creation.
Addresses gaps in standard context that prevent accurate YAML generation.

Key Improvements:
1. Entity IDs grouped by area (for target.area_id and entity resolution)
2. Binary sensors (motion/presence) explicitly listed
3. Trigger platform documentation
4. Existing automations (for duplicate detection)
5. Area-filtered entity lists
"""

import logging
from collections import defaultdict

from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..config.entity_blacklist import EntityBlacklist

logger = logging.getLogger(__name__)


class EnhancedContextBuilder:
    """
    Builds enhanced context with area-focused entity information.

    Supplements the standard context with:
    - Area-to-entity mappings (entity_ids by area)
    - Binary sensors (motion, presence, occupancy)
    - Existing automations (for duplicate detection)
    - Trigger platform reference

    Epic 93: Security-sensitive entities (locks, alarms) are filtered
    from context so the LLM cannot reference them in generated YAML.
    """

    def __init__(self, settings: Settings, blacklist: EntityBlacklist | None = None):
        """Initialize enhanced context builder."""
        self.settings = settings
        self.blacklist = blacklist or EntityBlacklist()
        self.ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token.get_secret_value()
        )
        self.data_api_client = DataAPIClient(base_url=settings.data_api_url, api_key=settings.data_api_key.get_secret_value() if settings.data_api_key else None)

    async def close(self):
        """Close client connections."""
        await self.ha_client.close()
        await self.data_api_client.close()

    async def build_area_entity_context(self, area_ids: list[str] | None = None) -> str:
        """
        Build entity context grouped by area.

        Args:
            area_ids: Optional list of area IDs to filter. If None, includes all areas.

        Returns:
            Formatted context string with entities grouped by area
        """
        try:
            # Fetch entities
            entities = await self.data_api_client.fetch_entities(limit=10000)
            if not entities:
                return "ENTITY_INVENTORY: No entities found"

            # Fetch device registry for area resolution
            devices = await self.ha_client.get_device_registry()
            device_area_map = {
                d.get("id"): d.get("area_id")
                for d in devices if d.get("id") and d.get("area_id")
            }

            # Fetch areas for friendly names
            areas = await self.ha_client.get_area_registry()
            area_name_map = {
                a.get("area_id"): a.get("name", a.get("area_id", ""))
                for a in areas if a.get("area_id")
            }

            # Group entities by area and domain
            area_domain_entities: dict[str, dict[str, list[dict]]] = defaultdict(
                lambda: defaultdict(list)
            )
            filtered_count = 0

            for entity in entities:
                entity_id = entity.get("entity_id", "")
                domain = entity.get("domain", "unknown")

                # Epic 93: Skip blocked entities (locks, alarms, etc.)
                if self.blacklist.is_blocked(entity_id):
                    filtered_count += 1
                    continue

                # Resolve area_id (from entity or device)
                area_id = entity.get("area_id")
                if not area_id:
                    device_id = entity.get("device_id")
                    if device_id:
                        area_id = device_area_map.get(device_id)

                area_id = area_id or "unassigned"

                # Filter by area_ids if specified
                if area_ids and area_id not in area_ids:
                    continue

                # Get friendly name and state
                friendly_name = entity.get("friendly_name") or entity.get("name") or entity_id
                state = entity.get("state", "unknown")

                # Get relevant attributes
                attributes = entity.get("attributes", {})

                entity_info = {
                    "entity_id": entity_id,
                    "friendly_name": friendly_name,
                    "state": state,
                    "device_id": entity.get("device_id"),
                }

                # Add domain-specific attributes
                if domain == "light":
                    if "effect_list" in attributes:
                        entity_info["effect_list"] = attributes["effect_list"]
                    if "supported_color_modes" in attributes:
                        entity_info["color_modes"] = attributes["supported_color_modes"]
                    if "brightness" in attributes:
                        entity_info["brightness"] = attributes["brightness"]

                elif domain == "binary_sensor":
                    device_class = attributes.get("device_class", "")
                    entity_info["device_class"] = device_class

                area_domain_entities[area_id][domain].append(entity_info)

            # Format output
            parts = ["ENTITIES BY AREA:"]

            for area_id in sorted(area_domain_entities.keys()):
                area_name = area_name_map.get(area_id, area_id.replace("_", " ").title())
                domains = area_domain_entities[area_id]

                parts.append(f"\n{area_name} (area_id: {area_id}):")

                # Prioritize critical domains for automation
                priority_domains = ["light", "binary_sensor", "switch", "fan", "media_player", "scene", "person", "sensor", "climate", "cover"]
                sorted_domains = sorted(
                    domains.keys(),
                    key=lambda d: (priority_domains.index(d) if d in priority_domains else 99, d)
                )

                for domain in sorted_domains:
                    domain_entities = domains[domain]
                    # Scenes are verbose — limit to 5 per area; other domains get 20
                    max_per_domain = 5 if domain == "scene" else 20
                    parts.append(f"  {domain} ({len(domain_entities)}):")

                    for entity in domain_entities[:max_per_domain]:  # Limit per domain
                        entity_id = entity["entity_id"]
                        friendly_name = entity["friendly_name"]
                        state = entity["state"]

                        line = f"    - {entity_id}"
                        if friendly_name and friendly_name != entity_id:
                            line += f' "{friendly_name}"'
                        line += f" (state: {state})"

                        # Epic 93: Annotate warn_domain entities
                        if self.blacklist.is_warned(entity_id):
                            line += " [⚠️ SAFETY WARNING: review before automating]"

                        # Add device_class for binary_sensor
                        if domain == "binary_sensor" and entity.get("device_class"):
                            line += f" [device_class: {entity['device_class']}]"

                        # Add effects for lights
                        if domain == "light" and entity.get("effect_list"):
                            effects = entity["effect_list"][:5]  # Top 5 effects
                            line += f" [effects: {', '.join(effects)}...]"

                        parts.append(line)

                    if len(domain_entities) > max_per_domain:
                        parts.append(f"    ... and {len(domain_entities) - max_per_domain} more")

            # Epic 93: Append filtered-entity notice
            if filtered_count > 0:
                parts.append(
                    f"\n[FILTERED] {filtered_count} security-sensitive entities "
                    "filtered (locks, alarms). Use HomeIQ Admin to manage these devices."
                )

            return "\n".join(parts)

        except Exception as e:
            logger.error(f"Error building area entity context: {e}", exc_info=True)
            return "ENTITY_INVENTORY: Unavailable"

    async def build_binary_sensor_context(self) -> str:
        """
        Build context specifically for binary sensors (motion, presence, occupancy).

        Critical for automation triggers based on presence/motion.
        """
        try:
            entities = await self.data_api_client.fetch_entities(limit=10000)
            if not entities:
                return "BINARY_SENSORS: No sensors found"

            # Fetch device registry for area resolution
            devices = await self.ha_client.get_device_registry()
            device_area_map = {
                d.get("id"): d.get("area_id")
                for d in devices if d.get("id") and d.get("area_id")
            }

            # Fetch areas for friendly names
            areas = await self.ha_client.get_area_registry()
            area_name_map = {
                a.get("area_id"): a.get("name", a.get("area_id", ""))
                for a in areas if a.get("area_id")
            }

            # Fetch live states from HA for accurate state reporting
            state_map: dict[str, str] = {}
            try:
                states = await self.ha_client.get_states()
                state_map = {
                    s.get("entity_id"): s.get("state", "unknown")
                    for s in states
                    if s.get("entity_id", "").startswith("binary_sensor.")
                }
            except Exception as e:
                logger.warning(f"Could not fetch live states for binary sensors: {e}")

            # Filter and group binary sensors
            sensor_by_area: dict[str, list[dict]] = defaultdict(list)

            for entity in entities:
                if entity.get("domain") != "binary_sensor":
                    continue

                entity_id = entity.get("entity_id", "")

                # Epic 93: Skip blocked binary sensors (defensive)
                if self.blacklist.is_blocked(entity_id):
                    continue
                attributes = entity.get("attributes", {}) or {}
                # Check device_class at top level (data-api format) AND in attributes (HA state format)
                device_class = entity.get("device_class") or attributes.get("device_class", "")

                # Only include motion/presence/occupancy sensors
                if device_class not in ["motion", "presence", "occupancy", "door", "window"] and not any(kw in entity_id.lower() for kw in ["motion", "presence", "occupancy", "fp2", "fp300"]):
                    continue

                # Resolve area: entity → device → name-based fallback
                area_id = entity.get("area_id")
                if not area_id:
                    device_id = entity.get("device_id")
                    if device_id:
                        area_id = device_area_map.get(device_id)
                if not area_id:
                    # Fallback: infer area from entity_id if it contains a known area name
                    entity_name = entity_id.split(".", 1)[-1] if "." in entity_id else entity_id
                    for known_area_id in area_name_map:
                        if known_area_id in entity_name.lower():
                            area_id = known_area_id
                            break
                area_id = area_id or "unassigned"

                # Use live state from HA (fallback to data-api state)
                live_state = state_map.get(entity_id) or entity.get("state") or "unknown"

                # Skip unavailable/unknown sensors — they can't trigger automations
                if live_state in ("unavailable", "unknown"):
                    continue

                sensor_by_area[area_id].append({
                    "entity_id": entity_id,
                    "friendly_name": entity.get("friendly_name") or entity.get("name") or entity_id,
                    "device_class": device_class or "motion",
                    "state": live_state,
                })

            # Format output with explicit per-area instructions
            parts = ["MOTION/PRESENCE SENSORS:"]
            parts.append("(MANDATORY: Use ALL sensors listed for each area in trigger entity_id list)")
            parts.append("")

            for area_id in sorted(sensor_by_area.keys()):
                if area_id == "unassigned":
                    continue  # Show unassigned at the end
                area_name = area_name_map.get(area_id, area_id.replace("_", " ").title())
                sensors = sensor_by_area[area_id]

                parts.append(f"{area_name} (area_id: {area_id}) — use ALL {len(sensors)} sensors:")
                for sensor in sensors:
                    parts.append(
                        f"  - {sensor['entity_id']} "
                        f"[{sensor['device_class']}] "
                        f"(state: {sensor['state']})"
                    )
                parts.append("")

            # Show unassigned last
            if "unassigned" in sensor_by_area:
                parts.append("Unassigned (no area):")
                for sensor in sensor_by_area["unassigned"]:
                    parts.append(
                        f"  - {sensor['entity_id']} "
                        f"[{sensor['device_class']}] "
                        f"(state: {sensor['state']})"
                    )
                parts.append("")

            if not sensor_by_area:
                parts.append("No motion/presence sensors found.")

            return "\n".join(parts)

        except Exception as e:
            logger.error(f"Error building binary sensor context: {e}", exc_info=True)
            return "BINARY_SENSORS: Unavailable"

    async def build_existing_automations_context(self) -> str:
        """
        Build context for existing automations (for duplicate detection).

        Only includes active automations (state == "on") to avoid confusion
        from disabled or unavailable automations.
        """
        try:
            # Fetch automation entities from Data API (for metadata like friendly_name)
            entities = await self.data_api_client.fetch_entities(limit=10000)
            automations = [
                e for e in entities
                if e.get("domain") == "automation"
            ]

            if not automations:
                return "EXISTING_AUTOMATIONS: None found"

            # Fetch actual states from Home Assistant
            try:
                states = await self.ha_client.get_states()
                # Create state map: entity_id -> state dict
                state_map = {
                    state.get("entity_id"): state.get("state", "unknown")
                    for state in states
                    if state.get("entity_id", "").startswith("automation.")
                }
            except Exception as e:
                logger.warning(f"Could not fetch states from Home Assistant: {e}")
                state_map = {}

            # Filter to only active automations and get actual state
            active_automations = []
            for auto in automations:
                entity_id = auto.get("entity_id", "")
                # Get actual state from Home Assistant (not from entity data)
                actual_state = state_map.get(entity_id, "unknown")

                # Only include automations that are active (state == "on")
                if actual_state == "on":
                    friendly_name = auto.get("friendly_name") or auto.get("name") or entity_id
                    active_automations.append({
                        "entity_id": entity_id,
                        "friendly_name": friendly_name,
                        "state": actual_state
                    })

            if not active_automations:
                return "EXISTING_AUTOMATIONS: No active automations found"

            parts = ["EXISTING_AUTOMATIONS:"]
            parts.append("(Check before creating to avoid duplicates)")
            parts.append("(Only active automations are shown)")
            parts.append("")

            for auto in active_automations[:30]:  # Limit to 30
                entity_id = auto["entity_id"]
                friendly_name = auto["friendly_name"]
                state = auto["state"]

                parts.append(f"  - {entity_id}: \"{friendly_name}\" (state: {state})")

            if len(active_automations) > 30:
                parts.append(f"  ... and {len(active_automations) - 30} more active automations")

            return "\n".join(parts)

        except Exception as e:
            logger.error(f"Error building automations context: {e}", exc_info=True)
            return "EXISTING_AUTOMATIONS: Unavailable"

    def build_trigger_platforms_reference(self) -> str:
        """
        Build quick reference for common trigger platforms.
        """
        return """TRIGGER PLATFORMS REFERENCE:
(Common triggers for automations)

State Change (motion/presence — ALWAYS use ALL sensors in the area):
  - platform: state
    entity_id:
      - binary_sensor.office_motion
      - binary_sensor.office_motion_desk
      - binary_sensor.office_presence
    to: "on"  # Any sensor detecting motion triggers

State Change with Delay (leave detection — ALL sensors must be off):
  - platform: state
    entity_id:
      - binary_sensor.office_motion
      - binary_sensor.office_motion_desk
      - binary_sensor.office_presence
    to: "off"
    for: "00:05:00"  # All sensors off for 5 minutes

Time-based:
  - platform: time
    at: "07:00:00"
  - platform: time_pattern
    minutes: "/15"  # Every 15 minutes

Sun-based:
  - platform: sun
    event: sunset
    offset: "-00:30:00"  # 30 min before sunset
"""

    async def build_enhanced_context(
        self,
        user_prompt: str | None = None,
        area_ids: list[str] | None = None
    ) -> str:
        """
        Build complete enhanced context.

        Args:
            user_prompt: Optional user prompt to extract relevant areas
            area_ids: Optional explicit area filter

        Returns:
            Complete enhanced context string
        """
        # Auto-detect areas from user prompt if not specified
        if user_prompt and not area_ids:
            area_ids = self._extract_areas_from_prompt(user_prompt)

        parts = []

        # Add area-filtered entity inventory
        entity_context = await self.build_area_entity_context(area_ids)
        parts.append(entity_context)

        # Add binary sensors (critical for motion/presence)
        sensor_context = await self.build_binary_sensor_context()
        parts.append(sensor_context)

        # Add existing automations (for duplicate detection)
        automation_context = await self.build_existing_automations_context()
        parts.append(automation_context)

        # Add trigger platforms reference
        trigger_ref = self.build_trigger_platforms_reference()
        parts.append(trigger_ref)

        return "\n\n---\n\n".join(parts)

    def _extract_areas_from_prompt(self, user_prompt: str) -> list[str] | None:
        """
        Extract area IDs from user prompt.

        Args:
            user_prompt: User's natural language prompt

        Returns:
            List of area IDs mentioned, or None if none found
        """
        prompt_lower = user_prompt.lower()

        # Common area name patterns
        area_patterns = {
            "office": "office",
            "living room": "living_room",
            "bedroom": "master_bedroom",
            "master bedroom": "master_bedroom",
            "kitchen": "kitchen",
            "garage": "garage",
            "hallway": "hallway",
            "bathroom": "bathroom",
            "backyard": "backyard",
            "patio": "patio",
            "porch": "porch",
            "bar": "bar",
            "dining": "dinning_room",
            "dinning": "dinning_room",
            "laundry": "laundry_room",
            "stairs": "stairs",
        }

        found_areas = []
        for pattern, area_id in area_patterns.items():
            if pattern in prompt_lower:
                found_areas.append(area_id)

        return found_areas if found_areas else None
