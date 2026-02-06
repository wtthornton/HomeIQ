"""
Automation Patterns Service

Queries recent automations and formats them as context patterns for AI agent.
Phase 2.3: Recent Automation Patterns (Score: 75)

Provides recent automation patterns to help AI agent learn from successful patterns
and create consistent automations.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient
from ..config import Settings
from ..services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class AutomationPatternsService:
    """
    Service for generating recent automation patterns summary.
    
    Queries recent automations from Data API (automation domain entities) and
    formats them as context patterns showing automation alias, trigger, and action summary.
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize automation patterns service.
        
        Args:
            settings: Application settings
            context_builder: Context builder for cache access
        """
        self.settings = settings
        self.context_builder = context_builder
        self.data_api_client = DataAPIClient(base_url=settings.data_api_url)
        self.ha_client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token.get_secret_value()
        )
        self._cache_key = "automation_patterns_summary"
        self._cache_ttl = 1800  # 30 minutes (patterns change occasionally)

    async def get_recent_patterns(
        self,
        user_prompt: str | None = None,
        area_id: str | None = None,
        limit: int = 3,
        skip_truncation: bool = False
    ) -> str:
        """
        Get recent automation patterns formatted for context injection.
        
        Args:
            user_prompt: Optional user prompt to match patterns by intent
            area_id: Optional area filter to match patterns by area
            limit: Maximum number of patterns to return (default: 3)
            skip_truncation: If True, skip truncation (for debug display)
            
        Returns:
            Formatted patterns string like:
            "RECENT AUTOMATION PATTERNS:
            - Office Lights Morning: time trigger at 07:00 → light.turn_on (brightness: 255)
            - Motion Office Lights: state trigger (motion sensor) → light.turn_on (area: office)"
        """
        # Check cache first (only if not skipping truncation)
        if not skip_truncation:
            cache_key = f"{self._cache_key}_{area_id or 'all'}_{limit}"
            cached = await self.context_builder._get_cached_value(cache_key)
            if cached:
                logger.debug("✅ Using cached automation patterns")
                return cached

        try:
            # Query automation entities from Data API
            logger.info(f"📋 Fetching recent automation patterns (area: {area_id}, limit: {limit})...")
            
            # Fetch automation entities (domain="automation")
            automation_entities = await self.data_api_client.fetch_entities(
                domain="automation",
                area_id=area_id,
                limit=100  # Fetch more to filter by recent
            )
            
            if not automation_entities:
                logger.debug("No automation entities found")
                return ""
            
            # Fetch automation states/configs from Home Assistant to get trigger/action details
            # We'll use entity_id to query automation configs
            patterns = []
            
            # Limit to most recent automations (by entity_id or timestamp if available)
            # For now, take first N automations (Data API should return most recent first)
            recent_automations = automation_entities[:limit * 2]  # Get more to filter
            
            for automation_entity in recent_automations[:limit]:
                entity_id = automation_entity.get("entity_id")
                friendly_name = automation_entity.get("friendly_name") or entity_id.replace("automation.", "").replace("_", " ").title()
                
                if not entity_id:
                    continue
                
                # Try to get automation config from Home Assistant
                try:
                    automation_config = await self._get_automation_config(entity_id)
                    if automation_config:
                        pattern_summary = self._format_pattern_summary(
                            friendly_name,
                            automation_config
                        )
                        if pattern_summary:
                            patterns.append(pattern_summary)
                except Exception as e:
                    logger.debug(f"⚠️ Could not get config for {entity_id}: {e}")
                    # Fallback: Use entity_id and friendly_name only
                    patterns.append(f"- {friendly_name} ({entity_id})")
            
            if not patterns:
                return ""
            
            summary = "RECENT AUTOMATION PATTERNS:\n" + "\n".join(patterns)
            
            # Truncate if too long (max 500 chars for token efficiency)
            if not skip_truncation and len(summary) > 500:
                summary = summary[:500] + "... (truncated)"
            
            # Cache the result
            if not skip_truncation:
                cache_key = f"{self._cache_key}_{area_id or 'all'}_{limit}"
                await self.context_builder._set_cached_value(
                    cache_key, summary, self._cache_ttl
                )
            
            logger.info(f"✅ Generated {len(patterns)} automation patterns ({len(summary)} chars)")
            return summary
            
        except Exception as e:
            logger.warning(f"⚠️ Error generating automation patterns: {e}")
            # Return empty string - patterns are optional
            return ""

    async def _get_automation_config(self, entity_id: str) -> dict[str, Any] | None:
        """
        Get automation configuration from Home Assistant.
        
        Args:
            entity_id: Automation entity ID (e.g., "automation.office_lights_morning")
            
        Returns:
            Automation config dictionary or None if not found
        """
        try:
            # Extract config_id from entity_id (remove "automation." prefix)
            config_id = entity_id.replace("automation.", "")
            
            # Use Home Assistant REST API to get automation config
            session = await self.ha_client._get_session()
            url = f"{self.ha_client.ha_url}/api/config/automation/config/{config_id}"
            
            async with session.get(url) as response:
                if response.status == 404:
                    # Automation not found
                    return None
                response.raise_for_status()
                return await response.json()
                
        except Exception as e:
            logger.debug(f"Could not fetch automation config for {entity_id}: {e}")
            return None

    def _format_pattern_summary(
        self,
        friendly_name: str,
        automation_config: dict[str, Any]
    ) -> str:
        """
        Format automation config as pattern summary.
        
        Args:
            friendly_name: Automation friendly name
            automation_config: Automation configuration dictionary
            
        Returns:
            Formatted pattern string like:
            "Office Lights Morning: time trigger at 07:00 → light.turn_on (brightness: 255)"
        """
        # Extract trigger summary
        triggers = automation_config.get("trigger", [])
        trigger_summary = self._summarize_triggers(triggers)
        
        # Extract action summary
        actions = automation_config.get("action", [])
        action_summary = self._summarize_actions(actions)
        
        if not trigger_summary or not action_summary:
            return f"- {friendly_name}"
        
        return f"- {friendly_name}: {trigger_summary} → {action_summary}"

    def _summarize_triggers(self, triggers: list[dict[str, Any]]) -> str:
        """Summarize automation triggers."""
        if not triggers:
            return "no trigger"
        
        # Take first trigger for summary
        trigger = triggers[0] if isinstance(triggers, list) else triggers
        platform = trigger.get("platform", "unknown")
        
        if platform == "time":
            at = trigger.get("at", "")
            return f"time trigger at {at}"
        elif platform == "time_pattern":
            minutes = trigger.get("minutes", "")
            hours = trigger.get("hours", "")
            if minutes:
                return f"time_pattern trigger every {minutes} minutes"
            elif hours:
                return f"time_pattern trigger every {hours} hours"
            return "time_pattern trigger"
        elif platform == "state":
            entity_id = trigger.get("entity_id", "")
            to_state = trigger.get("to", "")
            return f"state trigger ({entity_id} → {to_state})"
        elif platform == "numeric_state":
            entity_id = trigger.get("entity_id", "")
            return f"numeric_state trigger ({entity_id})"
        else:
            return f"{platform} trigger"

    def _summarize_actions(self, actions: list[dict[str, Any]]) -> str:
        """Summarize automation actions."""
        if not actions:
            return "no action"
        
        # Take first action for summary
        action = actions[0] if isinstance(actions, list) else actions
        
        if "service" in action:
            service = action["service"]
            target = action.get("target", {})
            data = action.get("data", {})
            
            # Format target
            target_str = ""
            if isinstance(target, dict):
                if "area_id" in target:
                    target_str = f"area: {target['area_id']}"
                elif "entity_id" in target:
                    entity_id = target["entity_id"]
                    if isinstance(entity_id, list):
                        target_str = f"{len(entity_id)} entities"
                    else:
                        target_str = f"entity: {entity_id}"
            
            # Format data (key parameters only)
            data_parts = []
            if "brightness" in data:
                data_parts.append(f"brightness: {data['brightness']}")
            if "rgb_color" in data:
                rgb = data["rgb_color"]
                if isinstance(rgb, list) and len(rgb) >= 3:
                    data_parts.append(f"rgb: [{rgb[0]},{rgb[1]},{rgb[2]}]")
            if "effect" in data:
                data_parts.append(f"effect: {data['effect']}")
            
            data_str = f" ({', '.join(data_parts)})" if data_parts else ""
            target_str = f" ({target_str})" if target_str else ""
            
            return f"{service}{target_str}{data_str}"
        elif "scene" in action:
            scene = action.get("scene", "")
            return f"scene.turn_on ({scene})"
        elif "delay" in action:
            delay = action.get("delay", "")
            return f"delay ({delay})"
        else:
            return "unknown action"

    async def close(self):
        """Close service resources"""
        await self.ha_client.close()
        await self.data_api_client.close()
