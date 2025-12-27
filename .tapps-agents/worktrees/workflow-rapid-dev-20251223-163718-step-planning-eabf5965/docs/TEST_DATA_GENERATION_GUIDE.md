# Test Data Generation Guide

This guide explains how to create test data for HomeIQ using synthetic home generation scripts.

## Overview

HomeIQ provides multiple methods for generating test data:

1. **Synthetic Home Generation** - Template-based generation of complete homes with devices, areas, events, and external data
2. **Dataset Loading** - Using existing home-assistant-datasets repository
3. **Event Injection** - Manually injecting events into InfluxDB

---

## Method 1: Synthetic Home Generation (Recommended)

### Quick Start

Generate 100 synthetic homes with 90 days of events:

```bash
cd services/ai-automation-service
python scripts/generate_synthetic_homes.py \
    --count 100 \
    --output tests/datasets/synthetic_homes \
    --days 90
```

### Command Options

```bash
python scripts/generate_synthetic_homes.py \
    --count 100              # Number of homes to generate (default: 100)
    --output <path>          # Output directory (default: tests/datasets/synthetic_homes)
    --days 90                # Days of events per home (default: 90)
    --home-types <types>     # Specific home types to generate (optional)
    --enable-weather         # Enable weather data (default: True)
    --disable-weather        # Disable weather data
    --enable-carbon          # Enable carbon intensity data (default: True)
    --disable-carbon         # Disable carbon intensity data
    --enable-pricing         # Enable electricity pricing (default: True)
    --disable-pricing        # Disable electricity pricing
    --enable-calendar        # Enable calendar events (default: True)
    --disable-calendar       # Disable calendar events
    --enable-openai          # Enable OpenAI enhancement (optional, costs money)
    --enhancement-percentage 0.20  # % of homes enhanced with OpenAI (default: 0.20)
```

### What Gets Generated

Each synthetic home JSON file includes:

- **Home Metadata**
  - Home type (single-family, apartment, condo, townhouse, etc.)
  - Size category (small, medium, large, extra-large)
  - Location information

- **Areas**
  - Room/area definitions (kitchen, living room, bedroom, etc.)

- **Devices**
  - Device entities with realistic names and types
  - Device metadata (manufacturer, model, capabilities)

- **Events** (90 days by default)
  - State changes
  - Device activations
  - Usage patterns
  - Time-based correlations

- **External Data** (optional)
  - Weather data (temperature, conditions, forecasts)
  - Carbon intensity (grid carbon footprint)
  - Electricity pricing (time-of-use rates)
  - Calendar events (work schedules, routines)

### Home Type Distribution

By default, generates homes with this distribution:

- Single-family house: 30 homes (30%)
- Apartment: 20 homes (20%)
- Condo: 15 homes (15%)
- Townhouse: 10 homes (10%)
- Cottage: 10 homes (10%)
- Studio: 5 homes (5%)
- Multi-story: 5 homes (5%)
- Ranch house: 5 homes (5%)

### Size Distribution

- Small (10-20 devices): 30 homes (30%)
- Medium (20-40 devices): 40 homes (40%)
- Large (40-60 devices): 20 homes (20%)
- Extra-large (60+ devices): 10 homes (10%)

### Example Output

```json
{
  "home_id": "home_001",
  "home_type": "single_family_house",
  "size_category": "medium",
  "areas": [
    {"area_id": "kitchen", "name": "Kitchen", ...},
    {"area_id": "living_room", "name": "Living Room", ...}
  ],
  "devices": [
    {"entity_id": "light.kitchen", "device_type": "light", ...},
    {"entity_id": "sensor.temperature_kitchen", "device_type": "sensor", ...}
  ],
  "events": [
    {"entity_id": "light.kitchen", "state": "on", "timestamp": "...", ...},
    ...
  ],
  "external_data": {
    "weather": [...],
    "carbon_intensity": [...],
    "pricing": [...],
    "calendar": [...]
  }
}
```

### Time and Cost Estimates

- **Template-based generation**: 10-30 minutes for 100 homes
- **With 90 days of events**: +5-15 minutes
- **Cost**: $0 (no API calls required)
- **With OpenAI enhancement**: Additional time + API costs (~$0.50-2.00 for 100 homes)

---

## Method 2: Loading Synthetic Homes into Home Assistant

After generating synthetic homes, you can load them into a Home Assistant instance for testing:

```bash
cd services/ai-automation-service
python scripts/load_synthetic_home_to_ha.py \
    --home tests/datasets/synthetic_homes/home_001.json \
    --ha-url http://localhost:8123 \
    --ha-token <your-token>
```

### Environment Variables

```bash
export HA_TEST_URL=http://localhost:8123
export HA_TEST_TOKEN=your-long-lived-access-token
```

---

## Method 3: Using Existing Datasets

HomeIQ supports using datasets from the [home-assistant-datasets](https://github.com/allenporter/home-assistant-datasets) repository.

### Setup

```bash
# Option A: Git submodule (recommended)
git submodule add https://github.com/allenporter/home-assistant-datasets.git services/tests/datasets

# Option B: Clone separately
git clone https://github.com/allenporter/home-assistant-datasets.git services/tests/datasets
```

### Available Datasets

- **assist-mini**: Small home, limited entities (fastest for testing)
- **assist**: Medium home, more complex scenarios
- **intents**: Large home, stress testing
- **automations**: Automation evaluation tasks

### Loading a Dataset

```python
from src.testing.dataset_loader import HomeAssistantDatasetLoader

loader = HomeAssistantDatasetLoader()
home_data = await loader.load_synthetic_home("assist-mini")

print(f"Loaded {len(home_data['devices'])} devices")
print(f"Loaded {len(home_data['areas'])} areas")
```

---

## Method 4: Event Injection into InfluxDB

You can inject events directly into InfluxDB for testing:

```python
from src.testing.event_injector import EventInjector

injector = EventInjector()
injector.connect()

events = [
    {
        'entity_id': 'light.kitchen',
        'state': 'on',
        'timestamp': '2025-01-15T18:00:00Z',
        'event_type': 'state_changed'
    },
    # ... more events
]

await injector.inject_events(events)
injector.disconnect()
```

### Environment Variables

```bash
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=homeiq-token
export INFLUXDB_ORG=homeiq
export INFLUXDB_BUCKET=home_assistant_events
```

---

## Common Use Cases

### Generate Small Test Dataset

For quick testing, generate just 5 homes:

```bash
python scripts/generate_synthetic_homes.py \
    --count 5 \
    --days 7 \
    --output tests/datasets/synthetic_homes_test
```

### Generate Training Dataset

For ML model training, generate 100 homes with full external data:

```bash
python scripts/generate_synthetic_homes.py \
    --count 100 \
    --days 90 \
    --enable-weather \
    --enable-carbon \
    --enable-pricing \
    --enable-calendar \
    --output tests/datasets/synthetic_homes_training
```

### Generate Specific Home Types

Generate only apartments and condos:

```bash
python scripts/generate_synthetic_homes.py \
    --count 20 \
    --home-types apartment condo \
    --days 30
```

### Generate Without External Data

For faster generation without external data:

```bash
python scripts/generate_synthetic_homes.py \
    --count 50 \
    --disable-weather \
    --disable-carbon \
    --disable-pricing \
    --disable-calendar
```

---

## Running Inside Docker

If you need to run generation inside a Docker container:

```bash
docker compose exec ai-automation-service bash
cd /app
python scripts/generate_synthetic_homes.py --count 10 --days 7
```

---

## Troubleshooting

### Issue: Script not found

**Solution**: Make sure you're in the correct directory:
```bash
cd services/ai-automation-service
```

### Issue: Module import errors

**Solution**: Ensure Python can find the src modules:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/services/ai-automation-service/src"
```

### Issue: InfluxDB connection errors

**Solution**: Verify InfluxDB is running and environment variables are set:
```bash
docker compose ps influxdb
echo $INFLUXDB_URL
echo $INFLUXDB_TOKEN
```

### Issue: Out of memory

**Solution**: Generate fewer homes at a time or reduce days:
```bash
python scripts/generate_synthetic_homes.py --count 10 --days 30
```

---

## Next Steps

After generating test data:

1. **Load into Home Assistant** (optional):
   ```bash
   python scripts/load_synthetic_home_to_ha.py --home <path>
   ```

2. **Inject events into InfluxDB** (optional):
   - Use EventInjector class in Python
   - Or write events via data-api service

3. **Run tests**:
   ```bash
   pytest tests/datasets/test_pattern_detection_with_datasets.py
   ```

4. **Train models** (if generating training data):
   ```bash
   python scripts/train_home_type_classifier.py \
       --synthetic-homes tests/datasets/synthetic_homes
   ```

---

## References

- **Synthetic Home Generation Plan**: `implementation/analysis/SYNTHETIC_HOME_GENERATION_AND_TRAINING_PLAN.md`
- **External Data Generation Design**: `implementation/analysis/SYNTHETIC_EXTERNAL_DATA_GENERATION_DESIGN.md`
- **Dataset Testing README**: `services/ai-automation-service/tests/datasets/README.md`
- **Main Generation Script**: `services/ai-automation-service/scripts/generate_synthetic_homes.py`

---

**Last Updated**: November 2025  
**Status**: Production Ready

