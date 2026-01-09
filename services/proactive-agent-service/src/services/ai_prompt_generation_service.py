"""
AI-Powered Prompt Generation Service for Proactive Agent Service

Uses LLM to generate intelligent, personalized automation suggestions
based on comprehensive HomeIQ context.

This is the "industry best" approach - not hardcoded templates, but
AI-generated suggestions that understand the full home context.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# System prompt for the suggestion generation LLM
SUGGESTION_SYSTEM_PROMPT = """You are HomeIQ's Proactive Automation Intelligence.

Your role is to analyze the current home context and generate 1-3 highly personalized, 
actionable automation suggestions that would genuinely help this specific homeowner.

## Your Capabilities
- You understand smart home devices, their states, and capabilities
- You know about weather patterns and their impact on home comfort
- You understand energy pricing and carbon intensity for cost/eco optimization
- You recognize behavioral patterns from historical data
- You can correlate multiple data sources to find synergies

## What Makes a Great Suggestion
1. **Specific**: Reference actual devices/areas by name, not generic
2. **Timely**: Based on current conditions, not generic advice
3. **Actionable**: Something that can become an automation
4. **Valuable**: Saves money, increases comfort, or improves safety
5. **Novel**: Not something they're already doing (check existing automations)

## Bad Suggestions (AVOID)
- Generic tips like "turn off lights when not in use"
- Things already covered by existing automations
- Suggestions that don't match their actual devices
- Temperature advice without knowing their comfort preferences

## Response Format
Return a JSON array of suggestions. Each suggestion:
{
    "prompt": "Natural language suggestion to show the user (1-2 sentences)",
    "context_type": "weather|sports|energy|pattern|device|synergy",
    "trigger": "unique_identifier_for_deduplication",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this suggestion is valuable"
}

Return 1-3 suggestions, or empty array [] if no good suggestions available.
Quality over quantity - only suggest things that are genuinely useful."""


class AIPromptGenerationService:
    """
    AI-powered prompt generation using LLM.
    
    Instead of hardcoded templates, this service:
    1. Gathers comprehensive home context from multiple sources
    2. Sends context to LLM with specialized prompt
    3. LLM generates personalized, intelligent suggestions
    """

    def __init__(
        self,
        openai_api_key: str | None = None,
        openai_model: str = "gpt-4o-mini",  # Cost-effective for suggestion generation
        ha_agent_url: str = "http://ha-ai-agent-service:8030",
    ):
        """
        Initialize AI Prompt Generation Service.
        
        Args:
            openai_api_key: OpenAI API key (defaults to env var)
            openai_model: Model to use for generation
            ha_agent_url: URL to HA AI Agent for context retrieval
        """
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.model = openai_model
        self.ha_agent_url = ha_agent_url.rstrip("/")
        
        if not self.api_key:
            logger.warning(
                "OPENAI_API_KEY not set - AI prompt generation unavailable. "
                "Falling back to basic template generation."
            )
        
        self.http_client = httpx.AsyncClient(timeout=60.0)
        logger.info(f"AI Prompt Generation Service initialized (model={self.model})")

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
            List of suggestion dictionaries
        """
        if not self.api_key:
            logger.warning("No API key - using fallback generation")
            return self._fallback_generation(context_analysis, max_prompts)
        
        try:
            # Step 1: Get rich home context from HA AI Agent
            home_context = await self._get_home_context()
            
            # Step 2: Build comprehensive context for LLM
            llm_context = self._build_llm_context(context_analysis, home_context)
            
            # Step 3: Call LLM to generate suggestions
            suggestions = await self._call_llm(llm_context, max_prompts)
            
            # Step 4: Validate and format suggestions
            validated = self._validate_suggestions(suggestions)
            
            logger.info(f"AI generated {len(validated)} suggestions")
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
            # Get Tier 1 context (devices, areas, services)
            response = await self.http_client.get(
                f"{self.ha_agent_url}/api/v1/context/tier1"
            )
            if response.status_code == 200:
                tier1 = response.json()
            else:
                tier1 = {}
            
            # Get system prompt (contains capability patterns)
            response = await self.http_client.get(
                f"{self.ha_agent_url}/api/v1/context/system-prompt"
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
    ) -> str:
        """
        Build comprehensive context string for LLM.
        """
        parts = ["## Current Home State\n"]
        
        # Weather context
        weather = context_analysis.get("weather", {})
        if weather.get("available"):
            current = weather.get("current", {})
            temp_c = current.get("temperature")
            temp_f = round((temp_c * 9/5) + 32) if temp_c else None
            parts.append(f"""### Weather
- Current: {temp_f}F ({temp_c}C), {current.get('condition', 'unknown')}
- Humidity: {current.get('humidity', 'unknown')}%
- Insights: {', '.join(weather.get('insights', []))}
""")
        
        # Sports context  
        sports = context_analysis.get("sports", {})
        if sports.get("available"):
            live = sports.get("live_games", [])
            upcoming = sports.get("upcoming_games", [])
            if live or upcoming:
                # Build team info - handle both 'team' and 'home_team' field names
                games_info = []
                for g in (live + upcoming)[:3]:
                    team = g.get('home_team') or g.get('team_abbr') or g.get('team', 'unknown')
                    opponent = g.get('away_team') or g.get('opponent_abbr') or g.get('opponent', '')
                    league = g.get('league', '')
                    status = g.get('status', '')
                    time_remaining = g.get('time_remaining', '')
                    if opponent:
                        games_info.append(f"{team} vs {opponent} ({league}, {status}) {time_remaining}")
                    else:
                        games_info.append(f"{team} ({league})")
                
                parts.append(f"""### Sports Events
- Live games: {len(live)}
- Upcoming games: {len(upcoming)}
- Games: {'; '.join(games_info)}
- Sports insights: {', '.join(sports.get('insights', []))}
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
        
        # Home context from HA AI Agent
        if home_context.get("available"):
            tier1 = home_context.get("tier1_context", "")
            if tier1:
                # Truncate to avoid token limits
                parts.append(f"""### Home Devices & Areas
{tier1[:3000]}...
""")
        
        # Summary
        summary = context_analysis.get("summary", {})
        parts.append(f"""### Context Summary
- Data sources available: {summary.get('available_sources', 0)}/{summary.get('total_sources', 4)}
- Total insights: {summary.get('total_insights', 0)}
""")
        
        return "\n".join(parts)

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
        """
        validated = []
        
        for suggestion in suggestions:
            # Must have a prompt
            if not suggestion.get("prompt"):
                continue
            
            # Normalize structure
            validated.append({
                "prompt": suggestion["prompt"],
                "context_type": suggestion.get("context_type", "ai_generated"),
                "quality_score": suggestion.get("confidence", 0.8),
                "metadata": {
                    "trigger": suggestion.get("trigger", "ai_suggestion"),
                    "reasoning": suggestion.get("reasoning", ""),
                    "ai_generated": True,
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
        logger.debug("AI Prompt Generation Service closed")
