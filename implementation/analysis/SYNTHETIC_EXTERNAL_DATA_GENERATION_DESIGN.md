# Synthetic External Data Generation Design & Plan

**Date:** January 2025  
**Status:** Design & Implementation Plan  
**Purpose:** Design smart, realistic synthetic data generation for weather, carbon intensity, electricity pricing, and calendar data to support correlation analysis training

---

## Executive Summary

This document designs a comprehensive synthetic data generation system for external data sources (weather, carbon intensity, electricity pricing, calendar) that integrates with the existing synthetic home generation pipeline. The generated data will be:

- **Smart**: Correlates with device usage patterns and home characteristics
- **Realistic**: Follows real-world patterns (seasonal, daily, weekly cycles)
- **Correlation-Ready**: Designed to support correlation analysis training
- **Home-Aware**: Adapts to home type, location, and characteristics

**Key Features:**
- Location-based weather generation (latitude/longitude, climate zones)
- Grid-aware carbon intensity (regional patterns, time-of-day variations)
- Market-based electricity pricing (time-of-use, demand patterns)
- Person-aware calendar generation (work schedules, routines, presence patterns)

---

## 1. Current State Analysis

### 1.1 Existing Synthetic Data Generation

**Current Components:**
- ✅ `SyntheticHomeGenerator` - Home metadata and structure
- ✅ `SyntheticAreaGenerator` - Room/area generation
- ✅ `SyntheticDeviceGenerator` - Device generation
- ✅ `SyntheticEventGenerator` - Device event generation

**Current Data Generated:**
- Home metadata (type, size, description)
- Areas (rooms, spaces)
- Devices (entity_id, domain, device_class, area)
- Events (state_changed events with timestamps, states, attributes)

**Missing External Data:**
- ❌ Weather data (temperature, humidity, condition, wind)
- ❌ Carbon intensity data (grid carbon intensity, renewable percentage)
- ❌ Electricity pricing data (price per kWh, time-of-use rates)
- ❌ Calendar data (events, schedules, presence patterns)

---

### 1.2 Integration Points

**Data Storage:**
- **InfluxDB**: Time-series data (events, weather, carbon, electricity)
- **SQLite**: Metadata (devices, entities, calendar events)

**Generation Pipeline:**
```
SyntheticHomeGenerator
    ↓
SyntheticAreaGenerator
    ↓
SyntheticDeviceGenerator
    ↓
SyntheticEventGenerator
    ↓
[NEW] SyntheticExternalDataGenerator
    ├─ SyntheticWeatherGenerator
    ├─ SyntheticCarbonIntensityGenerator
    ├─ SyntheticElectricityPricingGenerator
    └─ SyntheticCalendarGenerator
```

---

## 2. Design: Synthetic Weather Data Generation

### 2.1 Requirements

**Data Points:**
- Temperature (°C or °F)
- Humidity (%)
- Pressure (hPa)
- Wind speed (m/s or mph)
- Wind direction (degrees)
- Weather condition (sunny, cloudy, rainy, snowy, etc.)
- Cloud cover (%)
- Precipitation (mm/h)

**Realistic Patterns:**
- **Seasonal**: Temperature varies by season (winter cold, summer hot)
- **Daily**: Temperature peaks in afternoon, lowest at night
- **Geographic**: Different climates (tropical, temperate, continental, etc.)
- **Correlation**: Weather affects HVAC usage, window states, lighting

---

### 2.2 Design: Smart Weather Generation

**Location-Based Generation:**
```python
class SyntheticWeatherGenerator:
    """
    Generate realistic weather data based on:
    - Home location (latitude, longitude, climate zone)
    - Time of year (seasonal patterns)
    - Time of day (diurnal patterns)
    - Home type (affects microclimate)
    """
    
    # Climate zones (Köppen classification)
    CLIMATE_ZONES = {
        'tropical': {
            'temp_range': (20, 35),  # °C
            'humidity_range': (60, 90),
            'seasonal_variation': 5,  # Small seasonal variation
            'precipitation_freq': 0.3  # 30% chance of rain
        },
        'temperate': {
            'temp_range': (-5, 30),
            'humidity_range': (40, 80),
            'seasonal_variation': 15,
            'precipitation_freq': 0.25
        },
        'continental': {
            'temp_range': (-20, 35),
            'humidity_range': (30, 70),
            'seasonal_variation': 25,
            'precipitation_freq': 0.2
        },
        'arctic': {
            'temp_range': (-40, 15),
            'humidity_range': (50, 90),
            'seasonal_variation': 30,
            'precipitation_freq': 0.15
        }
    }
    
    def generate_weather(
        self,
        home: dict,
        start_date: datetime,
        days: int,
        location: dict = None  # {lat, lon, climate_zone}
    ) -> list[dict]:
        """
        Generate weather data for a home.
        
        Args:
            home: Home dictionary with metadata
            start_date: Start date for weather generation
            days: Number of days to generate
            location: Optional location data (auto-detected if not provided)
        
        Returns:
            List of weather data points (hourly)
        """
```

**Smart Features:**
1. **Seasonal Temperature Modeling**:
   - Base temperature from climate zone
   - Seasonal offset (winter: -10°C, summer: +10°C)
   - Daily cycle (peak at 2-3 PM, minimum at 4-6 AM)
   - Random variation (±3°C)

2. **Humidity Correlation**:
   - Higher humidity when raining
   - Lower humidity in hot weather
   - Geographic patterns (coastal vs inland)

3. **Weather Condition Logic**:
   - Rain probability based on season and climate
   - Snow when temperature < 0°C
   - Cloudy conditions affect temperature
   - Wind patterns (stronger in storms)

4. **Device Correlation**:
   - HVAC usage increases with temperature extremes
   - Window states correlate with weather (open in nice weather)
   - Lighting affected by cloud cover

---

### 2.3 Implementation Plan

**File:** `services/ai-automation-service/src/training/synthetic_weather_generator.py`

**Key Methods:**
- `generate_weather()` - Main generation method
- `_get_climate_zone()` - Determine climate from location
- `_calculate_seasonal_temp()` - Seasonal temperature calculation
- `_calculate_daily_temp()` - Daily temperature cycle
- `_generate_condition()` - Weather condition logic
- `_correlate_with_devices()` - Correlate weather with device events

**Integration:**
- Called after event generation
- Weather data stored in home JSON structure
- Can be injected into InfluxDB separately

---

## 3. Design: Synthetic Carbon Intensity Data Generation

### 3.1 Requirements

**Data Points:**
- Carbon intensity (gCO2/kWh)
- Renewable percentage (%)
- Grid region identifier
- Forecast (24-hour ahead)

**Realistic Patterns:**
- **Time-of-Day**: Lower carbon during solar peak (midday), higher in evening
- **Weekly**: Weekends may have different patterns
- **Seasonal**: Solar generation varies by season
- **Regional**: Different grid regions have different carbon profiles

---

### 3.2 Design: Smart Carbon Intensity Generation

**Grid-Aware Generation:**
```python
class SyntheticCarbonIntensityGenerator:
    """
    Generate realistic carbon intensity data based on:
    - Grid region (affects baseline carbon intensity)
    - Time of day (solar generation patterns)
    - Day of week (demand patterns)
    - Season (solar generation varies)
    """
    
    # Grid region profiles (baseline carbon intensity in gCO2/kWh)
    GRID_REGIONS = {
        'california': {
            'baseline': 250,  # Lower due to renewables
            'solar_peak': 150,  # Midday reduction
            'evening_peak': 350,  # Evening increase
            'renewable_capacity': 0.4  # 40% renewable capacity
        },
        'texas': {
            'baseline': 400,
            'solar_peak': 300,
            'evening_peak': 500,
            'renewable_capacity': 0.25
        },
        'germany': {
            'baseline': 350,
            'solar_peak': 200,
            'evening_peak': 450,
            'renewable_capacity': 0.5
        },
        'coal_heavy': {
            'baseline': 600,
            'solar_peak': 550,
            'evening_peak': 650,
            'renewable_capacity': 0.1
        }
    }
    
    def generate_carbon_intensity(
        self,
        home: dict,
        start_date: datetime,
        days: int,
        grid_region: str = None
    ) -> list[dict]:
        """
        Generate carbon intensity data.
        
        Args:
            home: Home dictionary
            start_date: Start date
            days: Number of days
            grid_region: Grid region identifier (auto-detected if not provided)
        
        Returns:
            List of carbon intensity data points (15-minute intervals)
        """
```

**Smart Features:**
1. **Time-of-Day Patterns**:
   - Lowest carbon: 10 AM - 3 PM (solar peak)
   - Highest carbon: 6 PM - 9 PM (evening peak)
   - Night baseline: Moderate carbon

2. **Seasonal Solar Generation**:
   - Summer: Strong solar reduction (50-70% reduction at peak)
   - Winter: Weak solar reduction (20-30% reduction at peak)
   - Spring/Fall: Moderate reduction (40-50%)

3. **Weekly Patterns**:
   - Weekdays: Higher demand, more variation
   - Weekends: Lower demand, more stable

4. **Device Correlation**:
   - High-energy devices correlate with carbon intensity
   - EV charging should prefer low-carbon periods
   - HVAC usage affects carbon footprint

---

### 3.3 Implementation Plan

**File:** `services/ai-automation-service/src/training/synthetic_carbon_intensity_generator.py`

**Key Methods:**
- `generate_carbon_intensity()` - Main generation method
- `_detect_grid_region()` - Auto-detect grid region from home location
- `_calculate_time_of_day_factor()` - Time-of-day carbon variation
- `_calculate_seasonal_solar()` - Seasonal solar generation
- `_calculate_renewable_percentage()` - Renewable energy percentage
- `_correlate_with_energy_devices()` - Correlate with high-energy devices

**Integration:**
- Called after event generation
- Carbon data stored in home JSON structure
- 15-minute intervals (matches real API refresh rate)

---

## 4. Design: Synthetic Electricity Pricing Data Generation

### 4.1 Requirements

**Data Points:**
- Price per kWh (currency-specific)
- Time-of-use periods (peak, off-peak, super off-peak)
- Forecast (24-hour ahead pricing)
- Currency (EUR, USD, etc.)

**Realistic Patterns:**
- **Time-of-Use**: Higher prices during peak hours
- **Daily**: Price varies throughout day
- **Weekly**: Weekend pricing may differ
- **Market-Based**: Prices reflect demand and supply
- **Regional**: Different pricing regions

---

### 4.2 Design: Smart Electricity Pricing Generation

**Market-Aware Generation:**
```python
class SyntheticElectricityPricingGenerator:
    """
    Generate realistic electricity pricing data based on:
    - Pricing region (affects baseline prices)
    - Time-of-use structure (peak/off-peak)
    - Market dynamics (demand-based pricing)
    - Day of week (weekend pricing)
    """
    
    # Pricing region profiles (baseline price in currency/kWh)
    PRICING_REGIONS = {
        'germany_awattar': {
            'baseline': 0.30,  # EUR/kWh
            'peak_multiplier': 1.5,  # Peak hours: 1.5x
            'off_peak_multiplier': 0.7,  # Off-peak: 0.7x
            'currency': 'EUR',
            'peak_hours': [17, 18, 19, 20],  # 5 PM - 9 PM
            'off_peak_hours': [0, 1, 2, 3, 4, 5]  # Midnight - 6 AM
        },
        'california_tou': {
            'baseline': 0.25,  # USD/kWh
            'peak_multiplier': 2.0,
            'off_peak_multiplier': 0.5,
            'currency': 'USD',
            'peak_hours': [15, 16, 17, 18, 19, 20],  # 3 PM - 9 PM
            'off_peak_hours': [22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8]  # 10 PM - 9 AM
        },
        'fixed_rate': {
            'baseline': 0.12,  # USD/kWh
            'peak_multiplier': 1.0,  # No variation
            'off_peak_multiplier': 1.0,
            'currency': 'USD',
            'peak_hours': [],
            'off_peak_hours': []
        }
    }
    
    def generate_electricity_pricing(
        self,
        home: dict,
        start_date: datetime,
        days: int,
        pricing_region: str = None
    ) -> list[dict]:
        """
        Generate electricity pricing data.
        
        Args:
            home: Home dictionary
            start_date: Start date
            days: Number of days
            pricing_region: Pricing region identifier
        
        Returns:
            List of pricing data points (hourly)
        """
```

**Smart Features:**
1. **Time-of-Use Pricing**:
   - Peak hours: 1.5-2.0x baseline price
   - Off-peak hours: 0.5-0.7x baseline price
   - Mid-peak: 1.0x baseline price

2. **Market Dynamics**:
   - High demand → higher prices
   - Low demand → lower prices
   - Random variation (±10%)

3. **Weekly Patterns**:
   - Weekdays: More price variation
   - Weekends: More stable pricing

4. **Device Correlation**:
   - High-energy devices correlate with pricing
   - EV charging should prefer low-price periods
   - HVAC scheduling based on pricing

---

### 3.3 Implementation Plan

**File:** `services/ai-automation-service/src/training/synthetic_electricity_pricing_generator.py`

**Key Methods:**
- `generate_electricity_pricing()` - Main generation method
- `_detect_pricing_region()` - Auto-detect pricing region
- `_calculate_time_of_use_price()` - Time-of-use pricing calculation
- `_calculate_market_dynamics()` - Market-based price variation
- `_correlate_with_energy_devices()` - Correlate with energy usage

**Integration:**
- Called after event generation
- Pricing data stored in home JSON structure
- Hourly intervals (matches real API refresh rate)

---

## 5. Design: Synthetic Calendar Data Generation

### 5.1 Requirements

**Data Points:**
- Calendar events (work, meetings, travel, etc.)
- Event metadata (title, description, location, attendees)
- Recurring events (daily, weekly, monthly)
- Presence patterns (home, away, work, travel)

**Realistic Patterns:**
- **Work Schedules**: 9-5 workdays, weekends off
- **Routines**: Morning routines, evening routines
- **Travel**: Occasional trips, vacations
- **Meetings**: Work meetings, personal appointments
- **Presence**: Home during evenings/weekends, away during work hours

---

### 5.2 Design: Smart Calendar Generation

**Person-Aware Generation:**
```python
class SyntheticCalendarGenerator:
    """
    Generate realistic calendar data based on:
    - Home type (affects work patterns)
    - Number of residents (multiple calendars)
    - Work schedule (9-5, shift work, remote work)
    - Lifestyle (active, sedentary, family-oriented)
    """
    
    # Work schedule profiles
    WORK_SCHEDULES = {
        'standard_9to5': {
            'work_days': [0, 1, 2, 3, 4],  # Monday-Friday
            'work_start': 9,  # 9 AM
            'work_end': 17,  # 5 PM
            'commute_time': 30  # minutes
        },
        'shift_work': {
            'work_days': [0, 1, 2, 3, 4, 5, 6],  # All days
            'work_start': 22,  # 10 PM
            'work_end': 6,  # 6 AM (next day)
            'commute_time': 20
        },
        'remote_work': {
            'work_days': [0, 1, 2, 3, 4],
            'work_start': 8,
            'work_end': 17,
            'commute_time': 0  # No commute
        },
        'unemployed': {
            'work_days': [],
            'work_start': None,
            'work_end': None,
            'commute_time': 0
        }
    }
    
    def generate_calendar(
        self,
        home: dict,
        start_date: datetime,
        days: int,
        residents: list[dict] = None  # [{name, work_schedule, lifestyle}]
    ) -> list[dict]:
        """
        Generate calendar events for home residents.
        
        Args:
            home: Home dictionary
            start_date: Start date
            days: Number of days
            residents: List of resident profiles
        
        Returns:
            List of calendar events
        """
```

**Smart Features:**
1. **Work Schedule Generation**:
   - Standard 9-5 workdays
   - Commute events (leave home, arrive work, leave work, arrive home)
   - Work meetings during work hours
   - Lunch breaks

2. **Routine Events**:
   - Morning routine (wake up, breakfast, leave)
   - Evening routine (arrive home, dinner, sleep)
   - Weekly routines (grocery shopping, gym, etc.)

3. **Presence Patterns**:
   - Home: Evenings (6 PM - 9 AM), weekends
   - Away: Work hours (9 AM - 6 PM), weekdays
   - Travel: Occasional trips (1-2 per month)

4. **Device Correlation**:
   - Presence affects device usage
   - Away → devices off, security on
   - Home → devices active, comfort settings
   - Calendar events trigger device changes

---

### 5.3 Implementation Plan

**File:** `services/ai-automation-service/src/training/synthetic_calendar_generator.py`

**Key Methods:**
- `generate_calendar()` - Main generation method
- `_generate_work_schedule()` - Work schedule events
- `_generate_routine_events()` - Daily/weekly routines
- `_generate_travel_events()` - Occasional travel
- `_calculate_presence()` - Presence patterns from calendar
- `_correlate_with_devices()` - Correlate calendar with device usage

**Integration:**
- Called after event generation
- Calendar data stored in home JSON structure
- Can be injected into SQLite (calendar_events table)

---

## 6. Integration Design

### 6.1 Unified External Data Generator

**File:** `services/ai-automation-service/src/training/synthetic_external_data_generator.py`

**Purpose:** Orchestrate all external data generation

```python
class SyntheticExternalDataGenerator:
    """
    Unified generator for all external data sources.
    
    Coordinates:
    - Weather generation
    - Carbon intensity generation
    - Electricity pricing generation
    - Calendar generation
    
    Ensures data correlation and realism.
    """
    
    def __init__(self):
        self.weather_generator = SyntheticWeatherGenerator()
        self.carbon_generator = SyntheticCarbonIntensityGenerator()
        self.pricing_generator = SyntheticElectricityPricingGenerator()
        self.calendar_generator = SyntheticCalendarGenerator()
    
    async def generate_all_external_data(
        self,
        home: dict,
        devices: list[dict],
        events: list[dict],
        start_date: datetime,
        days: int
    ) -> dict:
        """
        Generate all external data for a home.
        
        Args:
            home: Home dictionary
            devices: List of devices
            events: List of device events
            start_date: Start date
            days: Number of days
        
        Returns:
            Dictionary with all external data:
            {
                'weather': [...],
                'carbon_intensity': [...],
                'electricity_pricing': [...],
                'calendar': [...]
            }
        """
        # Generate weather (location-aware)
        weather = self.weather_generator.generate_weather(
            home=home,
            start_date=start_date,
            days=days
        )
        
        # Generate carbon intensity (grid-aware)
        carbon = self.carbon_generator.generate_carbon_intensity(
            home=home,
            start_date=start_date,
            days=days
        )
        
        # Generate electricity pricing (region-aware)
        pricing = self.pricing_generator.generate_electricity_pricing(
            home=home,
            start_date=start_date,
            days=days
        )
        
        # Generate calendar (person-aware)
        calendar = self.calendar_generator.generate_calendar(
            home=home,
            start_date=start_date,
            days=days
        )
        
        # Correlate external data with device events
        self._correlate_external_data_with_events(
            events=events,
            weather=weather,
            carbon=carbon,
            pricing=pricing,
            calendar=calendar
        )
        
        return {
            'weather': weather,
            'carbon_intensity': carbon,
            'electricity_pricing': pricing,
            'calendar': calendar
        }
```

---

### 6.2 Correlation Engine

**Purpose:** Ensure external data correlates realistically with device events

**Correlation Rules:**

1. **Weather → HVAC**:
   - Hot weather → AC usage increases
   - Cold weather → Heating usage increases
   - Nice weather → Windows open, HVAC off

2. **Weather → Lighting**:
   - Cloudy weather → More indoor lighting
   - Sunny weather → Less indoor lighting

3. **Carbon/Pricing → Energy Devices**:
   - Low carbon/low price → High-energy devices active
   - High carbon/high price → High-energy devices inactive

4. **Calendar → Presence**:
   - Work events → Away from home
   - Home events → At home
   - Travel events → Away for extended period

5. **Presence → Devices**:
   - Away → Security on, lights off, HVAC set back
   - Home → Security off, lights on, HVAC comfortable

---

### 6.3 Integration with Existing Pipeline

**Updated Generation Script:**

```python
# In generate_synthetic_homes.py

# After event generation:
events = await event_generator.generate_events(devices, days=args.days)
home['events'] = events

# NEW: Generate external data
external_data_generator = SyntheticExternalDataGenerator()
external_data = await external_data_generator.generate_all_external_data(
    home=home,
    devices=devices,
    events=events,
    start_date=start_date,
    days=args.days
)

# Add external data to home
home['weather'] = external_data['weather']
home['carbon_intensity'] = external_data['carbon_intensity']
home['electricity_pricing'] = external_data['electricity_pricing']
home['calendar'] = external_data['calendar']
```

---

## 7. Data Structure Design

### 7.1 Weather Data Structure

```json
{
  "timestamp": "2025-01-15T10:00:00Z",
  "temperature": 22.5,
  "humidity": 65,
  "pressure": 1013.25,
  "wind_speed": 5.2,
  "wind_direction": 180,
  "condition": "sunny",
  "cloud_cover": 20,
  "precipitation": 0.0,
  "location": {
    "lat": 37.7749,
    "lon": -122.4194,
    "climate_zone": "temperate"
  }
}
```

---

### 7.2 Carbon Intensity Data Structure

```json
{
  "timestamp": "2025-01-15T10:00:00Z",
  "carbon_intensity": 250,
  "renewable_percentage": 45,
  "grid_region": "california",
  "forecast_24h": [
    {"timestamp": "2025-01-15T11:00:00Z", "carbon_intensity": 200},
    {"timestamp": "2025-01-15T12:00:00Z", "carbon_intensity": 150}
  ]
}
```

---

### 7.3 Electricity Pricing Data Structure

```json
{
  "timestamp": "2025-01-15T10:00:00Z",
  "price_per_kwh": 0.25,
  "currency": "USD",
  "time_of_use_period": "mid_peak",
  "pricing_region": "california_tou",
  "forecast_24h": [
    {"timestamp": "2025-01-15T11:00:00Z", "price_per_kwh": 0.30},
    {"timestamp": "2025-01-15T12:00:00Z", "price_per_kwh": 0.35}
  ]
}
```

---

### 7.4 Calendar Data Structure

```json
{
  "event_id": "event_001",
  "title": "Work - Morning Commute",
  "start_time": "2025-01-15T08:00:00Z",
  "end_time": "2025-01-15T08:30:00Z",
  "event_type": "commute",
  "location": "work",
  "resident": "person_1",
  "recurring": {
    "frequency": "daily",
    "days": [0, 1, 2, 3, 4]
  },
  "presence_impact": {
    "before": "home",
    "during": "away",
    "after": "work"
  }
}
```

---

## 8. Implementation Plan

### 8.1 Phase 1: Weather Generation (Week 1)

**Tasks:**
1. Create `SyntheticWeatherGenerator` class
2. Implement location-based climate zone detection
3. Implement seasonal and daily temperature patterns
4. Implement weather condition logic
5. Add weather correlation with HVAC devices
6. Integrate with generation pipeline

**Deliverables:**
- `synthetic_weather_generator.py`
- Weather data in home JSON files
- Tests for weather generation

**Effort:** 3-5 days

---

### 8.2 Phase 2: Carbon Intensity Generation (Week 1-2)

**Tasks:**
1. Create `SyntheticCarbonIntensityGenerator` class
2. Implement grid region profiles
3. Implement time-of-day carbon patterns
4. Implement seasonal solar generation
5. Add carbon correlation with energy devices
6. Integrate with generation pipeline

**Deliverables:**
- `synthetic_carbon_intensity_generator.py`
- Carbon data in home JSON files
- Tests for carbon generation

**Effort:** 3-5 days

---

### 8.3 Phase 3: Electricity Pricing Generation (Week 2)

**Tasks:**
1. Create `SyntheticElectricityPricingGenerator` class
2. Implement pricing region profiles
3. Implement time-of-use pricing
4. Implement market dynamics
5. Add pricing correlation with energy devices
6. Integrate with generation pipeline

**Deliverables:**
- `synthetic_electricity_pricing_generator.py`
- Pricing data in home JSON files
- Tests for pricing generation

**Effort:** 3-5 days

---

### 8.4 Phase 4: Calendar Generation (Week 2-3)

**Tasks:**
1. Create `SyntheticCalendarGenerator` class
2. Implement work schedule generation
3. Implement routine event generation
4. Implement travel event generation
5. Implement presence pattern calculation
6. Add calendar correlation with device usage
7. Integrate with generation pipeline

**Deliverables:**
- `synthetic_calendar_generator.py`
- Calendar data in home JSON files
- Tests for calendar generation

**Effort:** 5-7 days

---

### 8.5 Phase 5: Integration & Correlation (Week 3)

**Tasks:**
1. Create `SyntheticExternalDataGenerator` orchestrator
2. Implement correlation engine
3. Integrate with existing generation script
4. Update home JSON structure
5. Add validation and testing
6. Documentation

**Deliverables:**
- `synthetic_external_data_generator.py`
- Updated `generate_synthetic_homes.py`
- Comprehensive tests
- Documentation

**Effort:** 5-7 days

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Weather Generator:**
- Test climate zone detection
- Test seasonal temperature patterns
- Test daily temperature cycles
- Test weather condition logic
- Test correlation with HVAC

**Carbon Generator:**
- Test grid region profiles
- Test time-of-day patterns
- Test seasonal solar generation
- Test correlation with energy devices

**Pricing Generator:**
- Test pricing region profiles
- Test time-of-use pricing
- Test market dynamics
- Test correlation with energy devices

**Calendar Generator:**
- Test work schedule generation
- Test routine events
- Test presence patterns
- Test correlation with devices

---

### 9.2 Integration Tests

**Full Pipeline Test:**
- Generate complete home with all external data
- Verify data structure
- Verify correlations
- Verify realism

**Correlation Validation:**
- Verify weather → HVAC correlation
- Verify carbon/pricing → energy device correlation
- Verify calendar → presence → device correlation

---

### 9.3 Data Quality Tests

**Realism Checks:**
- Temperature ranges are realistic
- Weather conditions are logical
- Carbon intensity follows patterns
- Pricing follows time-of-use
- Calendar events are consistent

**Correlation Checks:**
- External data correlates with device events
- Presence patterns match calendar
- Energy usage matches carbon/pricing

---

## 10. Usage Examples

### 10.1 Basic Usage

```bash
# Generate homes with external data
python scripts/generate_synthetic_homes.py \
    --count 100 \
    --output tests/datasets/synthetic_homes \
    --days 90
```

**Output:**
- Each home JSON file includes:
  - `weather`: Array of weather data points
  - `carbon_intensity`: Array of carbon data points
  - `electricity_pricing`: Array of pricing data points
  - `calendar`: Array of calendar events

---

### 10.2 Advanced Usage

```python
# Custom external data generation
from src.training.synthetic_external_data_generator import SyntheticExternalDataGenerator

generator = SyntheticExternalDataGenerator()

external_data = await generator.generate_all_external_data(
    home=home,
    devices=devices,
    events=events,
    start_date=datetime.now() - timedelta(days=90),
    days=90,
    location={'lat': 37.7749, 'lon': -122.4194, 'climate_zone': 'temperate'},
    grid_region='california',
    pricing_region='california_tou',
    residents=[{'name': 'person_1', 'work_schedule': 'standard_9to5'}]
)
```

---

## 11. Benefits for Correlation Analysis

### 11.1 Enhanced Training Data

**Correlation Features:**
- Weather → Device correlations
- Carbon → Energy device correlations
- Pricing → Energy device correlations
- Calendar → Presence → Device correlations

**Training Value:**
- TabPFN can learn from external data features
- Correlation predictions include external context
- More realistic correlation patterns

---

### 11.2 Realistic Test Scenarios

**Test Cases:**
- Weather-driven automations
- Energy optimization automations
- Presence-aware automations
- Cost-optimization automations

**Validation:**
- Correlations match real-world patterns
- Automations are context-aware
- Energy optimization works correctly

---

## 12. Summary

**Design Complete:**
- ✅ Weather generation (location-aware, seasonal, daily patterns)
- ✅ Carbon intensity generation (grid-aware, time-of-day patterns)
- ✅ Electricity pricing generation (region-aware, time-of-use)
- ✅ Calendar generation (person-aware, presence patterns)
- ✅ Correlation engine (ensures realistic correlations)
- ✅ Integration plan (phased implementation)

**Next Steps:**
1. Review and approve design
2. Begin Phase 1 implementation (weather generation)
3. Iterate through phases
4. Test and validate
5. Integrate with correlation analysis training

**Estimated Total Effort:** 3-4 weeks

---

**Status:** ✅ Design Complete - Ready for Implementation

