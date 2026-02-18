"""
Intent Planner Service

Hybrid Flow Implementation: Converts user intent to structured plan (template_id + parameters)
LLM outputs structured plan, NEVER YAML directly.
"""

import json
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..clients.openai_client import OpenAIClient
from ..database.models import Plan
from ..templates.template_library import TemplateLibrary

logger = logging.getLogger(__name__)


class IntentPlanner:
    """
    Service for planning automations from user intent.

    Converts natural language requests into structured plans (template_id + parameters).
    LLM selects appropriate template and fills in parameters.
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        template_library: TemplateLibrary,
        data_api_client: DataAPIClient | None = None,
    ):
        """
        Initialize intent planner.

        Args:
            openai_client: OpenAI client for LLM calls
            template_library: Template library for template selection
            data_api_client: Optional Data API client for context
        """
        self.openai_client = openai_client
        self.template_library = template_library
        self.data_api_client = data_api_client

    async def create_plan(
        self,
        user_text: str,
        conversation_id: str | None = None,
        context: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Create automation plan from user intent.

        Args:
            user_text: User's natural language request
            conversation_id: Optional conversation ID for tracking
            context: Optional context (selected devices, room, timezone, etc.)
            db: Optional database session for storing plan

        Returns:
            Plan dictionary with plan_id, template_id, parameters, confidence, etc.
        """
        # Get available templates for LLM selection
        available_templates = self.template_library.list_templates()

        # Build prompt for template selection
        template_descriptions = []
        for template_info in available_templates:
            template = self.template_library.get_template(
                template_info["template_id"], template_info["version"]
            )
            if template:
                template_descriptions.append(
                    {
                        "template_id": template.template_id,
                        "version": template.version,
                        "description": template.description,
                        "required_capabilities": template.required_capabilities.model_dump(),
                        "parameter_schema": {
                            param_name: {
                                "type": param.type.value,
                                "required": param.required,
                                "description": param.description,
                                "enum": param.enum,
                                "default": param.default,
                            }
                            for param_name, param in template.parameter_schema.items()
                        },
                    }
                )

        # Pre-filter templates that can't work in the target area
        template_descriptions = await self._filter_templates_by_capabilities(
            template_descriptions, context
        )

        # Build entity summary for hardware-aware selection
        entity_summary = await self._build_entity_summary()

        # Build system prompt for template selection
        system_prompt = f"""You are an automation planning assistant. Your job is to select the best template and fill in parameters based on user requests.

Available Templates:
{json.dumps(template_descriptions, indent=2)}

Rules:
1. Select the template_id that best matches the user's intent
2. Fill in ALL parameters (both required and optional) based on user text and context
3. Set confidence score (0.0-1.0) based on how well the template matches
4. If clarification is needed, add questions to clarifications_needed array
5. NEVER output YAML - only structured plan with template_id and parameters
6. Set safety_class based on devices involved (low/medium/high/critical)

Parameter Filling Rules:
- ALWAYS provide a value for every parameter defined in the template schema
- NEVER return null for any parameter — use the template's default value or a sensible fallback
- For target_entity: use "all" when the user says "all lights", "everything", or does not specify a specific entity
- For target_area: use the area/room name from the user's request (e.g., "office")
- For time_window: default to {{"after": "06:00:00", "before": "23:00:00"}} if not specified
- For action_data: use {{}} (empty object) if no extra data is needed
- For brightness_pct: default to 100 if not specified
- For color_temp: omit from parameters if user does not mention color temperature

Template Selection for Scheduled Actions:
- For fixed-time requests ("at midnight", "at 7pm", "every day at 9am") -> use scheduled_task_at
- For interval requests ("every 15 minutes", "every hour") -> use scheduled_task_interval

Output Format (JSON):
{{
  "template_id": "time_based_light_on",
  "template_version": 1,
  "parameters": {{
    "target_area": "office",
    "time": "19:00:00",
    "brightness_pct": 100
  }},
  "confidence": 0.95,
  "clarifications_needed": [],
  "safety_class": "low",
  "explanation": "User wants office lights on at 7pm. Using time_based_light_on for area-based time triggers."
}}

Examples:

Example 1 — Fixed time schedule:
User: "turn off all lights at midnight"
Plan:
{{
  "template_id": "scheduled_task_at",
  "template_version": 1,
  "parameters": {{
    "schedule_pattern": "00:00:00",
    "action_service": "light.turn_off",
    "target_entity": "all",
    "action_data": {{}}
  }},
  "confidence": 0.95,
  "clarifications_needed": [],
  "safety_class": "low",
  "explanation": "User wants all lights turned off at midnight. Using scheduled_task_at for fixed-time trigger."
}}

Example 2 — Time-based light control:
User: "turn on office lights at 7pm"
Plan:
{{
  "template_id": "time_based_light_on",
  "template_version": 1,
  "parameters": {{
    "target_area": "office",
    "time": "19:00:00",
    "brightness_pct": 100
  }},
  "confidence": 0.95,
  "clarifications_needed": [],
  "safety_class": "low",
  "explanation": "User wants office lights on at 7pm. Using time_based_light_on for area-based time triggers."
}}

Example 3 — Ambiguous request with clarification:
User: "make it cooler"
Plan:
{{
  "template_id": "temperature_control",
  "template_version": 1,
  "parameters": {{
    "sensor_entity": "sensor.living_room_temperature",
    "target_temperature": 20.0,
    "hvac_entity": "climate.living_room",
    "hvac_mode": "cool"
  }},
  "confidence": 0.6,
  "clarifications_needed": [
    {{"question": "Which room should I adjust the temperature in?"}},
    {{"question": "What temperature would you like?"}}
  ],
  "safety_class": "medium",
  "explanation": "User wants cooling but didn't specify room or target temp. Providing defaults with clarification requests."
}}"""

        # Append entity summary for hardware-aware template selection
        if entity_summary:
            system_prompt += f"""

{entity_summary}

IMPORTANT: When selecting a template, verify the target area has the required sensors/devices.
- room_entry_light_on requires a motion or presence sensor in the area. If the area has NO motion/presence sensors, use time_based_light_on or scene_activation instead.
- motion_dim_off requires a motion sensor in the area.
- temperature_control requires a temperature sensor and climate device in the area."""

        # Inject sports / team tracker sensor context for entity resolution
        sports_context = await self._build_sports_entity_context(user_text)
        if sports_context:
            system_prompt += f"\n\n{sports_context}"

        # Build user prompt with context
        user_prompt = f"User request: {user_text}"
        if context:
            user_prompt += f"\n\nContext: {json.dumps(context, indent=2)}"

        # Call LLM with structured output
        try:
            if not self.openai_client.client:
                raise ValueError("OpenAI client not initialized")

            plan_kwargs = {
                "model": self.openai_client.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            }
            if self.openai_client.supports_temperature:
                plan_kwargs["temperature"] = 0.3
            response = await self.openai_client.client.chat.completions.create(**plan_kwargs)

            plan_data = json.loads(response.choices[0].message.content)

            # Validate template exists
            template = self.template_library.get_template(
                plan_data["template_id"], plan_data.get("template_version")
            )
            if not template:
                raise ValueError(f"Template {plan_data['template_id']} not found")

            # Generate plan_id
            plan_id = f"p_{uuid.uuid4().hex[:8]}"

            # Create plan object
            plan = Plan(
                plan_id=plan_id,
                conversation_id=conversation_id,
                template_id=plan_data["template_id"],
                template_version=plan_data.get("template_version", 1),
                parameters=plan_data["parameters"],
                confidence=plan_data.get("confidence", 0.5),
                clarifications_needed=plan_data.get("clarifications_needed", []),
                safety_class=plan_data.get("safety_class", "low"),
                explanation=plan_data.get("explanation"),
            )

            # Store in database if session provided
            if db:
                db.add(plan)
                await db.commit()
                await db.refresh(plan)

            logger.info(
                f"Created plan {plan_id}: template={plan_data['template_id']}, "
                f"confidence={plan_data.get('confidence', 0.0):.2f}"
            )

            return {
                "plan_id": plan_id,
                "intent_type": "automation_request",
                "template_id": plan_data["template_id"],
                "template_version": plan_data.get("template_version", 1),
                "parameters": plan_data["parameters"],
                "confidence": plan_data.get("confidence", 0.5),
                "clarifications_needed": plan_data.get("clarifications_needed", []),
                "safety_class": plan_data.get("safety_class", "low"),
                "promotion_recommended": plan_data.get("confidence", 0.5) >= 0.8,
                "explanation": plan_data.get("explanation", ""),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"LLM returned invalid JSON: {e}") from e
        except Exception as e:
            logger.error(f"Failed to create plan: {e}", exc_info=True)
            raise RuntimeError(f"Failed to create plan: {e}") from e

    async def _build_entity_summary(self) -> str:
        """Build compact entity summary per area for the LLM prompt.

        Returns a string like:
          Available entities per area:
          - office: light (3), scene (2) -- NO motion/presence sensors
          - living_room: light (5), binary_sensor (1) -- has motion sensor
        """
        if not self.data_api_client:
            return ""

        try:
            areas = await self.data_api_client.fetch_areas()
            if not areas:
                return ""

            lines = ["Available entities per area:"]
            for area in areas:
                area_id = area.get("area_id", "")
                area_name = area.get("name", area_id)

                entities = await self.data_api_client.fetch_entities_in_area(area_id)

                # Count by domain and collect key sensor entity IDs
                domain_counts: dict[str, int] = {}
                motion_ids: list[str] = []
                presence_ids: list[str] = []
                light_ids: list[str] = []
                for entity in entities:
                    entity_id = entity.get("entity_id", "")
                    domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1

                    device_class = entity.get("device_class", "")
                    state = entity.get("state", "")
                    if device_class == "motion":
                        motion_ids.append(entity_id)
                    if device_class in ("presence", "occupancy"):
                        presence_ids.append(entity_id)
                    if domain == "light" and state != "unavailable":
                        light_ids.append(entity_id)

                parts = [f"{d} ({c})" for d, c in sorted(domain_counts.items())]
                sensor_note = ""
                if not motion_ids and not presence_ids:
                    sensor_note = " -- NO motion/presence sensors"
                else:
                    sensor_ids = motion_ids + presence_ids
                    sensor_note = f" -- motion/presence sensors: {', '.join(sensor_ids)}"

                lines.append(f"  - {area_name}: {', '.join(parts)}{sensor_note}")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Failed to build entity summary: {e}")
            return ""

    # Common team name → abbreviation mappings for NHL, NFL, NBA, MLB, MLS
    _TEAM_KEYWORDS: dict[str, list[str]] = {
        # NHL
        "vgk": ["golden knights", "vegas golden knights", "vgk", "knights"],
        "dal": ["dallas stars", "stars"],
        "sea": ["seattle kraken", "kraken"],
        "col": ["colorado avalanche", "avalanche", "avs"],
        "edm": ["edmonton oilers", "oilers"],
        "wpg": ["winnipeg jets", "jets"],
        "min": ["minnesota wild", "wild"],
        "van": ["vancouver canucks", "canucks"],
        "cgy": ["calgary flames", "flames"],
        "lak": ["los angeles kings", "la kings", "kings"],
        "ana": ["anaheim ducks", "ducks"],
        "sjs": ["san jose sharks", "sharks"],
        # NFL
        "kc": ["kansas city chiefs", "chiefs"],
        "lv": ["las vegas raiders", "raiders"],
        "ne": ["new england patriots", "patriots", "pats"],
        "phi": ["philadelphia eagles", "eagles"],
        "buf": ["buffalo bills", "bills"],
        "sf": ["san francisco 49ers", "49ers", "niners"],
        # NBA
        "lal": ["los angeles lakers", "lakers"],
        "gsw": ["golden state warriors", "warriors"],
        "bos": ["boston celtics", "celtics"],
        # MLB
        "nyy": ["new york yankees", "yankees"],
        "lad": ["los angeles dodgers", "dodgers"],
    }

    async def _build_sports_entity_context(self, user_text: str) -> str:
        """Build sports entity context for the LLM when sports-related keywords detected.

        Queries data-api for all team_tracker sensors and builds a mapping of
        team names/abbreviations to actual HA entity IDs so GPT uses real sensors
        instead of hallucinating entity IDs.

        Returns an empty string if no sports intent detected or no sensors found.
        """
        if not self.data_api_client:
            return ""

        text_lower = user_text.lower()

        # Quick sports intent detection
        sports_keywords = [
            "team",
            "score",
            "game",
            "match",
            "goal",
            "hockey",
            "football",
            "basketball",
            "baseball",
            "soccer",
            "nhl",
            "nfl",
            "nba",
            "mlb",
            "mls",
            "win",
            "lose",
            "start",
            "halftime",
            "quarter",
            "touchdown",
            "home run",
        ]
        # Also check team name keywords
        team_name_hit = False
        for _abbr, names in self._TEAM_KEYWORDS.items():
            for name in names:
                if name in text_lower:
                    team_name_hit = True
                    break
            if team_name_hit:
                break

        if not team_name_hit and not any(kw in text_lower for kw in sports_keywords):
            return ""

        try:
            entities = await self.data_api_client.fetch_entities()
            team_sensors = [
                e
                for e in entities
                if "team_tracker" in (e.get("entity_id") or "")
                and (e.get("entity_id") or "").startswith("sensor.")
            ]

            if not team_sensors:
                return ""

            lines = [
                "Sports Team Tracker Sensors (use ONLY these entity IDs for sports automations):",
            ]
            for sensor in team_sensors:
                entity_id = sensor.get("entity_id", "")
                # Extract abbreviation from entity_id (e.g., sensor.vgk_team_tracker → vgk)
                abbr = entity_id.replace("sensor.", "").replace("_team_tracker", "").lower()
                # Find known team names for this abbreviation
                known_names = self._TEAM_KEYWORDS.get(abbr, [])
                name_str = f" ({', '.join(known_names)})" if known_names else ""
                lines.append(f"  - {entity_id}: abbreviation={abbr.upper()}{name_str}")

            lines.append("")
            lines.append(
                "Team Tracker sensor states: PRE (pre-game), IN (in-progress), POST (game over), BYE, NOT_FOUND"
            )
            lines.append(
                "Key attributes: team_score, opponent_score, team_name, opponent_name, team_abbr, team_colors"
            )
            lines.append(
                "CRITICAL: For state triggers on team_tracker sensors, use 'platform: state' with 'to:' — do NOT include 'at:' field (that is for time triggers only)."
            )

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Failed to build sports entity context: {e}")
            return ""

    async def _filter_templates_by_capabilities(
        self, templates: list[dict[str, Any]], context: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Filter out templates whose required capabilities cannot be met.

        If we can identify the target area from context, check that
        the area has the required sensor types. Gracefully returns all
        templates on failure.
        """
        if not self.data_api_client or not context:
            return templates

        # Try to identify target area from context
        target_area = context.get("room") or context.get("area") or context.get("target_area")
        if not target_area:
            return templates

        try:
            areas = await self.data_api_client.fetch_areas()
            area_id = None
            for area in areas:
                if target_area.lower() in (area.get("name") or "").lower():
                    area_id = area.get("area_id")
                    break

            if not area_id:
                return templates

            entities = await self.data_api_client.fetch_entities_in_area(area_id)

            # Build set of available device classes
            available_device_classes = set()
            for entity in entities:
                device_class = entity.get("device_class", "")
                if device_class:
                    available_device_classes.add(device_class)

            # Filter templates
            filtered = []
            for t in templates:
                required_sensors = (t.get("required_capabilities") or {}).get("sensors", [])

                if required_sensors:
                    sensors_available = any(s in available_device_classes for s in required_sensors)
                    if not sensors_available:
                        logger.info(
                            f"Filtering out template '{t['template_id']}': "
                            f"requires sensors {required_sensors} but area '{target_area}' "
                            f"has device classes {available_device_classes}"
                        )
                        continue

                filtered.append(t)

            # Fallback to all if none match
            return filtered if filtered else templates
        except Exception as e:
            logger.warning(f"Failed to filter templates by capabilities: {e}")
            return templates
