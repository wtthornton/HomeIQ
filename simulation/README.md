# Simulation Framework

Comprehensive simulation framework for validating the complete 3 AM batch workflow and Ask AI conversational flow end-to-end using synthetic data, mocked services, and integrated ML model training/validation.

## Overview

This simulation framework enables pre-production validation of both pipelines (model training → event fetching → pattern detection → suggestion generation → YAML creation → validation) at scale and speed, without real API calls or network dependencies.

**⚠️ CRITICAL: Simulation code is deployed separately from production**
- **Location**: `simulation/` directory at project root (NOT in `services/`)
- **Isolation**: Zero dependencies on production services
- **Deployment**: Separate Docker Compose profile, excluded from production builds
- **Purpose**: Development, testing, CI/CD validation only

## Features

- **Fast Validation**: 4,000% faster than real-time (hours → minutes)
- **Zero API Costs**: No OpenAI calls, no HA API calls
- **High Coverage**: 100+ homes, 50+ queries in minutes
- **Comprehensive Metrics**: Performance, quality, and validation metrics
- **Multiple Report Formats**: JSON, CSV, and HTML reports

## Quick Start

### Using CLI

```bash
# Standard simulation (100 homes, 50 queries)
python simulation/cli.py --mode standard --homes 100 --queries 50

# Quick simulation (10 homes, 5 queries)
python simulation/cli.py --mode quick --homes 10 --queries 5

# Stress test (1000 homes, 500 queries)
python simulation/cli.py --mode stress --homes 1000 --queries 500
```

### Using Scripts

```bash
# Standard run
./simulation/scripts/run_simulation.sh

# Quick run
./simulation/scripts/run_simulation.sh --quick

# Stress test
./simulation/scripts/run_simulation.sh --stress
```

### Using Docker Compose

```bash
# Run simulation in Docker
docker-compose --profile simulation -f simulation/docker-compose.simulation.yml up
```

## Configuration

Configuration is managed via environment variables or `SimulationConfig`:

- `SIMULATION_MODE`: Simulation mode ("quick", "standard", "stress")
- `SIMULATION_SYNTHETIC_HOMES_COUNT`: Number of synthetic homes (default: 100)
- `SIMULATION_MAX_PARALLEL_HOMES`: Maximum parallel homes (default: 10)
- `SIMULATION_MODEL_MODE`: Model mode ("pretrained" or "train_during")

## Architecture

### Core Components

- **SimulationEngine**: Main orchestrator
- **Mock Services**: 8 mock services (InfluxDB, OpenAI, MQTT, Data API, Device Intelligence, HA Conversation, HA Client, Safety Validator)
- **Workflow Simulators**: 3 AM workflow and Ask AI flow simulators
- **Metrics Collector**: Comprehensive metrics collection
- **Validation Framework**: Prompt and YAML validation
- **Batch Processor**: Parallel processing for 100+ homes
- **Report Generator**: JSON, CSV, and HTML reports

### Directory Structure

```
simulation/
├── src/
│   ├── engine/          # Core simulation engine
│   ├── mocks/           # Mock service implementations
│   ├── workflows/       # Workflow simulators
│   ├── metrics/         # Metrics collection
│   ├── validation/      # Validation framework
│   ├── batch/           # Batch processing
│   └── reporting/      # Results aggregation and reporting
├── tests/               # Unit tests
├── scripts/             # Integration scripts
├── cli.py              # CLI interface
├── requirements.txt    # Dependencies
└── README.md          # This file
```

## Output

Simulation results are saved to `simulation_results/` directory (configurable):

- `simulation_report_YYYYMMDD_HHMMSS.json`: Detailed JSON report
- `simulation_report_YYYYMMDD_HHMMSS.csv`: Tabular CSV report
- `simulation_report_YYYYMMDD_HHMMSS.html`: Visual HTML report

## Testing

Run unit tests:

```bash
cd simulation
python -m pytest tests/ -v
```

## Integration

The simulation framework integrates with:

- Production code (imports from `services/ai-automation-service/`)
- Synthetic data generation (Epic AI-11)
- Model training pipeline (`scripts/prepare_for_production.py`)
- YAML validation (production validation logic)

## Epic AI-17

This framework implements Epic AI-17: Simulation Framework Core. See `docs/prd/epic-ai17-simulation-framework-core.md` for full details.
