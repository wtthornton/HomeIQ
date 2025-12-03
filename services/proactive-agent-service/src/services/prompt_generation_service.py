"""
Prompt Generation Service for Proactive Agent Service

Generates context-aware, natural language prompts for the HA AI Agent Service.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PromptGenerationService:
    """Service for generating context-aware prompts"""

    def __init__(self):
        """Initialize Prompt Generation Service"""
        self.templates = self._load_templates()
        logger.info("Prompt Generation Service initialized")

    def generate_prompts(self, context_analysis: dict[str, Any], max_prompts: int = 5) -> list[dict[str, Any]]:
        """
        Generate context-aware prompts from analysis results.

        Args:
            context_analysis: Results from ContextAnalysisService.analyze_all_context()
            max_prompts: Maximum number of prompts to generate (default: 5)

        Returns:
            List of prompt dictionaries with:
            {
                "prompt": str,
                "context_type": str,
                "quality_score": float,
                "metadata": {...}
            }
        """
        logger.debug("Generating prompts from context analysis")

        prompts = []

        # Generate weather-based prompts
        weather_prompts = self._generate_weather_prompts(context_analysis.get("weather", {}))
        prompts.extend(weather_prompts)

        # Generate sports-based prompts
        sports_prompts = self._generate_sports_prompts(context_analysis.get("sports", {}))
        prompts.extend(sports_prompts)

        # Generate energy-based prompts
        energy_prompts = self._generate_energy_prompts(context_analysis.get("energy", {}))
        prompts.extend(energy_prompts)

        # Generate historical pattern-based prompts
        pattern_prompts = self._generate_pattern_prompts(context_analysis.get("historical_patterns", {}))
        prompts.extend(pattern_prompts)

        # Score and filter prompts
        scored_prompts = [self._score_prompt(p) for p in prompts]
        scored_prompts.sort(key=lambda x: x["quality_score"], reverse=True)

        # Return top prompts
        top_prompts = scored_prompts[:max_prompts]

        logger.info(f"Generated {len(top_prompts)} prompts from {len(prompts)} candidates")
        return top_prompts

    def _generate_weather_prompts(self, weather_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate prompts based on weather context"""
        prompts = []

        if not weather_data.get("available"):
            return prompts

        current = weather_data.get("current", {})
        temperature = current.get("temperature")
        condition = current.get("condition", "").lower()
        forecast = weather_data.get("forecast", [])

        # High temperature prompt
        if temperature and temperature > 85:
            prompt = (
                f"It's going to be {temperature}°F today. "
                "Should I create an automation to pre-cool your home before you arrive?"
            )
            prompts.append({
                "prompt": prompt,
                "context_type": "weather",
                "metadata": {
                    "temperature": temperature,
                    "trigger": "high_temperature",
                },
            })

        # Low temperature prompt
        elif temperature and temperature < 50:
            prompt = (
                f"It's going to be {temperature}°F today. "
                "Should I create an automation to pre-heat your home before you arrive?"
            )
            prompts.append({
                "prompt": prompt,
                "context_type": "weather",
                "metadata": {
                    "temperature": temperature,
                    "trigger": "low_temperature",
                },
            })

        # Rainy weather prompt
        if "rain" in condition or "rainy" in condition:
            prompt = (
                "It's going to rain today. "
                "Should I create an automation to close windows and adjust outdoor devices?"
            )
            prompts.append({
                "prompt": prompt,
                "context_type": "weather",
                "metadata": {
                    "condition": condition,
                    "trigger": "rain",
                },
            })

        # Forecast-based prompt
        if forecast and len(forecast) > 0:
            tomorrow_temp = forecast[0].get("temperature") if forecast else None
            if tomorrow_temp and tomorrow_temp > 90:
                prompt = (
                    f"It's going to be {tomorrow_temp}°F tomorrow. "
                    "Should I create an automation to pre-cool your home in the morning?"
                )
                prompts.append({
                    "prompt": prompt,
                    "context_type": "weather",
                    "metadata": {
                        "temperature": tomorrow_temp,
                        "trigger": "forecast_high_temperature",
                    },
                })

        return prompts

    def _generate_sports_prompts(self, sports_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate prompts based on sports context"""
        prompts = []

        if not sports_data.get("available"):
            return prompts

        upcoming_games = sports_data.get("upcoming_games", [])
        live_games = sports_data.get("live_games", [])

        # Upcoming game prompt
        if upcoming_games:
            next_game = upcoming_games[0]
            game_time = next_game.get("time", "tonight")
            team = next_game.get("team", "your team")

            prompt = (
                f"{team} plays at {game_time} tonight. "
                "Should I create an automation to dim lights and adjust temperature during the game?"
            )
            prompts.append({
                "prompt": prompt,
                "context_type": "sports",
                "metadata": {
                    "game": next_game,
                    "trigger": "upcoming_game",
                },
            })

        # Live game prompt
        if live_games:
            live_game = live_games[0]
            team = live_game.get("team", "your team")

            prompt = (
                f"{team} is playing right now. "
                "Should I create an automation to optimize your viewing experience?"
            )
            prompts.append({
                "prompt": prompt,
                "context_type": "sports",
                "metadata": {
                    "game": live_game,
                    "trigger": "live_game",
                },
            })

        return prompts

    def _generate_energy_prompts(self, energy_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate prompts based on energy/carbon context"""
        prompts = []

        if not energy_data.get("available"):
            return prompts

        current_intensity = energy_data.get("current_intensity", {})
        intensity_value = current_intensity.get("intensity") if current_intensity else None

        # Low carbon intensity prompt
        if intensity_value and intensity_value < 200:
            prompt = (
                "Carbon intensity is low right now. "
                "Should I schedule your EV charging or other energy-intensive tasks for this time?"
            )
            prompts.append({
                "prompt": prompt,
                "context_type": "energy",
                "metadata": {
                    "intensity": intensity_value,
                    "trigger": "low_carbon",
                },
            })

        # High carbon intensity prompt
        elif intensity_value and intensity_value > 400:
            prompt = (
                "Carbon intensity is high right now. "
                "Should I delay energy-intensive tasks until intensity drops?"
            )
            prompts.append({
                "prompt": prompt,
                "context_type": "energy",
                "metadata": {
                    "intensity": intensity_value,
                    "trigger": "high_carbon",
                },
            })

        return prompts

    def _generate_pattern_prompts(self, historical_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate prompts based on historical patterns"""
        prompts = []

        if not historical_data.get("available"):
            return prompts

        patterns = historical_data.get("patterns", [])
        insights = historical_data.get("insights", [])

        # Frequent entity pattern prompt
        frequent_pattern = next(
            (p for p in patterns if p.get("type") == "frequent_entities"), None
        )
        if frequent_pattern:
            entities = frequent_pattern.get("entities", [])
            if entities:
                top_entity = entities[0]
                entity_id = top_entity.get("entity_id", "device")
                count = top_entity.get("count", 0)

                prompt = (
                    f"I noticed you use {entity_id} frequently ({count} times recently). "
                    "Should I create an automation to make this more convenient?"
                )
                prompts.append({
                    "prompt": prompt,
                    "context_type": "historical_pattern",
                    "metadata": {
                        "entity_id": entity_id,
                        "count": count,
                        "trigger": "frequent_usage",
                    },
                })

        # Peak hours pattern prompt
        peak_hours_pattern = next(
            (p for p in patterns if p.get("type") == "peak_hours"), None
        )
        if peak_hours_pattern:
            hours = peak_hours_pattern.get("hours", [])
            if hours:
                top_hour = hours[0]
                hour = top_hour.get("hour", 0)

                prompt = (
                    f"I noticed peak activity around {hour}:00. "
                    "Should I create an automation to prepare your home at that time?"
                )
                prompts.append({
                    "prompt": prompt,
                    "context_type": "historical_pattern",
                    "metadata": {
                        "hour": hour,
                        "trigger": "peak_hours",
                    },
                })

        return prompts

    def _score_prompt(self, prompt_data: dict[str, Any]) -> dict[str, Any]:
        """
        Score prompt quality (0.0 to 1.0).

        Args:
            prompt_data: Prompt dictionary with prompt, context_type, metadata

        Returns:
            Prompt dictionary with added quality_score
        """
        score = 0.5  # Base score

        # Context type scoring
        context_type = prompt_data.get("context_type", "")
        if context_type == "weather":
            score += 0.2
        elif context_type == "sports":
            score += 0.15
        elif context_type == "energy":
            score += 0.2
        elif context_type == "historical_pattern":
            score += 0.15

        # Prompt length scoring (optimal: 50-150 chars)
        prompt_text = prompt_data.get("prompt", "")
        prompt_length = len(prompt_text)
        if 50 <= prompt_length <= 150:
            score += 0.1
        elif prompt_length < 30 or prompt_length > 200:
            score -= 0.1

        # Metadata completeness
        metadata = prompt_data.get("metadata", {})
        if metadata and len(metadata) >= 2:
            score += 0.1

        # Normalize score to 0.0-1.0
        score = max(0.0, min(1.0, score))

        prompt_data["quality_score"] = round(score, 2)
        return prompt_data

    def _load_templates(self) -> dict[str, list[str]]:
        """
        Load prompt templates.

        Returns:
            Dictionary of template categories and templates
        """
        return {
            "weather": [
                "It's going to be {temperature}°F {timeframe}. Should I create an automation to {action}?",
                "Weather conditions suggest {condition}. Should I create an automation to {action}?",
            ],
            "sports": [
                "{team} plays at {time}. Should I create an automation to {action}?",
                "{team} is playing right now. Should I create an automation to {action}?",
            ],
            "energy": [
                "Carbon intensity is {level} right now. Should I {action}?",
                "Energy conditions are optimal. Should I schedule {action}?",
            ],
            "historical_pattern": [
                "I noticed you {pattern}. Should I create an automation to {action}?",
                "Based on your usage patterns, should I create an automation to {action}?",
            ],
        }

