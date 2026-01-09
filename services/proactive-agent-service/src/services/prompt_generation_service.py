"""
Prompt Generation Service for Proactive Agent Service

Generates context-aware, natural language prompts for the HA AI Agent Service.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def celsius_to_fahrenheit(celsius: float) -> int:
    """
    Convert Celsius to Fahrenheit and round to whole number.
    
    Args:
        celsius: Temperature in Celsius
        
    Returns:
        Temperature in Fahrenheit as whole number
    """
    fahrenheit = (celsius * 9 / 5) + 32
    return round(fahrenheit)


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
        temperature_celsius = current.get("temperature")
        condition = current.get("condition", "").lower()
        forecast = weather_data.get("forecast", [])

        # Convert Celsius to Fahrenheit and round to whole number
        if temperature_celsius is not None:
            temperature_f = celsius_to_fahrenheit(temperature_celsius)
        else:
            temperature_f = None

        # High temperature prompt (85°F = 29.4°C, so check against ~29°C)
        if temperature_celsius is not None and temperature_celsius > 29:
            prompt = (
                f"Today's high is {temperature_f}F. "
                "Want me to set up pre-cooling before you get home?"
            )
            prompts.append({
                "prompt": prompt,
                "context_type": "weather",
                "metadata": {
                    "temperature_celsius": temperature_celsius,
                    "temperature_fahrenheit": temperature_f,
                    "trigger": "high_temperature",
                },
            })

        # Low temperature prompt (50°F = 10°C, so check against ~10°C)
        elif temperature_celsius is not None and temperature_celsius < 10:
            prompt = (
                f"It's cold out there - only {temperature_f}F. "
                "Should I warm up the house before you arrive?"
            )
            prompts.append({
                "prompt": prompt,
                "context_type": "weather",
                "metadata": {
                    "temperature_celsius": temperature_celsius,
                    "temperature_fahrenheit": temperature_f,
                    "trigger": "low_temperature",
                },
            })

        # Rainy weather prompt
        if "rain" in condition or "rainy" in condition:
            prompt = (
                "Rain is expected today. "
                "Want me to close windows and adjust outdoor devices automatically?"
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
            tomorrow_temp_celsius = forecast[0].get("temperature") if forecast else None
            # 90°F = 32.2°C, so check against ~32°C
            if tomorrow_temp_celsius is not None and tomorrow_temp_celsius > 32:
                tomorrow_temp_f = celsius_to_fahrenheit(tomorrow_temp_celsius)
                prompt = (
                    f"Tomorrow will hit {tomorrow_temp_f}F. "
                    "Should I schedule morning pre-cooling?"
                )
                prompts.append({
                    "prompt": prompt,
                    "context_type": "weather",
                    "metadata": {
                        "temperature_celsius": tomorrow_temp_celsius,
                        "temperature_fahrenheit": tomorrow_temp_f,
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
            team = next_game.get("team", "Your team")

            prompt = (
                f"{team} plays at {game_time}. "
                "Want me to set game-day lighting and temperature?"
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
            team = live_game.get("team", "Your team")

            prompt = (
                f"{team} is playing now! "
                "Should I switch to game mode?"
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
                "Grid energy is clean right now. "
                "Good time to charge your EV or run heavy appliances."
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
                "Grid carbon is high. "
                "Want me to delay energy-heavy tasks until it drops?"
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
                
                # Make entity_id more readable (remove domain prefix if present)
                display_name = entity_id.split(".")[-1].replace("_", " ").title()

                prompt = (
                    f"You've used {display_name} {count} times this week. "
                    "Want me to automate it?"
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
                
                # Format hour nicely (e.g., "7 AM" or "8 PM")
                if hour == 0:
                    time_str = "midnight"
                elif hour == 12:
                    time_str = "noon"
                elif hour < 12:
                    time_str = f"{hour} AM"
                else:
                    time_str = f"{hour - 12} PM"

                prompt = (
                    f"Your home is busiest around {time_str}. "
                    "Should I prepare things automatically at that time?"
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
                "Today's high is {temperature}F. Want me to set up {action}?",
                "It's {condition} outside. Should I {action}?",
            ],
            "sports": [
                "{team} plays at {time}. Want game-day settings?",
                "{team} is on now! Switch to game mode?",
            ],
            "energy": [
                "Grid is clean right now. Good time for {action}.",
                "Carbon is high. Delay {action} until later?",
            ],
            "historical_pattern": [
                "You use {device} often. Automate it?",
                "Home is busiest at {time}. Prepare automatically?",
            ],
        }

