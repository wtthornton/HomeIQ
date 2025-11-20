"""
Contextual Pattern Detection

Detects automation opportunities based on enrichment data (weather, energy, events).

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Stories AI3.5-AI3.7
"""

from .energy_opportunities import EnergyOpportunityDetector
from .event_opportunities import EventOpportunityDetector
from .weather_opportunities import WeatherOpportunityDetector

__all__ = ['WeatherOpportunityDetector', 'EnergyOpportunityDetector', 'EventOpportunityDetector']

