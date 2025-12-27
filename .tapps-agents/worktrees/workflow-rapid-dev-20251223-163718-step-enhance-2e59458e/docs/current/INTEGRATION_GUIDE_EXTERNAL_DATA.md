# External Data Integration Guide

**Date:** November 2025  
**Status:** Production Ready  
**Purpose:** Integration guide for external data generation in the synthetic home pipeline

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Integration Points](#integration-points)
4. [Data Flow](#data-flow)
5. [Home JSON Structure](#home-json-structure)
6. [Correlation Integration](#correlation-integration)
7. [Testing Integration](#testing-integration)

---

## Overview

The external data generation system integrates seamlessly with the existing synthetic home generation pipeline. It adds four types of external data:

- **Weather Data**: Hourly weather conditions (temperature, humidity, etc.)
- **Carbon Intensity Data**: Hourly grid carbon intensity and renewable percentage
- **Electricity Pricing Data**: Hourly electricity pricing with time-of-use tiers
- **Calendar Data**: Calendar events representing presence patterns

All data is generated synchronously and stored in the home's `external_data` section.

---

## Architecture

### Component Structure

```
SyntheticExternalDataGenerator (Orchestrator)
    ├── SyntheticWeatherGenerator
    ├── SyntheticCarbonIntensityGenerator
    ├── SyntheticElectricityPricingGenerator
    └── SyntheticCalendarGenerator

SyntheticCorrelationEngine (Validation)
    ├── validate_weather_hvac_correlation()
    ├── validate_energy_correlation()
    └── validate_calendar_presence_correlation()
```

### Integration Flow

```
1. Generate Home Structure
   └── SyntheticHomeGenerator

2. Generate Areas
   └── SyntheticAreaGenerator

3. Generate Devices
   └── SyntheticDeviceGenerator

4. Generate Events
   └── SyntheticEventGenerator

5. Generate External Data (NEW)
   └── SyntheticExternalDataGenerator
       ├── Weather
       ├── Carbon Intensity
       ├── Pricing
       └── Calendar

6. Apply Correlations (Optional)
   └── Individual generator correlation methods
       └── SyntheticCorrelationEngine (validation)
```

---

## Integration Points

### 1. Command-Line Script Integration

**File:** `scripts/generate_synthetic_homes.py`

**Changes:**
- Replaced individual generators with unified orchestrator
- Added configuration flags for each data type
- Updated home JSON structure

**Usage:**
```bash
python scripts/generate_synthetic_homes.py \
    --count 100 \
    --days 90 \
    --enable-weather \
    --enable-carbon \
    --enable-pricing \
    --enable-calendar
```

### 2. Programmatic Integration

**Import:**
```python
from src.training.synthetic_external_data_generator import SyntheticExternalDataGenerator
```

**Integration:**
```python
# After generating events
external_data_generator = SyntheticExternalDataGenerator()
start_date = datetime.now(timezone.utc) - timedelta(days=args.days)

external_data = await external_data_generator.generate_external_data(
    home=home,
    start_date=start_date,
    days=args.days,
    enable_weather=args.enable_weather,
    enable_carbon=args.enable_carbon,
    enable_pricing=args.enable_pricing,
    enable_calendar=args.enable_calendar
)

home['external_data'] = external_data
```

### 3. Correlation Integration

**After generating external data, apply correlations:**

```python
# Apply weather correlations
from src.training.synthetic_weather_generator import SyntheticWeatherGenerator
weather_gen = SyntheticWeatherGenerator()

final_events = weather_gen.correlate_with_hvac(
    external_data['weather'],
    events,
    devices
)
final_events = weather_gen.correlate_with_windows(
    external_data['weather'],
    final_events,
    devices
)

# Apply carbon correlations
from src.training.synthetic_carbon_intensity_generator import SyntheticCarbonIntensityGenerator
carbon_gen = SyntheticCarbonIntensityGenerator()

final_events = carbon_gen.correlate_with_energy_devices(
    external_data['carbon_intensity'],
    final_events,
    devices
)

home['events'] = final_events
```

---

## Data Flow

### Generation Flow

```
Home Metadata
    ↓
Location Extraction (if available)
    ↓
External Data Generation
    ├── Weather (hourly, location-based)
    ├── Carbon Intensity (hourly, region-based)
    ├── Pricing (hourly, region-based)
    └── Calendar (events, home-based)
    ↓
Unified external_data Dictionary
    ↓
Home JSON Structure
```

### Correlation Flow

```
External Data + Device Events
    ↓
Correlation Engine Validation
    ├── Weather-HVAC Correlation
    ├── Energy Correlation
    └── Calendar-Presence Correlation
    ↓
Correlation Results
    ├── Overall Score
    ├── Individual Scores
    └── Violations (if any)
```

---

## Home JSON Structure

### Updated Structure

```json
{
  "home_id": "home_001",
  "home_type": "single_family_house",
  "areas": [...],
  "devices": [...],
  "events": [...],
  "external_data": {
    "weather": [
      {
        "timestamp": "2025-06-15T12:00:00+00:00",
        "temperature": 25.5,
        "humidity": 65.0,
        "condition": "sunny"
      }
    ],
    "carbon_intensity": [
      {
        "timestamp": "2025-06-15T12:00:00+00:00",
        "intensity": 200.0,
        "renewable_percentage": 50.0
      }
    ],
    "pricing": [
      {
        "timestamp": "2025-06-15T12:00:00+00:00",
        "price_per_kwh": 0.20,
        "pricing_tier": "mid-peak"
      }
    ],
    "calendar": [
      {
        "timestamp": "2025-06-15T09:00:00+00:00",
        "event_type": "work",
        "summary": "Work",
        "start": "2025-06-15T09:00:00+00:00",
        "end": "2025-06-15T17:00:00+00:00"
      }
    ]
  }
}
```

### Data Point Frequencies

- **Weather**: Hourly (24 points per day)
- **Carbon Intensity**: Hourly (24 points per day)
- **Pricing**: Hourly (24 points per day)
- **Calendar**: Event-based (varies by home)

---

## Correlation Integration

### Validation Integration

```python
from src.training.synthetic_correlation_engine import SyntheticCorrelationEngine

# After generating external data and events
correlation_engine = SyntheticCorrelationEngine()

results = correlation_engine.validate_all_correlations(
    external_data=home['external_data'],
    device_events=home['events'],
    devices=home['devices']
)

# Use results for quality assurance
if not results['overall_valid']:
    logger.warning(f"Correlation validation failed: {results}")
```

### Correlation Rules

**Weather → HVAC:**
- High temperature (>25°C) → AC should be on
- Low temperature (<18°C) → Heat should be on

**Carbon/Pricing → Energy Devices:**
- Low carbon intensity (<200 gCO2/kWh) → EV charging preferred
- High pricing (>1.5x baseline) → Delay high-energy devices
- Solar peak (low carbon + low price) → Increase renewable usage

**Calendar → Presence → Devices:**
- Away → Security on, lights off
- Home → Comfort settings, lights on
- Work → Reduced device activity

---

## Testing Integration

### Unit Tests

**Test Files:**
- `tests/training/test_synthetic_external_data_generator.py`
- `tests/training/test_synthetic_correlation_engine.py`

**Run Tests:**
```bash
python -m pytest tests/training/test_synthetic_external_data_generator.py -v
python -m pytest tests/training/test_synthetic_correlation_engine.py -v
```

### Integration Tests

**Test File:**
- `tests/training/test_external_data_integration.py`

**Test Coverage:**
- Full pipeline integration
- Data realism validation
- Performance testing
- Correlation validation

**Run Tests:**
```bash
python -m pytest tests/training/test_external_data_integration.py -v
```

### End-to-End Testing

```python
# Test full pipeline
async def test_full_pipeline():
    # Generate home
    home_gen = SyntheticHomeGenerator()
    homes = home_gen.generate_homes(target_count=1)
    home = homes[0]
    
    # Generate complete home with external data
    # ... (full pipeline)
    
    # Validate
    assert 'external_data' in home
    assert 'weather' in home['external_data']
    assert 'carbon_intensity' in home['external_data']
    assert 'pricing' in home['external_data']
    assert 'calendar' in home['external_data']
```

---

## Configuration

### Environment Variables

No environment variables required. All configuration is done via:
- Method parameters (enable flags, location, etc.)
- Command-line arguments (for script usage)

### Default Behavior

- All data types enabled by default
- Location inferred from home metadata if available
- 90 days of data generated by default (configurable)

### Performance Tuning

- **Reduce days**: Generate fewer days for faster execution
- **Disable unused types**: Only enable needed data types
- **Batch processing**: Process homes in batches for better performance

---

## Migration Guide

### From Individual Generators

**Before:**
```python
weather_gen = SyntheticWeatherGenerator()
weather_data = weather_gen.generate_weather(...)

carbon_gen = SyntheticCarbonIntensityGenerator()
carbon_data = carbon_gen.generate_carbon_intensity(...)
```

**After:**
```python
external_gen = SyntheticExternalDataGenerator()
external_data = await external_gen.generate_external_data(...)

weather_data = external_data['weather']
carbon_data = external_data['carbon_intensity']
```

### Backward Compatibility

- Individual generators still available for direct use
- Correlation methods unchanged
- Home JSON structure extended (backward compatible)

---

## Troubleshooting

### Common Issues

**Issue: Missing external_data in home JSON**
- **Solution**: Ensure `generate_external_data()` is called and result assigned to `home['external_data']`

**Issue: Correlation validation fails**
- **Solution**: Check that events and external data have matching timestamps

**Issue: Performance is slow**
- **Solution**: Reduce days, disable unused data types, or process in smaller batches

**Issue: Missing location data**
- **Solution**: Provide location in home metadata or as parameter to `generate_external_data()`

---

## Best Practices

1. **Always validate correlations** after generating external data
2. **Use appropriate time ranges** - generate only what you need
3. **Enable selectively** - disable unused data types for better performance
4. **Provide location data** for more realistic weather and carbon generation
5. **Test integration** with unit and integration tests before production use

---

**Last Updated:** November 2025

