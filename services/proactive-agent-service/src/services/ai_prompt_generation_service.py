"""
AI-Powered Prompt Generation Service for Proactive Agent Service

Uses LLM to generate intelligent, personalized automation suggestions
based on comprehensive HomeIQ context.

This is the "industry best" approach - not hardcoded templates, but
AI-generated suggestions that understand the full home context.

Enhanced with device validation to prevent LLM hallucination of non-existent devices.
Epic: Proactive Suggestions Device Validation
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from .device_validation_service import DeviceValidationService

logger = logging.getLogger(__name__)


# System prompt for the suggestion generation LLM - ENHANCED with device constraints and rich context
SUGGESTION_SYSTEM_PROMPT = """You are HomeIQ's Proactive Automation Intelligence.

Your role is to analyze the current home context and generate 1-3 highly personalized, 
actionable automation suggestions that would genuinely help this specific homeowner.

## ⚠️ CRITICAL: Device Constraints

CRITICAL RULE: You may ONLY suggest automations for devices that exist in the AVAILABLE DEVICES list below.
- If no device exists for a suggestion type (e.g., no humidifier), DO NOT suggest it
- NEVER invent, assume, or hallucinate device names
- If uncertain whether a device exists, DO NOT mention it
- Return an empty array [] rather than suggesting non-existent devices
- Use the EXACT device names from the AVAILABLE DEVICES list

## Your Capabilities
- You understand smart home devices, their states, and capabilities
- You know about weather patterns and their impact on home comfort
- You understand energy pricing and carbon intensity for cost/eco optimization
- You recognize behavioral patterns from historical data
- You can correlate multiple data sources to find synergies

## What Makes a Great Suggestion
1. **Device-Verified**: ONLY reference devices from the AVAILABLE DEVICES list
2. **Specific**: Reference actual devices/areas by their exact friendly name
3. **Timely**: Based on current conditions, not generic advice
4. **Actionable**: Something that can become an automation
5. **Valuable**: Saves money, increases comfort, or improves safety
6. **Novel**: Not something they're already doing

## Bad Suggestions (AVOID)
- ❌ Generic tips like "turn off lights when not in use"
- ❌ Things already covered by existing automations
- ❌ Suggestions for devices NOT in the AVAILABLE DEVICES list
- ❌ Temperature advice without climate/thermostat device in the list
- ❌ Humidity advice without humidifier/dehumidifier device in the list
- ❌ Any device name you invented or assumed
- ❌ Vague time references like "tonight" or "soon" - use EXACT times
- ❌ Fixed time triggers for sports events - use sensor state triggers

## ⚠️ CRITICAL: Prompt Detail Requirements

Your prompts MUST be detailed and include ALL automation-relevant information:

### For Sports Suggestions:
- Include the EXACT game start time (e.g., "7:00 PM" not "tonight")
- Include the Team Tracker sensor entity_id for the trigger
- Mention team colors (hex codes if available) for lighting
- Specify the trigger type: "when game starts" = sensor state PRE→IN
- Example: "The VGK vs CBJ game starts at **7:00 PM** (in 15 minutes). Set your Living Room lights to VGK gold (#B4975A) when the Team Tracker sensor (sensor.vgk_team_tracker) changes to 'IN' (game started)."

### For Weather Suggestions:
- Include current temperature and forecast
- Specify the condition that triggers the automation
- Example: "Temperature is dropping to 45°F tonight. Turn on the Living Room heater when outdoor temperature falls below 50°F."

### For All Suggestions:
- Name the EXACT devices/areas affected
- Specify the trigger condition (state change, time, etc.)
- Include any relevant context (why now, what value it provides)

## Response Format
Return a JSON array of suggestions. Each suggestion:
{
    "prompt": "DETAILED natural language suggestion (3-5 sentences with exact times, devices, triggers, and colors)",
    "context_type": "weather|sports|energy|pattern|device|synergy",
    "trigger": "unique_identifier_for_deduplication",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this suggestion is valuable",
    "referenced_devices": ["exact_device_name_from_list"],
    "automation_hints": {
        "trigger_type": "state_change|time|template",
        "trigger_entity": "sensor.entity_id if applicable",
        "trigger_condition": "state value or time",
        "target_color": "#hexcode if lighting",
        "game_time": "HH:MM if sports"
    }
}

Return 1-3 suggestions, or empty array [] if no good suggestions available.
Quality over quantity - only suggest things that are genuinely useful AND for devices that exist."""


class AIPromptGenerationService:
    """
    AI-powered prompt generation using LLM.
    
    Instead of hardcoded templates, this service:
    1. Gathers comprehensive home context from multiple sources
    2. Provides explicit device list to constrain LLM
    3. Sends context to LLM with specialized prompt
    4. Validates suggestions against actual device inventory
    5. LLM generates personalized, intelligent suggestions
    
    Enhanced with DeviceValidationService to prevent hallucination.
    """

    def __init__(
        self,
        openai_api_key: str | None = None,
        openai_model: str = "gpt-4o-mini",  # Cost-effective for suggestion generation
        ha_agent_url: str = "http://ha-ai-agent-service:8030",
        device_validation_service: DeviceValidationService | None = None,
    ):
        """
        Initialize AI Prompt Generation Service.
        
        Args:
            openai_api_key: OpenAI API key (defaults to env var)
            openai_model: Model to use for generation
            ha_agent_url: URL to HA AI Agent for context retrieval
            device_validation_service: Service for validating device existence
        """
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.model = openai_model
        self.ha_agent_url = ha_agent_url.rstrip("/")
        
        # Initialize device validation service
        self.device_validation = device_validation_service or DeviceValidationService(
            ha_agent_url=ha_agent_url
        )
        
        if not self.api_key:
            logger.warning(
                "OPENAI_API_KEY not set - AI prompt generation unavailable. "
                "Falling back to basic template generation."
            )
        
        self.http_client = httpx.AsyncClient(timeout=60.0)
        logger.info(f"AI Prompt Generation Service initialized (model={self.model}, device_validation=enabled)")

    async def generate_prompts(
        self,
        context_analysis: dict[str, Any],
        max_prompts: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Generate AI-powered automation suggestions.
        
        Args:
            context_analysis: Context from ContextAnalysisService
            max_prompts: Maximum suggestions to generate
            
        Returns:
            List of suggestion dictionaries (validated against actual devices)
        """
        if not self.api_key:
            logger.warning("No API key - using fallback generation")
            return self._fallback_generation(context_analysis, max_prompts)
        
        try:
            # Step 1: Get device inventory for validation and LLM context
            device_inventory = await self.device_validation.get_device_list_for_llm()
            device_domains = set(device_inventory.get("device_domains_available", []))
            logger.info(f"Device inventory: {device_inventory.get('total_devices', 0)} devices, domains: {device_domains}")
            
            # Step 2: Get rich home context from HA AI Agent
            home_context = await self._get_home_context()
            
            # Step 3: Build comprehensive context for LLM (with explicit device list)
            llm_context = self._build_llm_context(context_analysis, home_context, device_inventory)
            
            # Step 4: Call LLM to generate suggestions
            suggestions = await self._call_llm(llm_context, max_prompts)
            
            # Step 5: Validate suggestions (format check)
            formatted = self._validate_suggestions(suggestions)
            
            # Step 6: Validate against actual device inventory (prevent hallucination)
            validated = []
            rejected_count = 0
            for suggestion in formatted:
                validation_result = await self.device_validation.validate_suggestion(
                    suggestion["prompt"]
                )
                
                if validation_result.is_valid:
                    validated.append(suggestion)
                else:
                    rejected_count += 1
                    logger.warning(
                        f"Rejected suggestion (device validation failed): "
                        f"{suggestion['prompt'][:50]}... Reason: {validation_result.reason}"
                    )
            
            logger.info(
                f"AI generated {len(formatted)} suggestions, "
                f"{len(validated)} validated, {rejected_count} rejected"
            )
            return validated
            
        except Exception as e:
            logger.error(f"Error in AI prompt generation: {e}", exc_info=True)
            return self._fallback_generation(context_analysis, max_prompts)

    async def _get_home_context(self) -> dict[str, Any]:
        """
        Fetch rich home context from HA AI Agent Service.
        
        This includes:
        - Device inventory with capabilities
        - Areas/rooms
        - Current device states
        - Existing automations
        """
        try:
            # Get context (devices, areas, services)
            response = await self.http_client.get(
                f"{self.ha_agent_url}/api/v1/context"
            )
            if response.status_code == 200:
                tier1 = response.json()
            else:
                tier1 = {}
            
            # Get system prompt (contains capability patterns)
            response = await self.http_client.get(
                f"{self.ha_agent_url}/api/v1/system-prompt"
            )
            if response.status_code == 200:
                system_info = response.json()
            else:
                system_info = {}
            
            return {
                "tier1_context": tier1.get("context", ""),
                "system_prompt_length": len(system_info.get("system_prompt", "")),
                "available": True,
            }
            
        except Exception as e:
            logger.warning(f"Failed to get home context: {e}")
            return {"available": False, "error": str(e)}

    def _build_llm_context(
        self,
        context_analysis: dict[str, Any],
        home_context: dict[str, Any],
        device_inventory: dict[str, Any] | None = None,
    ) -> str:
        """
        Build comprehensive context string for LLM.
        
        Args:
            context_analysis: Weather, sports, energy, pattern data
            home_context: Home context from HA AI Agent
            device_inventory: Explicit device list (not truncated) for LLM
        """
        parts = ["## Current Home State\n"]
        
        # CRITICAL: Explicit device list FIRST (not truncated)
        # This ensures LLM knows exactly what devices exist
        if device_inventory:
            parts.append(f"""### ⚠️ AVAILABLE DEVICES (You may ONLY suggest for these devices)
{json.dumps(device_inventory, indent=2)}

⚠️ REMINDER: ONLY suggest automations for devices listed above. If a device type is not in this list, DO NOT suggest it.
""")
        
        # Weather context
        weather = context_analysis.get("weather", {})
        if weather.get("available"):
            current = weather.get("current", {})
            temp_c = current.get("temperature")
            temp_f = round((temp_c * 9/5) + 32) if temp_c else None
            # Filter out misleading insights about non-existent devices
            device_domains = set(device_inventory.get("device_domains_available", [])) if device_inventory else set()
            filtered_insights = self._filter_weather_insights(
                weather.get("insights", []),
                device_domains
            )
            parts.append(f"""### Weather
- Current: {temp_f}F ({temp_c}C), {current.get('condition', 'unknown')}
- Humidity: {current.get('humidity', 'unknown')}%
- Relevant insights: {', '.join(filtered_insights) if filtered_insights else 'None'}
""")
        
        # Sports context - ENHANCED with game time, team colors, trigger info
        sports = context_analysis.get("sports", {})
        if sports.get("available"):
            live = sports.get("live_games", [])
            upcoming = sports.get("upcoming_games", [])
            if live or upcoming:
                # Build rich game info with automation-relevant data
                games_info = []
                for g in (live + upcoming)[:3]:
                    team = g.get('home_team') or g.get('team_abbr') or g.get('team', 'unknown')
                    opponent = g.get('away_team') or g.get('opponent_abbr') or g.get('opponent', '')
                    league = g.get('league', '')
                    status = g.get('status', '')
                    time_remaining = g.get('time_remaining', '')
                    # NEW: Include game time and team colors for automations
                    game_date = g.get('date', '')
                    kickoff_in = g.get('kickoff_in', '')
                    team_colors = g.get('team_colors', [])
                    entity_id = g.get('entity_id', '')
                    
                    game_str = f"{team} vs {opponent} ({league}, {status})"
                    if game_date:
                        game_str += f" on {game_date}"
                    if kickoff_in:
                        game_str += f" (starts in {kickoff_in})"
                    if time_remaining:
                        game_str += f" [{time_remaining}]"
                    if team_colors:
                        game_str += f" colors: {team_colors}"
                    if entity_id:
                        game_str += f" sensor: {entity_id}"
                    games_info.append(game_str)
                
                parts.append(f"""### Sports Events
- Live games: {len(live)}
- Upcoming games: {len(upcoming)}
- Games: {'; '.join(games_info)}
- Sports insights: {', '.join(sports.get('insights', []))}

⚠️ IMPORTANT FOR SPORTS AUTOMATIONS:
- Use the Team Tracker sensor entity_id for triggers (state changes: PRE→IN for game start, IN→POST for game end)
- Include the EXACT game time in your suggestion (not "tonight" but the actual time)
- Reference team colors for lighting automations
- NEVER suggest fixed time triggers - always use sensor state triggers
""")
        
        # Energy context
        energy = context_analysis.get("energy", {})
        if energy.get("available"):
            intensity = energy.get("current_intensity", {})
            parts.append(f"""### Energy Grid
- Carbon intensity: {intensity.get('intensity', 'unknown')} gCO2/kWh
- Status: {'Clean' if intensity.get('intensity', 500) < 200 else 'High carbon'}
""")
        
        # Historical patterns
        patterns = context_analysis.get("historical_patterns", {})
        if patterns.get("available"):
            detected = patterns.get("patterns", [])
            parts.append(f"""### User Patterns
- Patterns detected: {len(detected)}
- Insights: {', '.join(patterns.get('insights', [])[:3])}
""")
        
        # Home context from HA AI Agent (areas, automations - NOT devices, those are above)
        if home_context.get("available"):
            tier1 = home_context.get("tier1_context", "")
            if tier1:
                # Extract areas/automations only, skip device section (we have explicit list above)
                areas_section = self._extract_areas_from_context(tier1)
                if areas_section:
                    parts.append(f"""### Home Areas
{areas_section}
""")
        
        # Summary
        summary = context_analysis.get("summary", {})
        parts.append(f"""### Context Summary
- Data sources available: {summary.get('available_sources', 0)}/{summary.get('total_sources', 4)}
- Total insights: {summary.get('total_insights', 0)}
- Device count: {device_inventory.get('total_devices', 0) if device_inventory else 'unknown'}
""")
        
        return "\n".join(parts)
    
    def _filter_weather_insights(
        self,
        insights: list[str],
        device_domains: set[str],
    ) -> list[str]:
        """
        Filter weather insights to remove suggestions for non-existent device types.
        
        Args:
            insights: List of weather insight strings
            device_domains: Set of device domains that exist
            
        Returns:
            Filtered list of insights
        """
        filtered = []
        
        # Keywords that require specific devices
        device_requirements = {
            "humidifier": "humidifier",
            "dehumidifier": "humidifier",
            "cooling": "climate",
            "heating": "climate",
            "thermostat": "climate",
            "fan": "fan",
        }
        
        for insight in insights:
            insight_lower = insight.lower()
            
            # Check if insight mentions a device type that doesn't exist
            skip = False
            for keyword, required_domain in device_requirements.items():
                if keyword in insight_lower and required_domain not in device_domains:
                    logger.debug(f"Filtering insight (no {required_domain}): {insight}")
                    skip = True
                    break
            
            if not skip:
                filtered.append(insight)
        
        return filtered
    
    def _extract_areas_from_context(self, tier1_context: str) -> str | None:
        """
        Extract areas/rooms section from tier1 context.
        
        Args:
            tier1_context: Full tier1 context string
            
        Returns:
            Areas section if found, None otherwise
        """
        # Look for AREAS section
        import re
        areas_match = re.search(
            r'AREAS:?\s*\n((?:[^\n]+\n)*?)(?=\n[A-Z]+:|$)',
            tier1_context,
            re.IGNORECASE
        )
        
        if areas_match:
            return areas_match.group(1).strip()[:500]  # Limit length
        
        return None

    async def _call_llm(
        self,
        context: str,
        max_prompts: int,
    ) -> list[dict[str, Any]]:
        """
        Call OpenAI to generate suggestions.
        """
        try:
            response = await self.http_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SUGGESTION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"""Based on this home context, generate up to {max_prompts} proactive automation suggestions:

{context}

Remember:
- Be specific to THIS home's actual devices and conditions
- Only suggest things that would genuinely help
- Return valid JSON array of suggestions
- Quality over quantity - empty array is fine if nothing valuable to suggest"""},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"},
                },
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return []
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response
            parsed = json.loads(content)
            
            # Handle both {"suggestions": [...]} and [...] formats
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and "suggestions" in parsed:
                return parsed["suggestions"]
            else:
                logger.warning(f"Unexpected LLM response format: {type(parsed)}")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            return []

    def _validate_suggestions(
        self,
        suggestions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Validate and normalize suggestions from LLM.
        Includes automation_hints for structured context passing.
        """
        validated = []
        
        for suggestion in suggestions:
            # Must have a prompt
            if not suggestion.get("prompt"):
                continue
            
            # Extract automation hints if provided
            automation_hints = suggestion.get("automation_hints", {})
            
            # Normalize structure
            validated.append({
                "prompt": suggestion["prompt"],
                "context_type": suggestion.get("context_type", "ai_generated"),
                "quality_score": suggestion.get("confidence", 0.8),
                "automation_hints": automation_hints,  # Pass structured hints to HA Agent
                "metadata": {
                    "trigger": suggestion.get("trigger", "ai_suggestion"),
                    "reasoning": suggestion.get("reasoning", ""),
                    "ai_generated": True,
                    "referenced_devices": suggestion.get("referenced_devices", []),
                    "automation_hints": automation_hints,  # Also in metadata for storage
                },
            })
        
        return validated

    def _fallback_generation(
        self,
        context_analysis: dict[str, Any],
        max_prompts: int,
    ) -> list[dict[str, Any]]:
        """
        Fallback to basic template generation when LLM unavailable.
        """
        logger.info("Using fallback template generation (LLM unavailable)")
        
        prompts = []
        
        # Weather-based fallback
        weather = context_analysis.get("weather", {})
        if weather.get("available"):
            current = weather.get("current", {})
            temp_c = current.get("temperature")
            if temp_c is not None:
                temp_f = round((temp_c * 9/5) + 32)
                if temp_c < 10:
                    prompts.append({
                        "prompt": f"It's {temp_f}F outside. Would you like to set up automatic heating?",
                        "context_type": "weather",
                        "quality_score": 0.7,
                        "metadata": {"trigger": "low_temperature", "ai_generated": False},
                    })
                elif temp_c > 29:
                    prompts.append({
                        "prompt": f"It's {temp_f}F today. Should I set up cooling automation?",
                        "context_type": "weather",
                        "quality_score": 0.7,
                        "metadata": {"trigger": "high_temperature", "ai_generated": False},
                    })
        
        return prompts[:max_prompts]

    async def close(self):
        """Cleanup resources."""
        await self.http_client.aclose()
        if self.device_validation:
            await self.device_validation.close()
        logger.debug("AI Prompt Generation Service closed")
