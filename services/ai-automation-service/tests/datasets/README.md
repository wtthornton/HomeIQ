# Dataset-Based Testing

Tests using [home-assistant-datasets](https://github.com/allenporter/home-assistant-datasets) repository to validate pattern detection, synergy detection, and automation generation.

## Setup

### 1. Clone Dataset Repository

```bash
# Option A: Git submodule (recommended)
git submodule add https://github.com/allenporter/home-assistant-datasets.git ../../tests/datasets

# Option B: Clone separately
git clone https://github.com/allenporter/home-assistant-datasets.git ../../tests/datasets
```

### 2. Set Environment Variables (Optional)

```bash
# If datasets are in a different location
export DATASET_ROOT=/path/to/home-assistant-datasets/datasets

# InfluxDB configuration (for event injection)
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=homeiq-token
export INFLUXDB_ORG=homeiq
export INFLUXDB_BUCKET=home_assistant_events
```

## Running Tests

```bash
# Run all dataset tests
pytest tests/datasets/ -v

# Run specific test
pytest tests/datasets/test_pattern_detection_with_datasets.py::test_pattern_detection_on_synthetic_home -v

# Run with dataset loader only (no InfluxDB required)
pytest tests/datasets/test_pattern_detection_with_datasets.py::test_dataset_loader_can_load_assist_mini -v
```

## Available Datasets

- **assist-mini**: Small home, limited entities (fastest for testing)
- **assist**: Medium home, more complex scenarios
- **intents**: Large home, stress testing
- **automations**: Automation evaluation tasks

## Test Structure

### Phase 1: Foundation ✅
- `test_pattern_detection_with_datasets.py` - Basic pattern detection tests
- `conftest.py` - Pytest fixtures for dataset loading and event injection

### Phase 2: Pattern Testing (Planned)
- Comprehensive pattern detection test suite
- Metrics collection (precision, recall, F1)
- Pattern type diversity testing

### Phase 3: Synergy Testing (Planned)
- Synergy detection test suite
- Relationship type validation
- ML-discovered synergy testing

### Phase 4: Automation Testing (Planned)
- Automation generation validation
- YAML quality testing
- Execution testing

## Usage Examples

### Load a Dataset

```python
from src.testing.dataset_loader import HomeAssistantDatasetLoader

loader = HomeAssistantDatasetLoader()
home_data = await loader.load_synthetic_home("assist-mini")

print(f"Loaded {len(home_data['devices'])} devices")
print(f"Loaded {len(home_data['areas'])} areas")
```

### Inject Events

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
    }
]

await injector.inject_events(events)
injector.disconnect()
```

## Notes

- Tests that require InfluxDB will be skipped if InfluxDB is not available
- Use a separate test bucket in production to avoid polluting real data
- Ground truth patterns/synergies can be added to datasets as `expected_patterns.json` and `expected_synergies.json`

