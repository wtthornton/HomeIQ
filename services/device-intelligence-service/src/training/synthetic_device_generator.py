"""
Synthetic Device Data Generator

Generate synthetic device health metrics using template-based approach for training Device Intelligence models.
Follows synthetic_home_generator.py pattern: template-based, no LLM/API calls, zero cost, fast generation.

Epic 46, Story 46.1: Synthetic Device Data Generator
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SyntheticDeviceGenerator:
    """
    Generate synthetic device health metrics using template-based approach.
    
    Uses predefined distributions and templates to generate realistic device metrics
    without LLM/API calls. Fast generation (<30 seconds for 1000 samples).
    """

    # Device type distribution (for diversity)
    DEVICE_TYPE_DISTRIBUTION = {
        'sensor': 30,          # Motion, temperature, humidity sensors
        'switch': 20,          # Light switches, outlets
        'light': 15,          # Smart bulbs, dimmers
        'climate': 10,        # Thermostats, HVAC
        'security': 10,       # Door sensors, cameras
        'battery_powered': 8,  # Battery-powered sensors, locks
        'media': 5,           # Media players
        'vacuum': 2           # Robot vacuums
    }

    # Home type device patterns (affects device distribution and characteristics)
    HOME_TYPE_DEVICE_PATTERNS = {
        'single_family_house': {
            'device_count_range': (30, 60),      # More devices
            'climate_ratio': 0.15,               # More HVAC systems
            'security_ratio': 0.12,              # More security devices
            'outdoor_devices': True,             # Yard sensors, outdoor lights
            'media_ratio': 0.08,                 # Multiple media zones
            'vacuum_ratio': 0.05                 # Robot vacuums common
        },
        'apartment': {
            'device_count_range': (10, 25),      # Fewer devices
            'climate_ratio': 0.20,               # Higher (central HVAC)
            'security_ratio': 0.15,              # More security (urban)
            'outdoor_devices': False,
            'media_ratio': 0.10,                 # Single media setup
            'vacuum_ratio': 0.02                 # Less common
        },
        'condo': {
            'device_count_range': (15, 35),      # Medium devices
            'climate_ratio': 0.18,                # Central HVAC
            'security_ratio': 0.13,              # Good security
            'outdoor_devices': False,
            'media_ratio': 0.12,
            'vacuum_ratio': 0.03
        },
        'townhouse': {
            'device_count_range': (20, 45),      # Medium-large
            'climate_ratio': 0.16,               # Multiple zones
            'security_ratio': 0.12,              # Good security
            'outdoor_devices': True,             # Small yard
            'media_ratio': 0.10,
            'vacuum_ratio': 0.04
        },
        'cottage': {
            'device_count_range': (15, 30),      # Smaller setup
            'climate_ratio': 0.12,               # Basic HVAC
            'security_ratio': 0.10,              # Basic security
            'outdoor_devices': True,             # Garden sensors
            'media_ratio': 0.06,
            'vacuum_ratio': 0.01                 # Rare
        },
        'studio': {
            'device_count_range': (5, 15),       # Minimal
            'climate_ratio': 0.10,               # Single zone
            'security_ratio': 0.08,              # Basic
            'outdoor_devices': False,
            'media_ratio': 0.15,                 # Higher (entertainment focus)
            'vacuum_ratio': 0.01                 # Rare
        },
        'multi_story': {
            'device_count_range': (40, 80),      # Large setup
            'climate_ratio': 0.18,                # Multi-zone HVAC
            'security_ratio': 0.14,              # Comprehensive
            'outdoor_devices': True,
            'media_ratio': 0.12,                 # Multiple zones
            'vacuum_ratio': 0.06                 # Multiple vacuums
        },
        'ranch_house': {
            'device_count_range': (25, 50),      # Medium-large
            'climate_ratio': 0.14,               # Single-level HVAC
            'security_ratio': 0.11,              # Good coverage
            'outdoor_devices': True,
            'media_ratio': 0.09,
            'vacuum_ratio': 0.04
        }
    }

    # Device type characteristics (base patterns)
    DEVICE_CHARACTERISTICS = {
        'sensor': {
            'response_time': (50, 200),      # ms - fast sensors
            'error_rate': (0.0, 0.05),       # Low error rate
            'battery_level': (20, 100),       # Battery-powered
            'signal_strength': (-70, -40),    # WiFi/Zigbee
            'usage_frequency': (0.3, 0.8),   # Moderate usage
            'temperature': (18, 28),          # Room temperature
            'humidity': (30, 70),            # Normal humidity
            'uptime_hours': (100, 2000),     # Hours
            'restart_count': (0, 5),         # Low restarts
            'connection_drops': (0, 2),      # Stable
            'data_transfer_rate': (100, 500) # KB/s
        },
        'switch': {
            'response_time': (100, 300),
            'error_rate': (0.0, 0.03),
            'battery_level': (100, 100),      # Wired
            'signal_strength': (-65, -35),
            'usage_frequency': (0.2, 0.6),
            'temperature': (20, 26),
            'humidity': (40, 60),
            'uptime_hours': (500, 3000),
            'restart_count': (0, 3),
            'connection_drops': (0, 1),
            'data_transfer_rate': (200, 800)
        },
        'light': {
            'response_time': (150, 400),
            'error_rate': (0.0, 0.05),
            'battery_level': (100, 100),      # Wired
            'signal_strength': (-70, -40),
            'usage_frequency': (0.4, 0.9),   # High usage
            'temperature': (22, 28),          # Can get warm
            'humidity': (30, 60),
            'uptime_hours': (300, 2500),
            'restart_count': (0, 5),
            'connection_drops': (0, 3),
            'data_transfer_rate': (150, 600)
        },
        'climate': {
            'response_time': (200, 500),
            'error_rate': (0.0, 0.08),
            'battery_level': (100, 100),      # Wired
            'signal_strength': (-65, -35),
            'usage_frequency': (0.5, 0.95),  # Very high usage
            'temperature': (18, 25),          # Controlled temp
            'humidity': (30, 60),
            'uptime_hours': (1000, 5000),
            'restart_count': (0, 2),
            'connection_drops': (0, 1),
            'data_transfer_rate': (300, 1000)
        },
        'security': {
            'response_time': (80, 250),
            'error_rate': (0.0, 0.10),       # Higher error tolerance
            'battery_level': (30, 100),        # Battery-powered
            'signal_strength': (-75, -45),
            'usage_frequency': (0.1, 0.5),   # Event-driven
            'temperature': (15, 30),
            'humidity': (20, 80),
            'uptime_hours': (200, 1800),
            'restart_count': (0, 8),
            'connection_drops': (0, 5),      # More drops
            'data_transfer_rate': (50, 300)
        },
        'battery_powered': {
            'response_time': (100, 300),
            'error_rate': (0.0, 0.06),
            'battery_level': (10, 100),       # Variable battery
            'signal_strength': (-80, -50),
            'usage_frequency': (0.2, 0.7),
            'temperature': (18, 28),
            'humidity': (30, 70),
            'uptime_hours': (50, 1000),
            'restart_count': (0, 10),
            'connection_drops': (0, 4),
            'data_transfer_rate': (100, 400)
        },
        'media': {
            'response_time': (200, 600),
            'error_rate': (0.0, 0.05),
            'battery_level': (100, 100),      # Wired
            'signal_strength': (-60, -30),
            'usage_frequency': (0.3, 0.8),
            'temperature': (22, 30),           # Can get warm
            'humidity': (30, 60),
            'uptime_hours': (400, 2000),
            'restart_count': (0, 6),
            'connection_drops': (0, 2),
            'data_transfer_rate': (500, 2000) # High bandwidth
        },
        'vacuum': {
            'response_time': (300, 800),
            'error_rate': (0.0, 0.10),
            'battery_level': (20, 100),       # Battery-powered
            'signal_strength': (-70, -40),
            'usage_frequency': (0.1, 0.4),   # Periodic usage
            'temperature': (20, 28),
            'humidity': (40, 70),
            'uptime_hours': (100, 800),
            'restart_count': (0, 15),         # More restarts
            'connection_drops': (0, 6),
            'data_transfer_rate': (200, 800)
        }
    }

    # Failure scenario patterns
    FAILURE_SCENARIOS = {
        'progressive': {
            'description': 'Gradual degradation over time',
            'error_rate_multiplier': (1.0, 5.0),  # Increases over time
            'response_time_multiplier': (1.0, 3.0),
            'battery_depletion_rate': 0.1,  # 10% per day
            'connection_drops_increase': (0, 5)
        },
        'sudden': {
            'description': 'Immediate failure after normal operation',
            'error_rate_multiplier': (10.0, 20.0),
            'response_time_multiplier': (5.0, 10.0),
            'battery_depletion_rate': 0.0,
            'connection_drops_increase': (10, 20)
        },
        'intermittent': {
            'description': 'Unstable behavior patterns',
            'error_rate_multiplier': (2.0, 8.0),  # Varies
            'response_time_multiplier': (1.5, 4.0),
            'battery_depletion_rate': 0.05,
            'connection_drops_increase': (3, 10)
        },
        'battery_depletion': {
            'description': 'Battery depletion leading to failures',
            'error_rate_multiplier': (1.0, 3.0),
            'response_time_multiplier': (1.0, 2.0),
            'battery_depletion_rate': 0.2,  # 20% per day
            'connection_drops_increase': (0, 3)
        },
        'network_issues': {
            'description': 'Network connectivity problems',
            'error_rate_multiplier': (1.5, 4.0),
            'response_time_multiplier': (2.0, 5.0),
            'battery_depletion_rate': 0.0,
            'connection_drops_increase': (5, 15)
        }
    }

    def __init__(self, random_seed: int | None = None, home_type: str | None = None):
        """
        Initialize synthetic device generator.
        
        Args:
            random_seed: Optional random seed for reproducibility
            home_type: Optional home type to influence device distribution
                      (single_family_house, apartment, condo, townhouse, cottage, studio, multi_story, ranch_house)
        """
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)
        
        self.home_type = home_type
        if home_type and home_type not in self.HOME_TYPE_DEVICE_PATTERNS:
            logger.warning(f"Unknown home type '{home_type}', using default distribution")
            self.home_type = None
        
        logger.info(f"SyntheticDeviceGenerator initialized (template-based generation, home_type={home_type or 'default'})")

    def generate_training_data(
        self,
        count: int = 1000,
        days: int = 180,
        failure_rate: float = 0.15,
        device_types: list[str] | None = None,
        home_type: str | None = None,
        reference_date: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate synthetic device training data with enhanced temporal patterns (2025).
        
        Args:
            count: Number of device samples to generate
            days: Number of days of historical data to simulate
            failure_rate: Percentage of devices with failure scenarios (0.0-1.0)
            device_types: Optional list of device types to generate (default: all)
            home_type: Optional home type to influence device distribution (overrides instance home_type)
            reference_date: Optional reference date for temporal patterns (2025: timezone-aware, defaults to now)
        
        Returns:
            List of device metric dictionaries compatible with training pipeline
        """
        # Use parameter home_type if provided, otherwise use instance home_type
        effective_home_type = home_type or self.home_type
        
        # Use current date if not provided (2025: timezone-aware)
        if reference_date is None:
            reference_date = datetime.now(timezone.utc)
        elif reference_date.tzinfo is None:
            reference_date = reference_date.replace(tzinfo=timezone.utc)
        
        logger.info(f"Generating {count} synthetic device samples (template-based, {days} days, home_type={effective_home_type or 'default'}, reference_date={reference_date.date()})")
        
        training_samples = []
        failure_count = int(count * failure_rate)
        normal_count = count - failure_count
        
        # Determine device types to use
        if device_types is None:
            device_types = list(self.DEVICE_TYPE_DISTRIBUTION.keys())
        
        # Adjust device type distribution based on home type
        if effective_home_type and effective_home_type in self.HOME_TYPE_DEVICE_PATTERNS:
            device_types = self._adjust_device_types_for_home_type(device_types, effective_home_type)
        
        # Generate normal devices
        for i in range(normal_count):
            device_type = self._select_device_type(device_types, effective_home_type)
            device_id = f"synthetic_device_{i+1:04d}"
            
            sample = self._generate_device_sample(
                device_id=device_id,
                device_type=device_type,
                days=days,
                failure_scenario=None,
                home_type=effective_home_type,
                reference_date=reference_date
            )
            training_samples.append(sample)
        
        # Generate devices with failure scenarios
        failure_scenarios = list(self.FAILURE_SCENARIOS.keys())
        for i in range(failure_count):
            device_type = self._select_device_type(device_types, effective_home_type)
            device_id = f"synthetic_device_{normal_count+i+1:04d}"
            failure_scenario = random.choice(failure_scenarios)
            
            sample = self._generate_device_sample(
                device_id=device_id,
                device_type=device_type,
                days=days,
                failure_scenario=failure_scenario,
                home_type=effective_home_type,
                reference_date=reference_date
            )
            training_samples.append(sample)
        
        logger.info(f"Generated {len(training_samples)} synthetic device samples")
        logger.info(f"- Normal devices: {normal_count}")
        logger.info(f"- Failure scenarios: {failure_count}")
        
        return training_samples

    def _adjust_device_types_for_home_type(self, device_types: list[str], home_type: str) -> list[str]:
        """Adjust device type distribution based on home type patterns."""
        patterns = self.HOME_TYPE_DEVICE_PATTERNS[home_type]
        
        # Create adjusted distribution
        adjusted_distribution = self.DEVICE_TYPE_DISTRIBUTION.copy()
        
        # Adjust ratios based on home type
        if 'climate_ratio' in patterns:
            # Increase climate devices for homes with higher HVAC usage
            adjusted_distribution['climate'] = int(adjusted_distribution['climate'] * (1 + patterns['climate_ratio']))
        
        if 'security_ratio' in patterns:
            adjusted_distribution['security'] = int(adjusted_distribution['security'] * (1 + patterns['security_ratio']))
        
        if 'media_ratio' in patterns:
            adjusted_distribution['media'] = int(adjusted_distribution['media'] * (1 + patterns['media_ratio']))
        
        if 'vacuum_ratio' in patterns:
            adjusted_distribution['vacuum'] = int(adjusted_distribution['vacuum'] * (1 + patterns['vacuum_ratio']))
        
        # Return device types that exist in both lists
        return [dt for dt in device_types if dt in adjusted_distribution]

    def _select_device_type(self, device_types: list[str], home_type: str | None = None) -> str:
        """Select device type based on distribution, optionally adjusted for home type."""
        # Create weighted list
        weighted_types = []
        
        # Use home-type-adjusted distribution if available
        if home_type and home_type in self.HOME_TYPE_DEVICE_PATTERNS:
            patterns = self.HOME_TYPE_DEVICE_PATTERNS[home_type]
            adjusted_distribution = self.DEVICE_TYPE_DISTRIBUTION.copy()
            
            # Apply home type adjustments
            if 'climate_ratio' in patterns:
                adjusted_distribution['climate'] = int(adjusted_distribution['climate'] * (1 + patterns['climate_ratio']))
            if 'security_ratio' in patterns:
                adjusted_distribution['security'] = int(adjusted_distribution['security'] * (1 + patterns['security_ratio']))
            if 'media_ratio' in patterns:
                adjusted_distribution['media'] = int(adjusted_distribution['media'] * (1 + patterns['media_ratio']))
            if 'vacuum_ratio' in patterns:
                adjusted_distribution['vacuum'] = int(adjusted_distribution['vacuum'] * (1 + patterns['vacuum_ratio']))
            
            distribution = adjusted_distribution
        else:
            distribution = self.DEVICE_TYPE_DISTRIBUTION
        
        for device_type in device_types:
            weight = distribution.get(device_type, 10)
            weighted_types.extend([device_type] * weight)
        
        return random.choice(weighted_types)

    def _generate_device_sample(
        self,
        device_id: str,
        device_type: str,
        days: int = 180,
        failure_scenario: str | None = None,
        home_type: str | None = None,
        reference_date: datetime | None = None
    ) -> dict[str, Any]:
        """
        Generate a single device sample with realistic metrics.
        
        Args:
            device_id: Unique device identifier
            device_type: Type of device (sensor, switch, light, etc.)
            days: Number of days of historical data
            failure_scenario: Optional failure scenario name
        
        Returns:
            Device metric dictionary compatible with training pipeline
        """
        # Get base characteristics for device type
        if device_type not in self.DEVICE_CHARACTERISTICS:
            device_type = 'sensor'# Fallback
        
        base_chars = self.DEVICE_CHARACTERISTICS[device_type]
        
        # Generate base metrics with enhanced temporal patterns (2025)
        # Use reference_date for timezone-aware temporal calculations
        response_time = self._generate_realistic_value(
            base_chars['response_time'],
            pattern='daily_cycle',
            days=days,
            reference_date=reference_date
        )
        
        error_rate = self._generate_realistic_value(
            base_chars['error_rate'],
            pattern='stable',
            days=days,
            reference_date=reference_date
        )
        
        battery_level = self._generate_realistic_value(
            base_chars['battery_level'],
            pattern='degradation' if device_type in ['battery_powered', 'security'] else 'stable',
            days=days,
            reference_date=reference_date
        )
        
        signal_strength = self._generate_realistic_value(
            base_chars['signal_strength'],
            pattern='variation',
            days=days,
            reference_date=reference_date
        )
        
        # Enhanced usage frequency with weekend patterns (2025)
        usage_frequency = self._generate_realistic_value(
            base_chars['usage_frequency'],
            pattern='weekend_peak' if device_type in ['light', 'media'] else 'weekly_cycle',
            days=days,
            reference_date=reference_date
        )
        
        # Enhanced temperature with seasonal-daily combination (2025)
        temperature = self._generate_realistic_value(
            base_chars['temperature'],
            pattern='seasonal_daily' if device_type == 'climate' else 'daily_cycle',
            days=days,
            reference_date=reference_date
        )
        
        # Enhanced humidity with seasonal patterns (2025)
        humidity = self._generate_realistic_value(
            base_chars['humidity'],
            pattern='seasonal',
            days=days,
            reference_date=reference_date
        )
        
        uptime_hours = self._generate_realistic_value(
            base_chars['uptime_hours'],
            pattern='increasing',
            days=days,
            reference_date=reference_date
        )
        
        restart_count = self._generate_realistic_value(
            base_chars['restart_count'],
            pattern='stable',
            days=days,
            reference_date=reference_date
        )
        
        connection_drops = self._generate_realistic_value(
            base_chars['connection_drops'],
            pattern='stable',
            days=days,
            reference_date=reference_date
        )
        
        # Enhanced data transfer with daily patterns (2025)
        data_transfer_rate = self._generate_realistic_value(
            base_chars['data_transfer_rate'],
            pattern='daily_cycle' if device_type == 'media' else 'variation',
            days=days,
            reference_date=reference_date
        )
        
        # Apply failure scenario if specified
        if failure_scenario:
            failure_params = self.FAILURE_SCENARIOS[failure_scenario]
            
            # Apply multipliers
            error_rate *= random.uniform(*failure_params['error_rate_multiplier'])
            response_time *= random.uniform(*failure_params['response_time_multiplier'])
            connection_drops += random.randint(*failure_params['connection_drops_increase'])
            
            # Battery depletion
            if failure_params['battery_depletion_rate'] > 0:
                battery_level = max(0, battery_level - (failure_params['battery_depletion_rate'] * days * 100))
        
        # Ensure realistic ranges
        response_time = max(10, min(5000, response_time))
        error_rate = max(0.0, min(1.0, error_rate))
        battery_level = max(0, min(100, battery_level))
        signal_strength = max(-100, min(-10, signal_strength))
        usage_frequency = max(0.0, min(1.0, usage_frequency))
        temperature = max(-10, min(50, temperature))
        humidity = max(0, min(100, humidity))
        uptime_hours = max(1.0, uptime_hours)
        restart_count = max(0, restart_count)
        connection_drops = max(0, connection_drops)
        data_transfer_rate = max(10, data_transfer_rate)
        
        # Build sample dictionary (matches _collect_training_data format)
        sample = {
            "device_id": device_id,
            "response_time": round(response_time, 2),
            "error_rate": round(error_rate, 4),
            "battery_level": round(battery_level, 1),
            "signal_strength": round(signal_strength, 1),
            "usage_frequency": round(usage_frequency, 3),
            "temperature": round(temperature, 1),
            "humidity": round(humidity, 1),
            "uptime_hours": round(uptime_hours, 1),
            "restart_count": int(restart_count),
            "connection_drops": int(connection_drops),
            "data_transfer_rate": round(data_transfer_rate, 1)
        }
        
        # Add optional health score (if device would have one)
        if random.random() > 0.3:  # 70% of devices have health score
            # Calculate health score based on metrics
            health_score = self._calculate_health_score(sample)
            sample["health_score"] = round(health_score, 2)
        
        return sample

    def _generate_realistic_value(
        self,
        base_range: tuple[float, float],
        pattern: str = 'stable',
        days: int = 180,
        reference_date: datetime | None = None
    ) -> float:
        """
        Generate realistic value with enhanced temporal patterns (2025 patterns).
        
        Args:
            base_range: (min, max) range for the value
            pattern: Pattern type ('stable', 'daily_cycle', 'weekly_cycle', 'seasonal', 
                     'degradation', 'increasing', 'variation', 'seasonal_daily', 'weekend_peak')
            days: Number of days to simulate
            reference_date: Optional reference date for temporal calculations (2025: timezone-aware)
        
        Returns:
            Realistic value within range
        """
        min_val, max_val = base_range
        base_value = random.uniform(min_val, max_val)
        
        # Use current date if not provided (2025: timezone-aware)
        if reference_date is None:
            reference_date = datetime.now(timezone.utc)
        elif reference_date.tzinfo is None:
            # Ensure timezone-aware (2025 best practice)
            reference_date = reference_date.replace(tzinfo=timezone.utc)
        
        if pattern == 'stable':
            # Small random variation around base
            variation = random.uniform(-0.1, 0.1) * (max_val - min_val)
            return base_value + variation
        
        elif pattern == 'daily_cycle':
            # Enhanced daily cycle with time-of-day awareness (2025 pattern)
            # Morning (6-9 AM) and evening (6-9 PM) peaks
            hour = reference_date.hour
            if 6 <= hour <= 9 or 18 <= hour <= 21:
                # Peak hours: higher values
                cycle_factor = np.sin((hour / 24) * 2 * np.pi) * 0.25 + 0.1
            else:
                # Off-peak: lower values
                cycle_factor = np.sin((hour / 24) * 2 * np.pi) * 0.15
            variation = cycle_factor * (max_val - min_val)
            return base_value + variation
        
        elif pattern == 'weekly_cycle':
            # Enhanced weekly pattern with weekday/weekend awareness (2025 pattern)
            weekday = reference_date.weekday()  # 0=Monday, 6=Sunday
            if weekday < 5:  # Weekday
                cycle_factor = np.sin((weekday / 7) * 2 * np.pi) * 0.1
            else:  # Weekend
                cycle_factor = np.sin((weekday / 7) * 2 * np.pi) * 0.2 + 0.1  # Higher on weekends
            variation = cycle_factor * (max_val - min_val)
            return base_value + variation
        
        elif pattern == 'seasonal':
            # Enhanced seasonal variation with month awareness (2025 pattern)
            month = reference_date.month
            # Northern hemisphere: winter (Dec-Feb) lower, summer (Jun-Aug) higher
            seasonal_phase = (month - 1) / 12.0 * 2 * np.pi
            seasonal_factor = np.sin(seasonal_phase) * 0.3
            variation = seasonal_factor * (max_val - min_val)
            return base_value + variation
        
        elif pattern == 'seasonal_daily':
            # Combined seasonal and daily patterns (2025: multi-scale temporal)
            month = reference_date.month
            hour = reference_date.hour
            seasonal_phase = (month - 1) / 12.0 * 2 * np.pi
            daily_phase = (hour / 24.0) * 2 * np.pi
            combined_factor = (np.sin(seasonal_phase) * 0.2 + np.sin(daily_phase) * 0.15)
            variation = combined_factor * (max_val - min_val)
            return base_value + variation
        
        elif pattern == 'weekend_peak':
            # Weekend-specific peak pattern (2025: behavior-aware)
            weekday = reference_date.weekday()
            if weekday >= 5:  # Weekend
                peak_factor = 0.2 + random.uniform(-0.05, 0.05)
            else:  # Weekday
                peak_factor = -0.1 + random.uniform(-0.05, 0.05)
            variation = peak_factor * (max_val - min_val)
            return base_value + variation
        
        elif pattern == 'degradation':
            # Gradual degradation over time (days-based)
            degradation_rate = 1.0 - (days * 0.0005)  # ~0.5% per day over 180 days
            degradation_factor = max(0.7, degradation_rate)  # Cap at 30% degradation
            return base_value * degradation_factor
        
        elif pattern == 'increasing':
            # Gradual increase over time (days-based)
            increase_rate = 1.0 + (days * 0.001)  # ~0.1% per day
            increase_factor = min(1.5, increase_rate)  # Cap at 50% increase
            return base_value * increase_factor
        
        elif pattern == 'variation':
            # Random variation within range
            variation = random.uniform(-0.2, 0.2) * (max_val - min_val)
            return base_value + variation
        
        else:
            # Default: stable with small variation
            variation = random.uniform(-0.1, 0.1) * (max_val - min_val)
            return base_value + variation

    def _calculate_health_score(self, sample: dict[str, Any]) -> float:
        """
        Calculate health score based on device metrics.
        
        Args:
            sample: Device metric dictionary
        
        Returns:
            Health score (0.0-1.0, where 1.0 is healthy)
        """
        score = 1.0
        
        # Penalize high error rate
        if sample['error_rate'] > 0.1:
            score -= 0.3
        elif sample['error_rate'] > 0.05:
            score -= 0.15
        
        # Penalize slow response time
        if sample['response_time'] > 2000:
            score -= 0.2
        elif sample['response_time'] > 1000:
            score -= 0.1
        
        # Penalize low battery
        if sample['battery_level'] < 20:
            score -= 0.2
        elif sample['battery_level'] < 50:
            score -= 0.1
        
        # Penalize poor signal
        if sample['signal_strength'] < -80:
            score -= 0.15
        elif sample['signal_strength'] < -70:
            score -= 0.08
        
        # Penalize connection drops
        if sample['connection_drops'] > 5:
            score -= 0.15
        elif sample['connection_drops'] > 2:
            score -= 0.08
        
        # Penalize frequent restarts
        if sample['restart_count'] > 10:
            score -= 0.1
        
        return max(0.0, min(1.0, score))

