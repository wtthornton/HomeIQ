"""
Synthetic External Data Generator (Unified Orchestrator)

Unified orchestrator that coordinates all external data generators:
- Weather
- Carbon Intensity
- Electricity Pricing
- Calendar

NUC-optimized: Coordinates generators efficiently without duplicating data.
Performance target: <50ms overhead, <500ms total per home.

2025 Best Practices:
- Python 3.11+ type hints
- Pydantic models for data validation
- Structured logging
- Memory-efficient (<150MB total for orchestrator + generators)
"""

import logging
from datetime import datetime
from typing import Any

from .synthetic_calendar_generator import SyntheticCalendarGenerator
from .synthetic_carbon_intensity_generator import SyntheticCarbonIntensityGenerator
from .synthetic_electricity_pricing_generator import SyntheticElectricityPricingGenerator
from .synthetic_weather_generator import SyntheticWeatherGenerator

logger = logging.getLogger(__name__)


class SyntheticExternalDataGenerator:
    """
    Unified orchestrator for all external data generators.
    
    Coordinates:
    - Weather generation
    - Carbon intensity generation
    - Electricity pricing generation
    - Calendar generation
    
    NUC-Optimized: Efficient coordination without data duplication.
    """
    
    def __init__(self):
        """Initialize orchestrator with all generators."""
        self.weather_gen = SyntheticWeatherGenerator()
        self.carbon_gen = SyntheticCarbonIntensityGenerator()
        self.pricing_gen = SyntheticElectricityPricingGenerator()
        self.calendar_gen = SyntheticCalendarGenerator()
        logger.debug("SyntheticExternalDataGenerator initialized")
    
    def generate_external_data(
        self,
        home: dict[str, Any],
        start_date: datetime,
        days: int,
        location: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Generate all external data for a synthetic home.
        
        Coordinates all four generators and returns unified external_data structure.
        
        Args:
            home: Home dictionary with metadata
            start_date: Start date/time for external data generation
            days: Number of days to generate
            location: Optional location data (latitude, longitude, region, etc.)
        
        Returns:
            Dictionary with unified external_data structure:
            {
                'weather': list[dict],      # Weather data points
                'carbon_intensity': list[dict],  # Carbon intensity data points
                'pricing': list[dict],      # Electricity pricing data points
                'calendar': list[dict]      # Calendar events
            }
        """
        logger.debug(f"Generating external data for {days} days starting {start_date}")
        
        try:
            # Generate weather data
            weather_data = self.weather_gen.generate_weather(
                home=home,
                start_date=start_date,
                days=days,
                location=location
            )
            logger.debug(f"Generated {len(weather_data)} weather data points")
            
            # Generate carbon intensity data
            carbon_data = self.carbon_gen.generate_carbon_intensity(
                home=home,
                start_date=start_date,
                days=days,
                location=location
            )
            logger.debug(f"Generated {len(carbon_data)} carbon intensity data points")
            
            # Generate electricity pricing data
            pricing_data = self.pricing_gen.generate_pricing(
                home=home,
                start_date=start_date,
                days=days,
                location=location
            )
            logger.debug(f"Generated {len(pricing_data)} pricing data points")
            
            # Generate calendar events
            calendar_data = self.calendar_gen.generate_calendar(
                home=home,
                start_date=start_date,
                days=days
            )
            logger.debug(f"Generated {len(calendar_data)} calendar events")
            
            # Return unified structure
            external_data = {
                'weather': weather_data,
                'carbon_intensity': carbon_data,
                'pricing': pricing_data,
                'calendar': calendar_data
            }
            
            logger.info(
                f"Generated external data: {len(weather_data)} weather, "
                f"{len(carbon_data)} carbon, {len(pricing_data)} pricing, "
                f"{len(calendar_data)} calendar events"
            )
            
            return external_data
            
        except Exception as e:
            logger.error(f"Error generating external data: {e}", exc_info=True)
            raise

