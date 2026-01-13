"""
Energy Savings Calculator Service

Phase 3.2: Energy savings scoring and prioritization for synergies.

Calculates energy savings scores, estimates kWh and cost savings,
and prioritizes synergies that save energy and reduce costs.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Default device power consumption (watts) - estimates
DEFAULT_DEVICE_POWER: dict[str, float] = {
    'climate': 3500.0,  # HVAC system (varies widely)
    'water_heater': 4500.0,  # Water heater
    'dryer': 3000.0,  # Clothes dryer
    'washer': 500.0,  # Washing machine
    'dishwasher': 1200.0,  # Dishwasher
    'ev_charger': 7200.0,  # EV charger (Level 2)
    'light': 10.0,  # LED light (average)
    'switch': 5.0,  # Switch-controlled device (average)
    'fan': 50.0,  # Ceiling fan
    'media_player': 100.0,  # TV/media player
}

# Default electricity price (USD per kWh) - can be overridden
DEFAULT_ELECTRICITY_PRICE = 0.12  # $0.12/kWh average


class EnergySavingsCalculator:
    """
    Calculate energy savings for synergies.
    
    Estimates kWh and cost savings based on device types, usage patterns,
    and energy scheduling opportunities.
    
    Attributes:
        electricity_price: Electricity price per kWh (default: $0.12)
        device_power: Dictionary mapping device domains to power consumption (watts)
    """
    
    def __init__(
        self,
        electricity_price: float = DEFAULT_ELECTRICITY_PRICE,
        device_power: Optional[dict[str, float]] = None
    ):
        """
        Initialize energy savings calculator.
        
        Args:
            electricity_price: Electricity price per kWh (default: $0.12)
            device_power: Optional dictionary mapping domains to power (watts)
        """
        self.electricity_price = electricity_price
        self.device_power = device_power or DEFAULT_DEVICE_POWER.copy()
    
    def calculate_energy_savings(
        self,
        synergy: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Calculate energy savings score for a synergy.
        
        Args:
            synergy: Synergy dictionary with devices and context_metadata
            
        Returns:
            Dictionary with:
            - energy_savings_score: float (0.0-1.0)
            - estimated_kwh_savings: float (optional)
            - estimated_cost_savings: float (optional)
            - savings_period: str ('daily', 'monthly', 'yearly')
            - rationale: str (explanation)
        """
        devices = synergy.get('devices', synergy.get('device_ids', []))
        synergy_type = synergy.get('synergy_type', '')
        context_metadata = synergy.get('context_metadata', {})
        
        if not devices:
            return {
                'energy_savings_score': 0.0,
                'rationale': 'No devices in synergy'
            }
        
        # Extract device domains
        device_domains = []
        for device in devices:
            if isinstance(device, str):
                domain = device.split('.')[0] if '.' in device else device
                device_domains.append(domain)
            elif isinstance(device, dict):
                device_id = device.get('entity_id', '')
                domain = device_id.split('.')[0] if '.' in device_id else ''
                device_domains.append(domain)
        
        # Calculate base energy savings score
        energy_score = 0.0
        kwh_savings = 0.0
        cost_savings = 0.0
        savings_period = 'monthly'
        rationale_parts = []
        
        # Pattern 1: Energy scheduling (off-peak scheduling)
        if synergy_type == 'energy_context' or context_metadata.get('context_type') == 'energy_scheduling':
            # Estimate savings from scheduling high-power devices during off-peak hours
            high_power_domains = ['climate', 'water_heater', 'dryer', 'washer', 'dishwasher', 'ev_charger']
            for domain in device_domains:
                if domain in high_power_domains:
                    power_watts = self.device_power.get(domain, 1000.0)
                    # Assume 2 hours/day shift to off-peak (20% price difference)
                    daily_kwh = (power_watts / 1000.0) * 2.0  # 2 hours
                    price_difference = 0.20  # 20% savings
                    daily_savings_kwh = daily_kwh * price_difference
                    monthly_savings_kwh = daily_savings_kwh * 30
                    monthly_cost_savings = monthly_savings_kwh * self.electricity_price
                    
                    kwh_savings += monthly_savings_kwh
                    cost_savings += monthly_cost_savings
                    energy_score += 0.4
                    rationale_parts.append(f'{domain} scheduling: ~${monthly_cost_savings:.2f}/month')
        
        # Pattern 2: Carbon intensity optimization
        if synergy_type == 'carbon_context' or context_metadata.get('context_type') == 'carbon_scheduling':
            # Estimate carbon savings (similar to energy scheduling)
            high_power_domains = ['climate', 'water_heater', 'dryer', 'washer', 'dishwasher', 'ev_charger']
            for domain in device_domains:
                if domain in high_power_domains:
                    power_watts = self.device_power.get(domain, 1000.0)
                    daily_kwh = (power_watts / 1000.0) * 2.0
                    monthly_savings_kwh = daily_kwh * 30
                    monthly_cost_savings = monthly_savings_kwh * self.electricity_price
                    
                    kwh_savings += monthly_savings_kwh
                    cost_savings += monthly_cost_savings
                    energy_score += 0.3
                    rationale_parts.append(f'{domain} carbon optimization: ~${monthly_cost_savings:.2f}/month')
        
        # Pattern 3: Lighting optimization (turn off when not needed)
        if 'light' in [d.lower() for d in device_domains]:
            # Motion-to-light, door-to-light, occupancy-to-light reduce unnecessary lighting
            if any(pattern in synergy_type for pattern in ['motion', 'door', 'occupancy']):
                # Estimate 1 hour/day savings per light
                power_watts = self.device_power.get('light', 10.0)
                daily_kwh = (power_watts / 1000.0) * 1.0  # 1 hour/day
                monthly_savings_kwh = daily_kwh * 30
                monthly_cost_savings = monthly_savings_kwh * self.electricity_price
                
                kwh_savings += monthly_savings_kwh
                cost_savings += monthly_cost_savings
                energy_score += 0.2
                rationale_parts.append(f'lighting optimization: ~${monthly_cost_savings:.2f}/month')
        
        # Pattern 4: Climate optimization (weather-based, window-based)
        if 'climate' in [d.lower() for d in device_domains]:
            if synergy_type == 'weather_context' or 'window' in synergy_type:
                # Weather-based climate control can save 10-15% (conservative estimate: 10%)
                power_watts = self.device_power.get('climate', 3500.0)
                # Assume 6 hours/day average usage
                daily_kwh = (power_watts / 1000.0) * 6.0
                savings_percentage = 0.10  # 10% savings
                daily_savings_kwh = daily_kwh * savings_percentage
                monthly_savings_kwh = daily_savings_kwh * 30
                monthly_cost_savings = monthly_savings_kwh * self.electricity_price
                
                kwh_savings += monthly_savings_kwh
                cost_savings += monthly_cost_savings
                energy_score += 0.3
                rationale_parts.append(f'climate optimization: ~${monthly_cost_savings:.2f}/month')
        
        # Normalize energy score to 0.0-1.0
        energy_score = min(1.0, energy_score)
        
        # Build rationale
        if rationale_parts:
            rationale = 'Energy savings: ' + ', '.join(rationale_parts)
        else:
            rationale = 'Limited energy savings potential'
        
        return {
            'energy_savings_score': round(energy_score, 4),
            'estimated_kwh_savings': round(kwh_savings, 2) if kwh_savings > 0 else None,
            'estimated_cost_savings': round(cost_savings, 2) if cost_savings > 0 else None,
            'savings_period': savings_period,
            'rationale': rationale
        }
    
    def estimate_kwh_savings(
        self,
        synergy: dict[str, Any]
    ) -> float:
        """
        Estimate kWh savings for a synergy.
        
        Args:
            synergy: Synergy dictionary
            
        Returns:
            Estimated kWh savings (monthly)
        """
        savings = self.calculate_energy_savings(synergy)
        return savings.get('estimated_kwh_savings', 0.0) or 0.0
    
    def estimate_cost_savings(
        self,
        synergy: dict[str, Any]
    ) -> float:
        """
        Estimate cost savings for a synergy.
        
        Args:
            synergy: Synergy dictionary
            
        Returns:
            Estimated cost savings in USD (monthly)
        """
        savings = self.calculate_energy_savings(synergy)
        return savings.get('estimated_cost_savings', 0.0) or 0.0
