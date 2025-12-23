# Dataset Testing Data Flow

## Simple Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Test Setup                                                 │
│    - Load dataset from /app/datasets/home-assistant-datasets │
│    - Initialize HomeAssistantDatasetLoader                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Dataset Loading                                            │
│    HomeAssistantDatasetLoader.load_synthetic_home()           │
│    ├─ Parse YAML files (home.yaml, devices, areas)           │
│    ├─ Extract devices, areas, events                         │
│    └─ Return: {devices, areas, events, expected_patterns}   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Event Injection (Optional)                                 │
│    EventInjector.inject_events()                              │
│    └─ Write synthetic events to InfluxDB                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Pattern Detection                                         │
│    Pattern Detectors (CoOccurrence, TimeOfDay, MultiFactor)  │
│    └─ Analyze events → Detect patterns                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Metrics Calculation                                       │
│    calculate_pattern_metrics()                                │
│    ├─ Compare detected vs. expected (ground truth)          │
│    ├─ Calculate: Precision, Recall, F1                      │
│    └─ Return: {TP, FP, FN, precision, recall, f1}           │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

1. **Dataset Source**: `/app/datasets/home-assistant-datasets/datasets/`
2. **Loader**: `HomeAssistantDatasetLoader` - Parses YAML, extracts data
3. **Injector**: `EventInjector` - Writes events to InfluxDB
4. **Detectors**: Pattern detection algorithms
5. **Metrics**: Compare results against ground truth

## Test Flow

```
Test → Load Dataset → Inject Events → Detect Patterns → Calculate Metrics → Assert Results
```

