"""
Home Assistant API Client (2025 Patterns)

Epic 39, Story 39.10: Automation Service Foundation
Async client for deploying and managing automations in Home Assistant.
"""

import logging
import re
import uuid
from typing import Any

import httpx
import yaml
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """
    Async client for interacting with Home Assistant REST API.

    Features:
    - Async HTTP requests with httpx
    - Automatic retry logic
    - Connection pooling
    - Proper error handling
    """

    def __init__(
        self,
        ha_url: str | None = None,
        access_token: str | None = None,
        max_retries: int = 3,
        timeout: float = 10.0,
    ):
        """
        Initialize HA client.

        Args:
            ha_url: Home Assistant URL (defaults to settings.ha_url)
            access_token: Long-lived access token (defaults to settings.ha_token)
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
        """
        self.ha_url = (ha_url or settings.ha_url or "").rstrip("/")
        self.access_token = access_token or settings.ha_token or ""
        self.max_retries = max_retries
        self.timeout = timeout

        if not self.ha_url or not self.access_token:
            logger.warning("Home Assistant URL or token not configured")

        # Create async HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
        )

        logger.info(f"Home Assistant client initialized with url={self.ha_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def deploy_automation(self, automation_yaml: str) -> dict[str, Any]:
        """
        Deploy automation to Home Assistant.

        Args:
            automation_yaml: Home Assistant automation YAML as string

        Returns:
            Dictionary with automation_id and status

        Raises:
            httpx.HTTPError: If deployment fails
            ValueError: If YAML is invalid
        """
        if not self.ha_url or not self.access_token:
            raise ValueError("Home Assistant URL and token must be configured")

        # Parse YAML to validate
        try:
            automation_data = yaml.safe_load(automation_yaml)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}") from e

        if not automation_data or not isinstance(automation_data, dict):
            raise ValueError("YAML must contain a valid automation dictionary")

        # Sanitize automation: strip invalid fields before sending to HA
        automation_data = self._sanitize_automation(automation_data)

        # Generate unique automation ID if not present
        if "id" not in automation_data:
            automation_data["id"] = f"automation.{uuid.uuid4().hex[:8]}"

        automation_id = automation_data["id"]

        # Log sanitized payload for debugging
        logger.info(
            f"Deploying automation {automation_id}, payload keys: {list(automation_data.keys())}"
        )
        if automation_data.get("condition"):
            logger.info(f"Conditions after sanitization: {automation_data['condition']}")

        # Deploy via Home Assistant API
        url = f"{self.ha_url}/api/config/automation/config/{automation_id}"

        try:
            response = await self.client.post(
                url, json=automation_data, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Automation deployed: {automation_id}")

            # Post-deploy verification using PostActionVerifier pattern (Story 3 + Reusable Pattern Framework)
            from ..services.automation_deploy_verifier import AutomationDeployVerifier

            verifier = AutomationDeployVerifier(get_state_fn=self.get_state)
            verification = await verifier.verify(
                {
                    "automation_id": automation_id,
                    "status": "deployed",
                }
            )

            response_data: dict[str, Any] = {
                "automation_id": automation_id,
                "status": "deployed",
                "data": result,
            }
            if verification.state is not None:
                response_data["state"] = verification.state
                response_data["attributes"] = verification.metadata.get("attributes", {})
            if verification.verification_warning:
                response_data["verification_warning"] = verification.verification_warning
                logger.warning(
                    f"Post-deploy verification: automation {automation_id} is unavailable"
                )
            return response_data
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to deploy automation: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error deploying automation: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    def _sanitize_automation(self, automation_data: dict[str, Any]) -> dict[str, Any]:
        """Sanitize automation data before sending to HA.

        Fixes common issues:
        - Strips 'at' from non-time triggers (HA returns 400 'extra keys not allowed')
        - Removes empty string values for 'to'/'from' in triggers
        - Removes empty 'area_id' from targets (HA rejects empty area_id)
        - Removes fields HA doesn't recognize in conditions
        """
        # 'at' is only valid for 'time' platform triggers
        _AT_ONLY_PLATFORMS = {"time", "time_pattern"}

        # --- Sanitize triggers ---
        triggers = automation_data.get("trigger", [])
        if isinstance(triggers, dict):
            triggers = [triggers]

        for trigger in triggers:
            if not isinstance(trigger, dict):
                continue
            platform = trigger.get("platform", "")
            # Strip 'at' from non-time triggers
            if platform not in _AT_ONLY_PLATFORMS and "at" in trigger:
                logger.info(
                    f"Stripping invalid 'at' from '{platform}' trigger (value={trigger['at']!r})"
                )
                del trigger["at"]
            # Strip empty 'to'/'from' values
            for field in ("to", "from"):
                if field in trigger and trigger[field] in (None, "", "''"):
                    logger.info(f"Stripping empty '{field}' from trigger")
                    del trigger[field]

        # --- Sanitize actions: remove empty area_id from targets ---
        actions = automation_data.get("action", [])
        if isinstance(actions, dict):
            actions = [actions]

        for action in actions:
            if not isinstance(action, dict):
                continue
            target = action.get("target")
            if isinstance(target, dict) and "area_id" in target and target.get("area_id") in (None, "", "''", []):
                del target["area_id"]
                logger.info("Stripping empty 'area_id' from action target")

        # --- Sanitize conditions: fix common GPT-generated condition format issues ---
        conditions = automation_data.get("condition", [])
        if isinstance(conditions, list):
            automation_data["condition"] = self._sanitize_conditions(conditions)

        # --- Sanitize action data: strip non-HA fields ---
        for action in actions:
            if not isinstance(action, dict):
                continue
            data = action.get("data")
            if isinstance(data, dict):
                # Remove non-HA fields GPT likes to inject
                for bad_key in (
                    "note",
                    "description",
                    "sequence_colors",
                    "rgb_color_sequence",
                    "rgb_sequence",
                    "repeat",
                    "fallback_colors",
                    "color_template",
                ):
                    if bad_key in data:
                        logger.info(f"Stripping non-HA field '{bad_key}' from action data")
                        del data[bad_key]

        # --- Improve generic/bad alias names ---
        alias = automation_data.get("alias", "")
        _GENERIC_ALIASES = {
            "",
            "automation",
            "multi-condition automation",
            "automation with or conditions",
            "automation with and conditions",
            "new automation",
            "untitled",
            "untitled automation",
        }
        # Also detect aliases containing raw entity_id patterns
        # e.g. "sensor.vgk_team_tracker → light.turn_on"
        _RAW_ENTITY_RE = re.compile(
            r"\b(?:sensor|light|switch|binary_sensor|input_boolean|climate|"
            r"cover|fan|media_player|automation|script|scene|input_number|"
            r"input_select|group|number|select|button)\.\w+"
        )
        needs_alias = alias.lower().strip() in _GENERIC_ALIASES or _RAW_ENTITY_RE.search(alias)
        if needs_alias:
            new_alias = self._generate_alias(automation_data)
            logger.info(f"Replacing alias '{alias}' → '{new_alias}'")
            automation_data["alias"] = new_alias

        # --- Remove non-standard top-level fields HA doesn't understand ---
        _KNOWN_TOP_LEVEL = {
            "id",
            "alias",
            "description",
            "trigger",
            "condition",
            "action",
            "mode",
            "max",
            "max_exceeded",
            "variables",
            "trace",
            "initial_state",
        }
        unknown_keys = [k for k in automation_data if k not in _KNOWN_TOP_LEVEL]
        for key in unknown_keys:
            logger.info(f"Stripping unknown top-level field '{key}' from automation")
            del automation_data[key]

        return automation_data

    def _sanitize_conditions(self, conditions: list) -> list:
        """Sanitize condition list to match HA format.

        GPT often generates conditions with 'type'/'condition_type'/'entity'
        instead of the correct HA fields 'condition'/'entity_id'.
        """
        sanitized = []
        for cond in conditions:
            if not isinstance(cond, dict):
                sanitized.append(cond)
                continue

            fixed = dict(cond)

            # Fix 'or'/'and' wrapper conditions
            if fixed.get("condition") in ("or", "and"):
                inner = fixed.get("conditions", [])
                if isinstance(inner, list):
                    fixed["conditions"] = self._sanitize_conditions(inner)
                sanitized.append(fixed)
                continue

            # Map GPT condition types → valid HA condition types
            _COND_TYPE_MAP = {
                "state": "state",
                "numeric_state": "numeric_state",
                "template": "template",
                "attribute_changed": "numeric_state",
                "attribute_increase": "numeric_state",
                "attribute_decrease": "numeric_state",
                "time": "time",
                "zone": "zone",
                "sun": "sun",
                "device": "device",
                "trigger": "trigger",
            }

            # Fix condition_type → condition
            if "condition_type" in fixed and "condition" not in fixed:
                ct = fixed.pop("condition_type")
                mapped = _COND_TYPE_MAP.get(ct)
                if not mapped:
                    logger.warning(f"Unknown condition_type '{ct}', falling back to 'template'")
                    mapped = "template"
                fixed["condition"] = mapped

            # Fix 'type' → 'condition' (another GPT pattern)
            if "type" in fixed and "condition" not in fixed:
                t = fixed.pop("type")
                mapped = _COND_TYPE_MAP.get(t)
                if not mapped:
                    logger.warning(f"Unknown condition type '{t}', falling back to 'template'")
                    mapped = "template"
                fixed["condition"] = mapped

            # Fix 'entity' → 'entity_id'
            if "entity" in fixed and "entity_id" not in fixed:
                fixed["entity_id"] = fixed.pop("entity")

            # For state conditions: HA uses 'state' key (not 'to')
            if fixed.get("condition") == "state" and "to" in fixed and "state" not in fixed:
                fixed["state"] = fixed.pop("to")

            # For numeric_state: ensure 'above' or 'below' key exists
            if (
                fixed.get("condition") == "numeric_state"
                and "above" not in fixed
                and "below" not in fixed
            ):
                fixed["above"] = 0

            # For template conditions that were converted from unknown types:
            # Build a value_template from available fields and strip non-HA keys
            if fixed.get("condition") == "template" and "value_template" not in fixed:
                entity_id = fixed.get("entity_id", "")
                attribute = fixed.get("attribute", "")
                if entity_id and attribute:
                    fixed["value_template"] = (
                        f"{{{{ state_attr('{entity_id}', '{attribute}') | int(0) > 0 }}}}"
                    )
                elif entity_id:
                    state = fixed.get("state", fixed.get("to", ""))
                    if state:
                        fixed["value_template"] = f"{{{{ is_state('{entity_id}', '{state}') }}}}"
                    else:
                        fixed["value_template"] = "{{ true }}"
                else:
                    fixed["value_template"] = "{{ true }}"

            # Determine valid fields per condition type
            _VALID_FIELDS: dict[str, set[str]] = {
                "state": {"condition", "entity_id", "state", "for", "attribute", "alias"},
                "numeric_state": {
                    "condition",
                    "entity_id",
                    "above",
                    "below",
                    "attribute",
                    "value_template",
                    "alias",
                },
                "template": {"condition", "value_template", "alias"},
                "time": {"condition", "after", "before", "weekday", "alias"},
                "zone": {"condition", "entity_id", "zone", "state", "alias"},
                "sun": {"condition", "after", "before", "after_offset", "before_offset", "alias"},
                "trigger": {"condition", "id", "alias"},
                "device": {"condition", "device_id", "domain", "entity_id", "type", "alias"},
            }
            cond_type = fixed.get("condition", "")
            valid = _VALID_FIELDS.get(cond_type)
            if valid:
                extra_keys = [k for k in fixed if k not in valid]
                for k in extra_keys:
                    logger.info(f"Stripping invalid field '{k}' from '{cond_type}' condition")
                    del fixed[k]

            # Strip non-HA fields from conditions (catch-all)
            for bad_key in ("description", "change"):
                fixed.pop(bad_key, None)

            sanitized.append(fixed)

        return sanitized

    def _generate_alias(self, automation_data: dict[str, Any]) -> str:
        """Generate a meaningful alias from the automation's triggers and actions.

        Produces names like:
        - 'VGK Game → Lights Strobe'
        - 'Motion Office → Lights On'
        - 'Midnight → All Lights Off'
        """
        parts: list[str] = []

        # Extract trigger description
        triggers = automation_data.get("trigger", [])
        if isinstance(triggers, dict):
            triggers = [triggers]
        if triggers and isinstance(triggers[0], dict):
            t = triggers[0]
            platform = t.get("platform", "")
            entity_id = t.get("entity_id", "")
            to_state = t.get("to", "")

            if "team_tracker" in entity_id:
                # Sports trigger: use team abbreviation
                abbr = entity_id.replace("sensor.", "").replace("_team_tracker", "").upper()
                parts.append(f"{abbr} Game")
            elif platform == "time":
                at_time = t.get("at", "")
                parts.append(f"At {at_time}" if at_time else "Scheduled")
            elif platform == "state" and entity_id:
                # Shorten entity_id: binary_sensor.office_motion → Office Motion
                short = entity_id.split(".")[-1].replace("_", " ").title()
                parts.append(short)
                if to_state:
                    parts[-1] += f" {to_state}"
            else:
                parts.append(platform.replace("_", " ").title() if platform else "Trigger")

        # Extract action description
        actions = automation_data.get("action", [])
        if isinstance(actions, dict):
            actions = [actions]
        if actions and isinstance(actions[0], dict):
            a = actions[0]
            service = a.get("service", "")
            data = a.get("data", {}) or {}
            effect = data.get("effect", "")

            if service:
                # light.turn_on → Light Turn On
                svc_parts = service.split(".")
                domain = svc_parts[0].title() if svc_parts else ""
                action_name = svc_parts[1].replace("_", " ").title() if len(svc_parts) > 1 else ""
                action_str = f"{domain} {action_name}".strip()
                if effect:
                    action_str += f" ({effect.replace('_', ' ').title()})"
                parts.append(action_str)

        alias = " → ".join(parts) if len(parts) == 2 else " ".join(parts)
        return alias or "Automation"

    async def get_automation(self, automation_id: str) -> dict[str, Any] | None:
        """
        Get automation from Home Assistant.

        Args:
            automation_id: Automation entity ID

        Returns:
            Automation data or None if not found
        """
        if not self.ha_url or not self.access_token:
            return None

        url = f"{self.ha_url}/api/config/automation/config/{automation_id}"

        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get automation {automation_id}: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def list_automations(self) -> list[dict[str, Any]]:
        """
        List all automations from Home Assistant.

        Uses /api/states endpoint and filters for automation.* entities.
        This is the correct Home Assistant API endpoint (not /api/config/automation/config).

        Returns:
            List of automation dictionaries
        """
        if not self.ha_url or not self.access_token:
            logger.warning("Home Assistant URL or token not configured - cannot list automations")
            return []

        url = f"{self.ha_url}/api/states"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            all_states = response.json()

            # Filter for automation entities
            if isinstance(all_states, list):
                automations = [
                    state
                    for state in all_states
                    if (state.get("entity_id") or "").startswith("automation.")
                ]
                logger.info(f"✅ Found {len(automations)} automations in Home Assistant")
                return automations
            else:
                logger.warning(f"Unexpected response format from /api/states: {type(all_states)}")
                return []
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Home Assistant API error listing automations: {e.response.status_code} - {e.response.text}"
            )
            return []
        except httpx.HTTPError as e:
            logger.error(f"Failed to connect to Home Assistant: {e}")
            return []

    async def enable_automation(self, automation_id: str) -> bool:
        """
        Enable an automation.

        Args:
            automation_id: Automation entity ID

        Returns:
            True if successful
        """
        if not self.ha_url or not self.access_token:
            return False

        url = f"{self.ha_url}/api/services/automation/turn_on"

        try:
            response = await self.client.post(url, json={"entity_id": automation_id})
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to enable automation {automation_id}: {e}")
            return False

    async def disable_automation(self, automation_id: str) -> bool:
        """
        Disable an automation.

        Args:
            automation_id: Automation entity ID

        Returns:
            True if successful
        """
        if not self.ha_url or not self.access_token:
            return False

        url = f"{self.ha_url}/api/services/automation/turn_off"

        try:
            response = await self.client.post(url, json={"entity_id": automation_id})
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to disable automation {automation_id}: {e}")
            return False

    async def trigger_automation(self, automation_id: str) -> bool:
        """
        Trigger an automation.

        Args:
            automation_id: Automation entity ID

        Returns:
            True if successful
        """
        if not self.ha_url or not self.access_token:
            return False

        url = f"{self.ha_url}/api/services/automation/trigger"

        try:
            response = await self.client.post(url, json={"entity_id": automation_id})
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to trigger automation {automation_id}: {e}")
            return False

    async def get_state(self, entity_id: str) -> dict[str, Any] | None:
        """
        Get the current state of an entity (M6 fix).

        Args:
            entity_id: Entity ID (e.g. "light.living_room")

        Returns:
            State dictionary or None if not found
        """
        if not self.ha_url or not self.access_token:
            return None

        url = f"{self.ha_url}/api/states/{entity_id}"
        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get state for {entity_id}: {e}")
            return None

    async def set_state(
        self, entity_id: str, state: str, attributes: dict[str, Any] | None = None
    ) -> bool:
        """
        Set the state of an entity (M6 fix).

        Uses the HA /api/states/<entity_id> POST endpoint.

        Args:
            entity_id: Entity ID
            state: New state value
            attributes: Optional attributes dict

        Returns:
            True if successful
        """
        if not self.ha_url or not self.access_token:
            return False

        url = f"{self.ha_url}/api/states/{entity_id}"
        payload: dict[str, Any] = {"state": state}
        if attributes:
            payload["attributes"] = attributes

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to set state for {entity_id}: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Check if Home Assistant is accessible.

        Returns:
            True if service is healthy
        """
        if not self.ha_url or not self.access_token:
            return False

        try:
            url = f"{self.ha_url}/api/"
            response = await self.client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Home Assistant health check failed: {e}")
            return False

    async def close(self):
        """Close HTTP client connection."""
        await self.client.aclose()
        logger.debug("Home Assistant client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
