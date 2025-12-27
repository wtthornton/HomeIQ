# External Data Generation Usage Examples

**Date:** November 2025  
**Status:** Production Ready  
**Purpose:** Usage examples and integration guide for synthetic external data generation

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Advanced Usage](#advanced-usage)
4. [Pipeline Integration](#pipeline-integration)
5. [Correlation Validation](#correlation-validation)
6. [Configuration Options](#configuration-options)

---

## Quick Start

### Generate External Data for a Single Home

```python
import asyncio
from datetime import datetime, timedelta, timezone
from src.training.synthetic_external_data_generator import SyntheticExternalDataGenerator
from src.training.synthetic_home_generator import SyntheticHomeGenerator

async def main():
    # Generate a synthetic home
    home_generator = SyntheticHomeGenerator()
    homes = home_generator.generate_homes(target_count=1)
    home = homes[0]
    
    # Generate external data
    external_data_generator = SyntheticExternalDataGenerator()
    start_date = datetime.now(timezone.utc) - timedelta(days=90)
    
    external_data = await external_data_generator.generate_external_data(
        home=home,
        start_date=start_date,
        days=90
    )
    
    # Access generated data
    weather = external_data['weather']
    carbon = external_data['carbon_intensity']
    pricing = external_data['pricing']
    calendar = external_data['calendar']
    
    print(f"Generated {len(weather)} weather points")
    print(f"Generated {len(carbon)} carbon intensity points")
    print(f"Generated {len(pricing)} pricing points")
    print(f"Generated {len(calendar)} calendar events")

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Basic Usage

### Generate All External Data Types

```python
from src.training.synthetic_external_data_generator import SyntheticExternalDataGenerator
from datetime import datetime, timedelta, timezone

# Initialize generator
generator = SyntheticExternalDataGenerator()

# Generate external data
external_data = await generator.generate_external_data(
    home={
        'home_type': 'single_family_house',
        'location': {'latitude': 37.7749, 'longitude': -122.4194}
    },
    start_date=datetime.now(timezone.utc) - timedelta(days=30),
    days=30
)

# Access data
weather_data = external_data['weather']
carbon_data = external_data['carbon_intensity']
pricing_data = external_data['pricing']
calendar_data = external_data['calendar']
```

### Generate Specific Data Types Only

```python
# Generate only weather and carbon data
external_data = await generator.generate_external_data(
    home=home,
    start_date=start_date,
    days=30,
    enable_weather=True,
    enable_carbon=True,
    enable_pricing=False,  # Skip pricing
    enable_calendar=False  # Skip calendar
)
```

### With Custom Location

```python
external_data = await generator.generate_external_data(
    home=home,
    start_date=start_date,
    days=30,
    location={
        'latitude': 40.7128,
        'longitude': -74.0060,
        'region': 'new_york',
        'climate_zone': 'temperate'
    }
)
```

---

## Advanced Usage

### Full Pipeline Integration

```python
from src.training.synthetic_home_generator import SyntheticHomeGenerator
from src.training.synthetic_area_generator import SyntheticAreaGenerator
from src.training.synthetic_device_generator import SyntheticDeviceGenerator
from src.training.synthetic_event_generator import SyntheticEventGenerator
from src.training.synthetic_external_data_generator import SyntheticExternalDataGenerator
from datetime import datetime, timedelta, timezone

async def generate_complete_home():
    # Generate home structure
    home_gen = SyntheticHomeGenerator()
    homes = home_gen.generate_homes(target_count=1)
    home = homes[0]
    
    # Generate areas
    area_gen = SyntheticAreaGenerator()
    areas = area_gen.generate_areas(home)
    home['areas'] = areas
    
    # Generate devices
    device_gen = SyntheticDeviceGenerator()
    devices = device_gen.generate_devices(home, areas)
    home['devices'] = devices
    
    # Generate events
    event_gen = SyntheticEventGenerator()
    events = await event_gen.generate_events(devices, days=90)
    home['events'] = events
    
    # Generate external data
    external_gen = SyntheticExternalDataGenerator()
    start_date = datetime.now(timezone.utc) - timedelta(days=90)
    
    external_data = await external_gen.generate_external_data(
        home=home,
        start_date=start_date,
        days=90
    )
    home['external_data'] = external_data
    
    return home
```

### Apply Correlations to Events

```python
from src.training.synthetic_weather_generator import SyntheticWeatherGenerator
from src.training.synthetic_carbon_intensity_generator import SyntheticCarbonIntensityGenerator

# Generate external data
external_data = await external_gen.generate_external_data(...)

# Apply weather correlations to HVAC and windows
weather_gen = SyntheticWeatherGenerator()
correlated_events = weather_gen.correlate_with_hvac(
    external_data['weather'],
    events,
    devices
)
correlated_events = weather_gen.correlate_with_windows(
    external_data['weather'],
    correlated_events,
    devices
)

# Apply carbon correlations to energy devices
carbon_gen = SyntheticCarbonIntensityGenerator()
final_events = carbon_gen.correlate_with_energy_devices(
    external_data['carbon_intensity'],
    correlated_events,
    devices
)
```

---

## Pipeline Integration

### Using the Command-Line Script

```bash
# Generate 100 homes with all external data
python scripts/generate_synthetic_homes.py \
    --count 100 \
    --days 90 \
    --output tests/datasets/synthetic_homes

# Generate with specific data types only
python scripts/generate_synthetic_homes.py \
    --count 50 \
    --days 30 \
    --enable-weather \
    --enable-carbon \
    --disable-pricing \
    --disable-calendar

# Generate specific home types
python scripts/generate_synthetic_homes.py \
    --count 20 \
    --home-types single_family_house apartment \
    --days 90
```

### Programmatic Pipeline Usage

```python
import asyncio
from scripts.generate_synthetic_homes import main

# Run the pipeline programmatically
async def run_pipeline():
    # This simulates command-line arguments
    class Args:
        count = 100
        days = 90
        output = 'tests/datasets/synthetic_homes'
        home_types = None
        enable_openai = False
        enable_weather = True
        enable_carbon = True
        enable_pricing = True
        enable_calendar = True
    
    args = Args()
    await main()
```

---

## Correlation Validation

### Validate All Correlations

```python
from src.training.synthetic_correlation_engine import SyntheticCorrelationEngine

# Initialize correlation engine
correlation_engine = SyntheticCorrelationEngine()

# Validate all correlations
results = correlation_engine.validate_all_correlations(
    external_data=external_data,
    device_events=events,
    devices=devices
)

# Check results
print(f"Overall valid: {results['overall_valid']}")
print(f"Overall score: {results['overall_score']:.2f}")
print(f"Weather-HVAC score: {results['weather_hvac']['correlation_score']:.2f}")
print(f"Energy score: {results['energy']['correlation_score']:.2f}")
print(f"Calendar-Presence score: {results['calendar_presence']['correlation_score']:.2f}")

# Check for violations
if results['weather_hvac']['violations']:
    print(f"Weather-HVAC violations: {results['weather_hvac']['violations']}")
```

### Validate Individual Correlations

```python
# Validate weather-HVAC correlation only
weather_hvac_result = correlation_engine.validate_weather_hvac_correlation(
    weather_data=external_data['weather'],
    hvac_events=[e for e in events if e.get('entity_id', '').startswith('climate.')]
)

# Validate energy correlation
energy_result = correlation_engine.validate_energy_correlation(
    carbon_data=external_data['carbon_intensity'],
    pricing_data=external_data['pricing'],
    energy_events=[e for e in events if 'ev' in e.get('entity_id', '').lower()]
)

# Validate calendar-presence correlation
calendar_result = correlation_engine.validate_calendar_presence_correlation(
    calendar_data=external_data['calendar'],
    device_events=events,
    devices=devices
)
```

---

## Configuration Options

### Enable/Disable Data Types

```python
# Generate only weather data
external_data = await generator.generate_external_data(
    home=home,
    start_date=start_date,
    days=30,
    enable_weather=True,
    enable_carbon=False,
    enable_pricing=False,
    enable_calendar=False
)
```

### Custom Location Settings

```python
# Specify location for weather and carbon generation
external_data = await generator.generate_external_data(
    home=home,
    start_date=start_date,
    days=30,
    location={
        'latitude': 37.7749,
        'longitude': -122.4194,
        'region': 'california',
        'climate_zone': 'mediterranean',
        'grid_region': 'california_iso'
    }
)
```

### Time Range Configuration

```python
from datetime import datetime, timedelta, timezone

# Generate data for specific date range
start_date = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
days = 365  # Full year

external_data = await generator.generate_external_data(
    home=home,
    start_date=start_date,
    days=days
)
```

---

## Data Structure Examples

### Weather Data Structure

```python
weather_point = {
    'timestamp': '2025-06-15T12:00:00+00:00',
    'temperature': 25.5,  # °C
    'humidity': 65.0,     # %
    'pressure': 1013.25,  # hPa
    'wind_speed': 5.2,    # m/s
    'wind_direction': 180,  # degrees
    'condition': 'sunny',
    'cloud_cover': 10.0,  # %
    'precipitation': 0.0  # mm/h
}
```

### Carbon Intensity Data Structure

```python
carbon_point = {
    'timestamp': '2025-06-15T12:00:00+00:00',
    'intensity': 200.0,  # gCO2/kWh
    'renewable_percentage': 50.0,  # %
    'region': 'california'
}
```

### Pricing Data Structure

```python
pricing_point = {
    'timestamp': '2025-06-15T12:00:00+00:00',
    'price_per_kwh': 0.20,  # $/kWh
    'pricing_tier': 'mid-peak',
    'region': 'california_tou'
}
```

### Calendar Event Structure

```python
calendar_event = {
    'timestamp': '2025-06-15T09:00:00+00:00',
    'event_type': 'work',
    'summary': 'Work',
    'start': '2025-06-15T09:00:00+00:00',
    'end': '2025-06-15T17:00:00+00:00'
}
```

---

## Best Practices

1. **Use async/await**: The `generate_external_data()` method is async, always use `await`
2. **Specify location**: Provide location data for more realistic weather and carbon generation
3. **Validate correlations**: Always validate correlations after generating external data
4. **Enable selectively**: Only enable data types you need to reduce generation time
5. **Use appropriate time ranges**: Generate data for the time period you actually need

---

## Troubleshooting

### Performance Issues

If generation is slow:
- Reduce the number of days
- Disable unused data types
- Use fewer homes in batch generation

### Correlation Validation Failures

If correlations fail:
- Check that device events match the external data timestamps
- Verify device types are correctly identified (HVAC, energy devices, etc.)
- Review violation messages for specific issues

### Missing Data

If data is missing:
- Check that enable flags are set correctly
- Verify home structure includes location data
- Check generator logs for errors

---

**Last Updated:** November 2025

