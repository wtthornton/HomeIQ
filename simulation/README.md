# Simulation Framework

**Status:** 📋 **PLANNING**  
**Epics:** [AI-17](../docs/prd/epic-ai17-simulation-framework-core.md), [AI-18](../docs/prd/epic-ai18-simulation-data-generation-training.md)  
**Purpose:** End-to-end workflow validation and training data collection for AI Automation Service

---

## ⚠️ IMPORTANT: Production Isolation

**This simulation framework is completely isolated from production deployment.**

- **Location**: `simulation/` directory at project root (NOT in `services/`)
- **Deployment**: Separate Docker Compose profile (`--profile simulation`)
- **Exclusion**: NOT included in production Docker images or builds
- **Purpose**: Development, testing, CI/CD validation, model training data collection only

---

## Overview

The simulation framework provides:

1. **Complete Workflow Validation**: Test 3 AM and Ask AI workflows end-to-end
2. **Mock Services**: All external APIs mocked (OpenAI, HA, InfluxDB, etc.)
3. **Synthetic Data Generation**: Generate multiple homes with varied characteristics
4. **Training Data Collection**: Collect all data needed for model training
5. **Automated Model Retraining**: Continuously improve models with collected data
6. **Validation & Scoring**: Comprehensive validation and quality scoring

---

## Folder Structure

```
simulation/
├── src/
│   ├── engine/              # Core simulation engine
│   ├── mocks/               # Mock service implementations
│   ├── workflows/           # Workflow simulators (3 AM, Ask AI)
│   ├── validation/          # Validation frameworks
│   ├── metrics/             # Metrics collection
│   ├── reporting/           # Report generation
│   ├── data_generation/     # Synthetic data generation (Epic AI-18)
│   ├── training_data/       # Training data collection (Epic AI-18)
│   ├── retraining/          # Model retraining (Epic AI-18)
│   └── config.py            # Configuration management
├── tests/                   # Simulation framework tests
├── data/                    # Generated/cached synthetic data
├── training_data/           # Collected training data
├── results/                 # Simulation results and reports
├── cli.py                   # CLI interface
├── requirements.txt         # Simulation-only dependencies
├── docker-compose.yml       # Separate Docker Compose (simulation profile)
└── README.md                # This file
```

---

## Quick Start

```bash
# Install simulation dependencies
pip install -r simulation/requirements.txt

# Run 3 AM workflow simulation
python simulation/cli.py run-3am --homes 50 --mode standard

# Run Ask AI workflow simulation
python simulation/cli.py run-ask-ai --datasets all --mode standard

# Run continuous improvement loop
python simulation/cli.py improve --max-cycles 10 --target-score 95

# Generate synthetic homes
python simulation/cli.py generate-homes --count 50 --days 90
```

---

## Documentation

- **Epic AI-17**: [Simulation Framework Core](../docs/prd/epic-ai17-simulation-framework-core.md)
- **Epic AI-18**: [Simulation Data Generation & Training Collection](../docs/prd/epic-ai18-simulation-data-generation-training.md)
- **Usage Guide**: `simulation/docs/USAGE.md` (coming soon)

---

## Production Exclusion

This simulation framework is **NOT** part of production deployment:

- Excluded from production Docker builds
- Separate Docker Compose profile
- No production service dependencies
- Zero impact on production runtime

---

**Last Updated:** January 2025

