# Dataset Testing Guide

Complete guide for testing pattern detection, synergy detection, and automation generation using Home Assistant datasets.

## Prerequisites

1. **Docker Services Running:**
   ```powershell
   docker-compose up -d ai-automation-service automation-miner influxdb data-api
   ```

2. **Dataset Repository:**
   The tests require the `home-assistant-datasets` repository to be cloned.

## Setup

### Step 1: Clone Dataset Repository

**Option A: Using Setup Script (Recommended)**
```powershell
cd services/ai-automation-service
.\scripts\setup_datasets.ps1
```

**Option B: Manual Clone**
```powershell
# Create datasets directory
New-Item -ItemType Directory -Path tests\datasets -Force

# Clone repository
cd tests\datasets
git clone https://github.com/allenporter/home-assistant-datasets.git

# Create junction to datasets folder
New-Item -ItemType Junction -Path datasets -Target home-assistant-datasets\datasets
```

**Option C: Set Environment Variable**
```powershell
$env:DATASET_ROOT = "C:\path\to\home-assistant-datasets\datasets"
```

### Step 2: Verify Setup

```powershell
# Check if datasets are available
Test-Path services/ai-automation-service/tests/datasets/datasets/assist-mini/home.yaml
```

## Running Tests

### Option 1: Run Tests Locally (Python)

```powershell
cd services/ai-automation-service

# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio

# Run all dataset tests
pytest tests/datasets/ -v

# Run specific test file
pytest tests/datasets/test_pattern_detection_with_datasets.py -v

# Run specific test
pytest tests/datasets/test_pattern_detection_with_datasets.py::test_dataset_loader_can_load_assist_mini -v

# Run with output
pytest tests/datasets/ -v -s
```

### Option 2: Run Tests in Docker Container

```powershell
# Run tests inside the container
docker exec -it ai-automation-service bash
cd /app
pytest tests/datasets/ -v

# Or run directly from host
docker exec ai-automation-service pytest tests/datasets/ -v
```

### Option 3: Run Tests with Docker Compose

```powershell
# Run tests in a new container
docker-compose run --rm ai-automation-service pytest tests/datasets/ -v
```

## Available Test Suites

### 1. Basic Pattern Detection Tests
**File:** `test_pattern_detection_with_datasets.py`

**Tests:**
- `test_dataset_loader_can_load_assist_mini` - Verify dataset loading
- `test_pattern_detection_on_synthetic_home` - Basic pattern detection

**Run:**
```powershell
pytest tests/datasets/test_pattern_detection_with_datasets.py -v
```

### 2. Comprehensive Pattern Detection Tests
**File:** `test_pattern_detection_comprehensive.py`

**Tests:**
- `test_pattern_detection_accuracy_co_occurrence` - Co-occurrence pattern accuracy
- `test_pattern_detection_accuracy_time_of_day` - Time-of-day pattern accuracy
- `test_pattern_detection_accuracy_multi_factor` - Multi-factor pattern accuracy
- `test_pattern_detection_with_blueprint_validation` - Blueprint-validated patterns

**Run:**
```powershell
pytest tests/datasets/test_pattern_detection_comprehensive.py -v
```

### 3. Comprehensive Synergy Detection Tests
**File:** `test_synergy_detection_comprehensive.py`

**Tests:**
- `test_synergy_detection_accuracy` - All 16 relationship types
- `test_ml_discovered_synergies` - ML-discovered synergies
- `test_synergy_detection_on_multiple_datasets` - Multiple dataset validation

**Run:**
```powershell
pytest tests/datasets/test_synergy_detection_comprehensive.py -v
```

### 4. Automation Generation Tests
**File:** `test_automation_generation_comprehensive.py`

**Tests:**
- `test_automation_yaml_quality` - YAML structure validation
- `test_automation_entity_resolution` - Entity resolution accuracy
- `test_automation_suggestion_ranking` - Suggestion ranking quality

**Run:**
```powershell
pytest tests/datasets/test_automation_generation_comprehensive.py -v
```

### 5. Blueprint Correlation Tests
**File:** `test_blueprint_correlation.py`

**Tests:**
- `test_blueprint_correlator_initialization` - Correlator setup
- `test_find_matching_blueprints_for_pattern` - Pattern-to-blueprint matching
- `test_blueprint_dataset_correlation_workflow` - End-to-end workflow

**Run:**
```powershell
pytest tests/datasets/test_blueprint_correlation.py -v
```

## Test Configuration

### Environment Variables

```powershell
# InfluxDB Configuration (for event injection)
$env:INFLUXDB_URL = "http://localhost:8086"
$env:INFLUXDB_TOKEN = "homeiq-token"
$env:INFLUXDB_ORG = "homeiq"
$env:INFLUXDB_BUCKET = "home_assistant_events"

# Dataset Location (if not in default location)
$env:DATASET_ROOT = "C:\path\to\datasets"

# Automation Miner URL (for blueprint correlation)
$env:AUTOMATION_MINER_URL = "http://localhost:8029"
```

### Test Fixtures

The `conftest.py` file provides:
- `dataset_root` - Path to dataset directory
- `dataset_loader` - HomeAssistantDatasetLoader instance
- `event_injector` - EventInjector for InfluxDB
- `loaded_dataset` - Pre-loaded assist-mini dataset

## Understanding Test Results

### Pattern Detection Metrics

Tests output precision, recall, and F1 scores:
```
Pattern Detection Results:
  Precision: 0.85
  Recall: 0.80
  F1 Score: 0.82
  True Positives: 42
  False Positives: 7
  False Negatives: 10
```

### Synergy Detection Metrics

Tests validate relationship types:
```
Synergy Detection Results:
  Total Synergies: 156
  Pattern-Validated: 142 (91.0%)
  ML-Discovered: 14 (9.0%)
  Relationship Types: 12/16
```

### Automation Generation Metrics

Tests validate YAML quality:
```
Automation Generation Results:
  YAML Quality: 4.8/5.0
  Entity Resolution: 4.9/5.0
  Test Pass Rate: 96%
```

## Troubleshooting

### Issue: "Dataset root not found"

**Solution:**
1. Clone the repository using `setup_datasets.ps1`
2. Or set `DATASET_ROOT` environment variable
3. Or place datasets at `tests/datasets/datasets/`

### Issue: "InfluxDB connection failed"

**Solution:**
1. Ensure InfluxDB is running: `docker-compose ps influxdb`
2. Check environment variables match docker-compose.yml
3. Tests will skip if InfluxDB is unavailable

### Issue: "ModuleNotFoundError: No module named 'src.testing'"

**Solution:**
1. Ensure you're running from `services/ai-automation-service` directory
2. Or use Docker: `docker exec ai-automation-service pytest ...`
3. Verify the service was rebuilt: `docker-compose build ai-automation-service`

### Issue: "Automation miner not available"

**Solution:**
1. Start automation-miner: `docker-compose up -d automation-miner`
2. Tests will skip blueprint correlation if miner is unavailable
3. Check logs: `docker-compose logs automation-miner`

## Quick Test Commands

```powershell
# Quick smoke test (no InfluxDB required)
pytest tests/datasets/test_pattern_detection_with_datasets.py::test_dataset_loader_can_load_assist_mini -v

# Full pattern detection test
pytest tests/datasets/test_pattern_detection_comprehensive.py -v -s

# Full synergy detection test
pytest tests/datasets/test_synergy_detection_comprehensive.py -v -s

# Full automation generation test
pytest tests/datasets/test_automation_generation_comprehensive.py -v -s

# All tests with coverage
pytest tests/datasets/ -v --cov=src.testing --cov-report=term-missing
```

## Next Steps

1. **Run Basic Tests:** Start with `test_pattern_detection_with_datasets.py`
2. **Review Metrics:** Check precision/recall scores
3. **Run Comprehensive Tests:** Validate all pattern types
4. **Test Blueprint Correlation:** Verify blueprint integration
5. **Generate Report:** Use metrics to identify improvements

## Additional Resources

- **Integration Plan:** `implementation/analysis/HOME_ASSISTANT_DATASETS_INTEGRATION_PLAN.md`
- **Quick Start:** `implementation/analysis/HOME_ASSISTANT_DATASETS_QUICK_START.md`
- **Dataset README:** `tests/datasets/README.md`
- **Repository:** https://github.com/allenporter/home-assistant-datasets

