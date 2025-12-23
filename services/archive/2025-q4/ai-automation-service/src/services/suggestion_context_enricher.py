"""
Suggestion Context Enricher - Phase 2 Improvements

Enriches automation suggestions with:
- Energy pricing data for cost-optimization
- Historical usage patterns for personalization
- Weather forecasts for context-aware suggestions
- Carbon intensity for eco-friendly automations
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from ..clients.data_api_client import DataAPIClient
from ..clients.data_enrichment_client import DataEnrichmentClient

logger = logging.getLogger(__name__)


class SuggestionContextEnricher:
    """
    Enriches automation suggestions with contextual data from multiple sources.
    
    Phase 2 improvements:
    - Energy optimization context
    - Historical usage patterns
    - Weather context
    - Carbon intensity data
    """

    def __init__(
        self,
        data_api_client: DataAPIClient | None = None,
        enrichment_client: DataEnrichmentClient | None = None
    ):
        """
        Initialize context enricher.
        
        Args:
            data_api_client: Client for fetching historical events
            enrichment_client: Client for fetching enrichment data (weather, energy, carbon)
        """
        self.data_api_client = data_api_client or DataAPIClient()
        self.enrichment_client = enrichment_client or DataEnrichmentClient()
        
        logger.info("SuggestionContextEnricher initialized")

    async def enrich_suggestion(
        self,
        suggestion: dict[str, Any],
        device_id: str | None = None,
        entity_id: str | None = None
    ) -> dict[str, Any]:
        """
        Enrich a suggestion with contextual data.
        
        Args:
            suggestion: Suggestion dictionary to enrich
            device_id: Optional device ID for historical analysis
            entity_id: Optional entity ID for historical analysis
        
        Returns:
            Enriched suggestion dictionary with additional context fields
        """
        context = {
            'energy': None,
            'historical': None,
            'weather': None,
            'carbon': None
        }

        try:
            # 1. Energy pricing context (for energy-related suggestions)
            if suggestion.get('category') == 'energy' or 'energy' in suggestion.get('title', '').lower():
                context['energy'] = await self._get_energy_context()
            
            # 2. Historical usage context
            if device_id or entity_id:
                context['historical'] = await self._get_historical_context(
                    device_id=device_id,
                    entity_id=entity_id
                )
            
            # 3. Weather context (for weather-responsive suggestions)
            description_lower = suggestion.get('description', '').lower() + ' ' + suggestion.get('title', '').lower()
            if any(keyword in description_lower for keyword in ['weather', 'rain', 'temperature', 'humidity', 'cold', 'hot', 'warm', 'cool', 'frost', 'snow', 'sun']):
                context['weather'] = await self._get_weather_context()
            
            # 4. Carbon intensity context (for eco-friendly suggestions)
            # Check category and description for eco-friendly keywords
            if suggestion.get('category') in ['energy', 'comfort'] or any(keyword in description_lower for keyword in ['green', 'eco', 'carbon', 'renewable', 'sustainable']):
                context['carbon'] = await self._get_carbon_context()
            
            # Add context to suggestion metadata
            if not isinstance(suggestion.get('metadata'), dict):
                suggestion['metadata'] = {}
            
            suggestion['metadata']['context'] = context
            
            # Calculate energy savings if applicable
            if context['energy'] and context['historical']:
                savings = self._calculate_energy_savings(context['energy'], context['historical'], suggestion)
                if savings:
                    suggestion['metadata']['energy_savings'] = savings
                    suggestion['metadata']['estimated_monthly_savings'] = savings.get('monthly_savings_usd', 0)
            
            logger.debug(f"Enriched suggestion {suggestion.get('id')} with context: {list(context.keys())}")
            
        except Exception as e:
            logger.warning(f"Failed to enrich suggestion context: {e}")
            # Continue without context - suggestion still valid
        
        return suggestion

    async def _get_energy_context(self) -> dict[str, Any] | None:
        """Get current energy pricing context."""
        try:
            pricing = await self.enrichment_client.get_electricity_pricing()
            if not pricing:
                return None
            
            return {
                'current_price': pricing.get('current_price'),
                'currency': pricing.get('currency', 'EUR'),
                'peak_period': pricing.get('peak_period', False),
                'cheapest_hours': pricing.get('cheapest_hours', []),
                'provider': pricing.get('provider'),
                'timestamp': pricing.get('timestamp')
            }
        except Exception as e:
            logger.warning(f"Failed to fetch energy context: {e}")
            return None

    async def _get_historical_context(
        self,
        device_id: str | None = None,
        entity_id: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get historical usage context for a device/entity.
        
        Analyzes:
        - Frequency of usage
        - Time-of-day patterns
        - Duration patterns
        - Seasonal variations
        """
        try:
            # Fetch last 30 days of events
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=30)
            
            events_df = await self.data_api_client.fetch_events(
                start_time=start_time,
                end_time=end_time,
                entity_id=entity_id,
                device_id=device_id,
                limit=50000
            )
            
            if events_df.empty:
                return None
            
            # Analyze usage patterns
            usage_stats = self._analyze_usage_patterns(events_df)
            
            return {
                'total_events': len(events_df),
                'usage_frequency': usage_stats.get('frequency'),
                'avg_daily_usage': usage_stats.get('avg_daily'),
                'most_common_hour': usage_stats.get('most_common_hour'),
                'most_common_day': usage_stats.get('most_common_day'),
                'avg_duration_minutes': usage_stats.get('avg_duration'),
                'usage_trend': usage_stats.get('trend'),  # 'increasing', 'decreasing', 'stable'
                'analysis_period_days': 30
            }
        except Exception as e:
            logger.warning(f"Failed to fetch historical context: {e}")
            return None

    def _analyze_usage_patterns(self, events_df: pd.DataFrame) -> dict[str, Any]:
        """Analyze usage patterns from event DataFrame."""
        stats = {}
        
        try:
            # Convert timestamp if needed
            if 'timestamp' in events_df.columns:
                events_df['timestamp'] = pd.to_datetime(events_df['timestamp'])
            elif '_time' in events_df.columns:
                events_df['timestamp'] = pd.to_datetime(events_df['_time'])
            
            # Frequency analysis
            stats['frequency'] = len(events_df) / 30  # events per day average
            stats['avg_daily'] = stats['frequency']
            
            # Time-of-day analysis
            if 'timestamp' in events_df.columns:
                events_df['hour'] = events_df['timestamp'].dt.hour
                hour_counts = events_df['hour'].value_counts()
                if not hour_counts.empty:
                    stats['most_common_hour'] = int(hour_counts.index[0])
                
                # Day of week analysis
                events_df['day_of_week'] = events_df['timestamp'].dt.day_name()
                day_counts = events_df['day_of_week'].value_counts()
                if not day_counts.empty:
                    stats['most_common_day'] = day_counts.index[0]
            
            # Duration analysis (if state changes available)
            if 'old_state' in events_df.columns and 'new_state' in events_df.columns:
                # Simple duration estimate based on state changes
                on_events = events_df[events_df['new_state'].str.lower().isin(['on', 'open', 'active'])]
                stats['avg_duration'] = len(on_events) * 60  # Rough estimate in minutes
            
            # Trend analysis (comparing first half vs second half of period)
            if len(events_df) > 10 and 'timestamp' in events_df.columns:
                sorted_df = events_df.sort_values('timestamp')
                mid_point = len(sorted_df) // 2
                first_half = len(sorted_df[:mid_point])
                second_half = len(sorted_df[mid_point:])
                
                if second_half > first_half * 1.1:
                    stats['trend'] = 'increasing'
                elif first_half > second_half * 1.1:
                    stats['trend'] = 'decreasing'
                else:
                    stats['trend'] = 'stable'
            else:
                stats['trend'] = 'stable'
            
        except Exception as e:
            logger.warning(f"Error analyzing usage patterns: {e}")
        
        return stats

    async def _get_weather_context(self) -> dict[str, Any] | None:
        """Get current weather context."""
        try:
            # Try DataEnrichmentClient first (direct API calls)
            if hasattr(self.enrichment_client, 'get_weather'):
                weather = await self.enrichment_client.get_weather()
            else:
                # Fallback: try to get from InfluxDB via data API
                weather = None
            
            if not weather:
                return None
            
            return {
                'temperature': weather.get('temperature') or weather.get('current_temperature'),
                'humidity': weather.get('humidity'),
                'condition': weather.get('condition'),
                'forecast': weather.get('forecast', {}),
                'timestamp': weather.get('timestamp')
            }
        except Exception as e:
            logger.warning(f"Failed to fetch weather context: {e}")
            return None

    async def _get_carbon_context(self) -> dict[str, Any] | None:
        """Get current carbon intensity context."""
        try:
            # Try DataEnrichmentClient first (direct API calls)
            if hasattr(self.enrichment_client, 'get_carbon_intensity'):
                carbon = await self.enrichment_client.get_carbon_intensity()
            else:
                carbon = None
            
            if not carbon:
                return None
            
            # Handle different response formats
            intensity = carbon.get('intensity') or carbon.get('carbon_intensity') or carbon.get('carbon_intensity_gco2_kwh', 0)
            is_low = carbon.get('is_low_carbon', False)
            if not is_low and intensity:
                # Consider low carbon if intensity < 200 gCO2/kWh
                is_low = intensity < 200
            
            return {
                'current_intensity': intensity,
                'unit': carbon.get('unit', 'gCO2/kWh'),
                'is_low_carbon': is_low,
                'renewable_percentage': carbon.get('renewable_percentage'),
                'forecast': carbon.get('forecast', []),
                'timestamp': carbon.get('timestamp')
            }
        except Exception as e:
            logger.warning(f"Failed to fetch carbon context: {e}")
            return None

    def _calculate_energy_savings(
        self,
        energy_context: dict[str, Any],
        historical_context: dict[str, Any],
        suggestion: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Calculate potential energy savings for a suggestion.
        
        Args:
            energy_context: Energy pricing data
            historical_context: Historical usage patterns
            suggestion: Suggestion dictionary
        
        Returns:
            Dictionary with savings estimates or None
        """
        try:
            # Estimate device power consumption (W) - default values
            device_power_watts = {
                'light': 10,  # LED light
                'switch': 50,  # Generic switch
                'climate': 2000,  # HVAC
                'water_heater': 3000,
                'dishwasher': 1500,
                'default': 100
            }
            
            # Get device type from suggestion
            device_type = 'default'
            if 'light' in suggestion.get('title', '').lower():
                device_type = 'light'
            elif 'climate' in suggestion.get('title', '').lower() or 'heating' in suggestion.get('title', '').lower():
                device_type = 'climate'
            elif 'dishwasher' in suggestion.get('title', '').lower():
                device_type = 'dishwasher'
            
            power_watts = device_power_watts.get(device_type, device_power_watts['default'])
            
            # Calculate savings based on usage frequency and pricing
            avg_daily_usage = historical_context.get('avg_daily_usage', 1)
            current_price = energy_context.get('current_price', 0.20)  # Default €0.20/kWh
            
            # Estimate hours saved per day (if automation reduces usage)
            hours_saved_per_day = avg_daily_usage * 0.5  # Assume 50% reduction
            
            # Calculate daily savings
            daily_kwh_saved = (power_watts / 1000) * hours_saved_per_day
            daily_savings_eur = daily_kwh_saved * current_price
            
            # Monthly savings
            monthly_savings_eur = daily_savings_eur * 30
            
            # Find cheapest hours for optimization
            cheapest_hours = energy_context.get('cheapest_hours', [])
            
            return {
                'daily_savings_kwh': round(daily_kwh_saved, 2),
                'daily_savings_usd': round(daily_savings_eur * 1.1, 2),  # Convert EUR to USD
                'monthly_savings_usd': round(monthly_savings_eur * 1.1, 2),
                'currency': energy_context.get('currency', 'EUR'),
                'device_power_watts': power_watts,
                'cheapest_hours': cheapest_hours[:4],  # Top 4 cheapest hours
                'optimization_potential': 'high' if monthly_savings_eur > 5 else 'medium' if monthly_savings_eur > 1 else 'low'
            }
        except Exception as e:
            logger.warning(f"Failed to calculate energy savings: {e}")
            return None

