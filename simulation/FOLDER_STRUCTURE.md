# Simulation Framework Folder Structure

**Status:** 📋 **PLANNING**  
**Purpose:** Document the complete folder structure for simulation framework

---

## Root Structure

```
simulation/
├── src/                          # Source code
│   ├── engine/                   # Core simulation engine (Epic AI-17)
│   │   ├── simulation_engine.py  # Main orchestrator
│   │   ├── config.py             # Configuration management
│   │   ├── dependency_injection.py
│   │   ├── model_training.py
│   │   ├── model_loader.py
│   │   └── batch/                # Batch processing
│   │       ├── processor.py
│   │       ├── parallel_executor.py
│   │       └── progress_tracker.py
│   ├── mocks/                    # Mock service implementations (Epic AI-17)
│   │   ├── influxdb_client.py
│   │   ├── openai_client.py
│   │   ├── mqtt_client.py
│   │   ├── data_api_client.py
│   │   ├── device_intelligence_client.py
│   │   ├── ha_conversation_api.py
│   │   ├── ha_client.py
│   │   └── safety_validator.py
│   ├── workflows/                # Workflow simulators (Epic AI-17)
│   │   ├── daily_analysis_simulator.py
│   │   └── ask_ai_simulator.py
│   ├── validation/               # Validation frameworks (Epic AI-17)
│   │   ├── prompt_validator.py
│   │   ├── prompt_quality.py
│   │   ├── yaml_validator.py
│   │   ├── yaml_metrics.py
│   │   └── ground_truth_comparator.py
│   ├── metrics/                  # Metrics collection (Epic AI-17)
│   │   ├── pattern_metrics.py
│   │   ├── model_metrics.py
│   │   ├── performance_metrics.py
│   │   ├── ask_ai_metrics.py
│   │   └── aggregator.py
│   ├── reporting/                # Report generation (Epic AI-17)
│   │   ├── aggregator.py
│   │   ├── report_generator.py
│   │   └── formatters.py
│   ├── data_generation/          # Synthetic data generation (Epic AI-18)
│   │   ├── data_generation_manager.py
│   │   ├── config.py
│   │   ├── home_generator.py
│   │   ├── ground_truth_generator.py
│   │   └── pattern_extractor.py
│   ├── training_data/            # Training data collection (Epic AI-18)
│   │   ├── collector.py
│   │   ├── validators.py
│   │   ├── exporters.py
│   │   ├── formatters.py
│   │   └── lineage_tracker.py
│   └── retraining/               # Model retraining (Epic AI-18)
│       ├── retraining_manager.py
│       ├── data_sufficiency.py
│       ├── model_evaluator.py
│       └── deployment.py
├── tests/                        # Simulation framework tests
│   ├── test_engine.py
│   ├── test_mocks.py
│   ├── test_model_training.py
│   ├── test_daily_analysis_simulation.py
│   ├── test_ask_ai_simulation.py
│   ├── test_prompt_validation.py
│   ├── test_yaml_validation.py
│   ├── test_metrics.py
│   ├── test_reporting.py
│   ├── test_batch_processing.py
│   ├── test_cli.py
│   ├── test_data_generation_manager.py
│   ├── test_home_generator.py
│   ├── test_ground_truth_generator.py
│   ├── test_collector.py
│   ├── test_exporters.py
│   ├── test_lineage_tracker.py
│   ├── test_retraining_manager.py
│   └── test_model_evaluation.py
├── data/                         # Generated/cached synthetic data
│   ├── homes/                    # Generated home files
│   │   ├── home_001.json
│   │   ├── home_002.json
│   │   └── ...
│   ├── cache/                    # Generation cache
│   │   └── cache_manifest.json
│   └── ground_truth/             # Ground truth annotations
│       ├── home_001_ground_truth.json
│       └── ...
├── training_data/                # Collected training data
│   ├── cycle_1/
│   │   ├── gnn_synergy/
│   │   │   ├── synergies.json
│   │   │   ├── entities.json
│   │   │   └── metadata.json
│   │   ├── soft_prompt/
│   │   │   ├── queries.json
│   │   │   └── metadata.json
│   │   ├── pattern_detection/
│   │   │   ├── patterns.json
│   │   │   └── ground_truth.json
│   │   └── yaml_generation/
│   │       ├── yaml_pairs.json
│   │       └── validation_results.json
│   ├── cycle_2/
│   └── aggregated/               # Combined data across cycles
├── results/                      # Simulation results and reports
│   ├── cycle_1/
│   │   ├── report.json
│   │   ├── report.csv
│   │   └── report.html
│   └── ...
├── docs/                         # Documentation
│   └── USAGE.md                  # Usage guide
├── cli.py                        # CLI interface
├── requirements.txt              # Simulation-only dependencies
├── docker-compose.yml            # Separate Docker Compose (simulation profile)
├── .gitignore                    # Git ignore rules
├── README.md                     # Main README
└── FOLDER_STRUCTURE.md           # This file
```

---

## Key Points

### Production Isolation

1. **Separate Directory**: `simulation/` at project root (NOT in `services/`)
2. **Separate Dependencies**: `simulation/requirements.txt` (NOT in production requirements)
3. **Separate Docker Profile**: `--profile simulation` (excluded from default)
4. **One-Way Imports**: Simulation imports from production (read-only), production never imports from simulation

### Data Storage

1. **Generated Data**: `simulation/data/` (cached, reusable)
2. **Training Data**: `simulation/training_data/` (per-cycle organization)
3. **Results**: `simulation/results/` (reports, metrics)

### Testing

1. **Unit Tests**: `simulation/tests/` (mirrors `simulation/src/` structure)
2. **Integration Tests**: In workflow simulator tests
3. **Coverage**: >90% target for all simulation code

---

## Exclusion from Production

### Docker Compose

Production `docker-compose.yml` does NOT include simulation services:

```yaml
# Production docker-compose.yml - NO simulation profile
services:
  ai-automation-service:
    # ... production services only
```

Simulation `simulation/docker-compose.yml` is separate:

```yaml
# simulation/docker-compose.yml - Separate profile
services:
  simulation-runner:
    profiles: ["simulation"]
    # ... simulation services only
```

### Build Process

1. Production builds: `docker-compose build` (excludes simulation)
2. Simulation builds: `docker-compose -f simulation/docker-compose.yml build` (separate)
3. CI/CD: Simulation tests run separately, not part of production deployment

---

**Last Updated:** January 2025

