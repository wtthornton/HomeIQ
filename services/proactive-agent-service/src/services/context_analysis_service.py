"""
Context Analysis Service for Proactive Agent Service

Analyzes weather, sports, energy, and historical patterns to provide
context-aware insights for automation suggestions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from ..clients.carbon_intensity_client import CarbonIntensityClient
from ..clients.data_api_client import DataAPIClient
from ..clients.sports_data_client import SportsDataClient
from ..clients.weather_api_client import WeatherAPIClient
from ..config import Settings

logger = logging.getLogger(__name__)

# Global settings instance
_settings = Settings()


class ContextAnalysisService:
    """Service for analyzing context from multiple data sources"""

    def __init__(
        self,
        weather_client: WeatherAPIClient | None = None,
        sports_client: SportsDataClient | None = None,
        carbon_client: CarbonIntensityClient | None = None,
        data_api_client: DataAPIClient | None = None,
    ):
        """
        Initialize Context Analysis Service.

        Args:
            weather_client: Weather API client (optional, creates default if None)
            sports_client: Sports Data client (optional, creates default if None)
            carbon_client: Carbon Intensity client (optional, creates default if None)
            data_api_client: Data API client (optional, creates default if None)
        """
        self.weather_client = weather_client or WeatherAPIClient()
        self.sports_client = sports_client or SportsDataClient()
        self.carbon_client = carbon_client or CarbonIntensityClient(
            data_api_url=_settings.data_api_url
        )
        self.data_api_client = data_api_client or DataAPIClient()
        logger.info("Context Analysis Service initialized")

    async def analyze_all_context(self) -> dict[str, Any]:
        """
        Analyze all available context sources.

        Returns:
            Dictionary containing analysis results from all sources:
            {
                "weather": {...},
                "sports": {...},
                "energy": {...},
                "historical_patterns": {...},
                "summary": {...}
            }
        """
        logger.info("Starting comprehensive context analysis")

        # Analyze all contexts in parallel
        weather_analysis = await self.analyze_weather()
        sports_analysis = await self.analyze_sports()
        energy_analysis = await self.analyze_energy()
        historical_analysis = await self.analyze_historical_patterns()

        # Aggregate and correlate
        summary = self._create_summary(
            weather_analysis, sports_analysis, energy_analysis, historical_analysis
        )

        result = {
            "weather": weather_analysis,
            "sports": sports_analysis,
            "energy": energy_analysis,
            "historical_patterns": historical_analysis,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("Context analysis complete")
        return result

    async def analyze_weather(self) -> dict[str, Any]:
        """
        Analyze weather context.

        Returns:
            Dictionary with weather analysis:
            {
                "current": {...},
                "forecast": {...},
                "trends": {...},
                "insights": [...]
            }
        """
        logger.debug("Analyzing weather context")

        try:
            current_weather = await self.weather_client.get_current_weather()

            if not current_weather:
                logger.warning("Weather data unavailable")
                return {
                    "available": False,
                    "current": None,
                    "forecast": None,
                    "trends": None,
                    "insights": [],
                }

            # Extract key weather metrics
            temperature = current_weather.get("temperature")
            condition = current_weather.get("condition", "unknown")
            humidity = current_weather.get("humidity")
            forecast = current_weather.get("forecast", [])

            # Generate insights
            insights = []
            if temperature:
                if temperature > 85:
                    insights.append("High temperature detected - consider cooling automation")
                elif temperature < 50:
                    insights.append("Low temperature detected - consider heating automation")

            if condition and "rain" in condition.lower():
                insights.append("Rainy conditions - consider window/outdoor device automation")

            # REMOVED: Generic humidity insight that suggests non-existent devices
            # if humidity and humidity > 70:
            #     insights.append("High humidity - consider dehumidifier automation")
            # 
            # Device-specific insights are now generated in AIPromptGenerationService
            # based on actual device inventory. This prevents suggesting devices
            # the user doesn't have. See: device_validation_service.py
            if humidity and humidity > 70:
                insights.append("High humidity detected")  # Generic, no device suggestion
            elif humidity and humidity < 30:
                insights.append("Low humidity detected")  # Generic, no device suggestion

            # Analyze forecast trends
            trends = self._analyze_weather_trends(forecast)

            return {
                "available": True,
                "current": {
                    "temperature": temperature,
                    "condition": condition,
                    "humidity": humidity,
                },
                "forecast": forecast[:5] if forecast else [],  # Next 5 periods
                "trends": trends,
                "insights": insights,
            }

        except Exception as e:
            logger.error(f"Error analyzing weather: {str(e)}", exc_info=True)
            return {
                "available": False,
                "error": str(e),
                "current": None,
                "forecast": None,
                "trends": None,
                "insights": [],
            }

    async def analyze_sports(self) -> dict[str, Any]:
        """
        Analyze sports context.

        Returns:
            Dictionary with sports analysis:
            {
                "live_games": [...],
                "upcoming_games": [...],
                "insights": [...]
            }
        """
        logger.debug("Analyzing sports context")

        try:
            live_games = await self.sports_client.get_live_games()
            upcoming_games = await self.sports_client.get_upcoming_games()

            insights = []
            if live_games:
                insights.append(f"{len(live_games)} game(s) currently live - consider viewing automation")

            if upcoming_games:
                next_game = upcoming_games[0] if upcoming_games else None
                if next_game:
                    insights.append(
                        f"Upcoming game scheduled - consider pre-game automation (lights, temperature)"
                    )
            else:
                # Generate insights even when no games scheduled
                if not live_games:
                    insights.append("No games scheduled - sports automations can be set up for future games")
                    insights.append("Team Tracker sensors detected - automations will trigger automatically when games start")

            return {
                "available": True,
                "live_games": live_games[:10],  # Limit to 10
                "upcoming_games": upcoming_games[:10],  # Limit to 10
                "insights": insights,
            }

        except Exception as e:
            logger.error(f"Error analyzing sports: {str(e)}", exc_info=True)
            return {
                "available": False,
                "error": str(e),
                "live_games": [],
                "upcoming_games": [],
                "insights": [],
            }

    async def analyze_energy(self) -> dict[str, Any]:
        """
        Analyze energy/carbon intensity context.

        Returns:
            Dictionary with energy analysis:
            {
                "current_intensity": {...},
                "trends": {...},
                "insights": [...]
            }
        """
        logger.debug("Analyzing energy context")

        try:
            current_intensity = await self.carbon_client.get_current_intensity()
            trends_data = await self.carbon_client.get_trends()

            insights = []
            if current_intensity:
                intensity_value = current_intensity.get("intensity", 0)
                if intensity_value and intensity_value < 200:
                    insights.append("Low carbon intensity - good time for energy-intensive tasks")
                elif intensity_value and intensity_value > 400:
                    insights.append("High carbon intensity - consider delaying energy-intensive tasks")
                
                # Add trend-based insights
                if trends_data:
                    trend = trends_data.get("trend", "stable")
                    if trend == "increasing":
                        insights.append("Carbon intensity trending upward - schedule tasks soon")
                    elif trend == "decreasing":
                        insights.append("Carbon intensity trending downward - good time for energy tasks")

            # Format trends data
            trends = None
            if trends_data:
                trends = {
                    "average_24h": trends_data.get("average_24h"),
                    "min_24h": trends_data.get("min_24h"),
                    "max_24h": trends_data.get("max_24h"),
                    "trend": trends_data.get("trend", "stable"),
                }

            return {
                "available": current_intensity is not None,
                "current_intensity": current_intensity,
                "trends": trends,
                "insights": insights,
            }

        except Exception as e:
            logger.error(f"Error analyzing energy: {str(e)}", exc_info=True)
            return {
                "available": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "current_intensity": None,
                "trends": None,
                "insights": [],
            }

    async def analyze_historical_patterns(
        self, days_back: int = 7, limit: int = 100
    ) -> dict[str, Any]:
        """
        Analyze historical event patterns.

        Args:
            days_back: Number of days to look back (default: 7)
            limit: Maximum number of events to analyze (default: 100)

        Returns:
            Dictionary with historical pattern analysis:
            {
                "events": [...],
                "patterns": [...],
                "insights": [...]
            }
        """
        logger.debug(f"Analyzing historical patterns (last {days_back} days)")

        try:
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days_back)

            # Fetch recent events
            events = await self.data_api_client.get_events(
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                limit=limit,
            )

            if not events:
                logger.debug(f"No historical events found in last {days_back} days")
                return {
                    "available": True,  # Data source is available, just no events
                    "events": [],
                    "patterns": [],
                    "insights": [
                        f"No events found in last {days_back} days - patterns will appear as usage increases"
                    ],
                    "query_info": {
                        "days_back": days_back,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                    },
                }

            # Analyze patterns
            patterns = self._detect_patterns(events)
            insights = self._generate_pattern_insights(patterns, events)

            return {
                "available": True,
                "events_count": len(events),
                "events": events[:20],  # Return sample of events
                "patterns": patterns,
                "insights": insights,
                "query_info": {  # Include query info even when events found
                    "days_back": days_back,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Error analyzing historical patterns: {str(e)}", exc_info=True)
            return {
                "available": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "events": [],
                "patterns": [],
                "insights": [f"Unable to fetch historical data: {str(e)}"],
            }

    def _analyze_weather_trends(self, forecast: list[dict[str, Any]]) -> dict[str, Any] | None:
        """
        Analyze weather forecast trends.

        Args:
            forecast: List of forecast periods

        Returns:
            Dictionary with trend analysis or None
        """
        if not forecast or len(forecast) < 2:
            return None

        try:
            temperatures = [
                period.get("temperature")
                for period in forecast
                if period.get("temperature") is not None
            ]

            if not temperatures:
                return None

            avg_temp = sum(temperatures) / len(temperatures)
            max_temp = max(temperatures)
            min_temp = min(temperatures)
            trend = "increasing" if temperatures[-1] > temperatures[0] else "decreasing"

            return {
                "average_temperature": round(avg_temp, 1),
                "max_temperature": max_temp,
                "min_temperature": min_temp,
                "trend": trend,
                "periods_analyzed": len(temperatures),
            }

        except Exception as e:
            logger.warning(f"Error analyzing weather trends: {str(e)}")
            return None

    def _detect_patterns(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Detect patterns in historical events.

        Args:
            events: List of historical events

        Returns:
            List of detected patterns
        """
        if not events:
            return []

        patterns = []

        # Group events by entity_id
        entity_groups: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            entity_id = event.get("entity_id", "unknown")
            if entity_id not in entity_groups:
                entity_groups[entity_id] = []
            entity_groups[entity_id].append(event)

        # Detect frequent entities
        frequent_entities = [
            {"entity_id": entity_id, "count": len(events_list)}
            for entity_id, events_list in entity_groups.items()
            if len(events_list) >= 3  # At least 3 occurrences
        ]
        frequent_entities.sort(key=lambda x: x["count"], reverse=True)

        if frequent_entities:
            patterns.append(
                {
                    "type": "frequent_entities",
                    "entities": frequent_entities[:10],  # Top 10
                    "description": f"Most frequently used entities in last period",
                }
            )

        # Detect time-based patterns (morning, evening, etc.)
        time_patterns = self._detect_time_patterns(events)
        if time_patterns:
            patterns.extend(time_patterns)

        return patterns

    def _detect_time_patterns(
        self, events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Detect time-based patterns in events.

        Args:
            events: List of historical events

        Returns:
            List of time-based patterns
        """
        if not events:
            return []

        patterns = []

        # Group by hour of day
        hour_groups: dict[int, int] = {}
        for event in events:
            try:
                timestamp_str = event.get("timestamp") or event.get("time")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    hour = timestamp.hour
                    hour_groups[hour] = hour_groups.get(hour, 0) + 1
            except (ValueError, AttributeError):
                continue

        if hour_groups:
            peak_hours = sorted(hour_groups.items(), key=lambda x: x[1], reverse=True)[:3]
            patterns.append(
                {
                    "type": "peak_hours",
                    "hours": [{"hour": hour, "count": count} for hour, count in peak_hours],
                    "description": "Peak activity hours",
                }
            )

        return patterns

    def _generate_pattern_insights(
        self, patterns: list[dict[str, Any]], events: list[dict[str, Any]]
    ) -> list[str]:
        """
        Generate insights from detected patterns.

        Args:
            patterns: List of detected patterns
            events: List of historical events

        Returns:
            List of insight strings
        """
        insights = []

        if not patterns:
            return insights

        # Frequent entities insight
        frequent_pattern = next(
            (p for p in patterns if p.get("type") == "frequent_entities"), None
        )
        if frequent_pattern:
            entities = frequent_pattern.get("entities", [])
            if entities:
                top_entity = entities[0]
                insights.append(
                    f"Most active entity: {top_entity.get('entity_id')} "
                    f"({top_entity.get('count')} events)"
                )

        # Peak hours insight
        peak_hours_pattern = next(
            (p for p in patterns if p.get("type") == "peak_hours"), None
        )
        if peak_hours_pattern:
            hours = peak_hours_pattern.get("hours", [])
            if hours:
                top_hour = hours[0]
                insights.append(
                    f"Peak activity hour: {top_hour.get('hour')}:00 "
                    f"({top_hour.get('count')} events)"
                )

        return insights

    def _create_summary(
        self,
        weather: dict[str, Any],
        sports: dict[str, Any],
        energy: dict[str, Any],
        historical: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create aggregated summary of all context analyses.

        Args:
            weather: Weather analysis results
            sports: Sports analysis results
            energy: Energy analysis results
            historical: Historical pattern analysis results

        Returns:
            Summary dictionary
        """
        available_sources = sum(
            [
                weather.get("available", False),
                sports.get("available", False),
                energy.get("available", False),
                historical.get("available", False),
            ]
        )

        all_insights = []
        all_insights.extend(weather.get("insights", []))
        all_insights.extend(sports.get("insights", []))
        all_insights.extend(energy.get("insights", []))
        all_insights.extend(historical.get("insights", []))

        return {
            "available_sources": available_sources,
            "total_sources": 4,
            "total_insights": len(all_insights),
            "insights": all_insights,
            "has_weather": weather.get("available", False),
            "has_sports": sports.get("available", False),
            "has_energy": energy.get("available", False),
            "has_historical": historical.get("available", False),
        }

    async def close(self):
        """Close all client connections"""
        await self.weather_client.close()
        await self.sports_client.close()
        await self.carbon_client.close()
        await self.data_api_client.close()
        logger.debug("Context Analysis Service closed")

