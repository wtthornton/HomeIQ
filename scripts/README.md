# HomeIQ Scripts

## Overview

Scripts for managing HomeIQ system operations, including automation management, testing, training, and production deployment.

---

## Scripts Available

### `prepare_for_production.py` ⭐ NEW
**Purpose:** Complete production readiness pipeline - builds, deploys, tests, generates data, trains models, and prepares for production

**Usage:**
```bash
# Full pipeline
python scripts/prepare_for_production.py

# Quick mode (smaller dataset)
python scripts/prepare_for_production.py --quick

# Skip specific steps
python scripts/prepare_for_production.py --skip-build --skip-deploy

# Verbose output
python scripts/prepare_for_production.py --verbose
```

**Features:**
- **Pre-flight validation** (Epic 42): Validates dependencies, environment variables, and services before starting
- Builds all Docker images
- Deploys all services
- Runs comprehensive smoke tests
- Generates synthetic test data (100 homes, 90 days by default)
  - **Progress reporting:** Shows "X of Y homes" progress with ETA during generation
  - **Real-time output:** Streams progress updates as data is generated
- Trains all ML models (home type classifier, device intelligence, GNN synergy, soft prompt)
  - **Critical vs Optional classification** (Epic 42): Clear distinction between required and enhancement models
- Saves and verifies trained models
- Generates production readiness report with enhanced status reporting
- **Enhanced error messages** (Epic 42): What/Why/How to Fix format with actionable instructions

**Options:**
- `--skip-build` - Skip Docker build step
- `--skip-deploy` - Skip deployment step
- `--skip-smoke` - Skip smoke tests
- `--skip-generation` - Skip test data generation
- `--skip-training` - Skip model training
- `--skip-validation` - Skip pre-flight dependency validation (advanced users only)
- `--quick` - Use smaller dataset (10 homes, 7 days)
- `--count N` - Number of synthetic homes to generate (overrides default/quick)
- `--days N` - Number of days of events per home (overrides default/quick)
- `--verbose` - Enable detailed logging
- `--output-dir` - Custom output directory for reports

**Output:**
- Production readiness report: `implementation/production_readiness_report_{timestamp}.md`
- Smoke test results: `test-results/smoke_test_results_{timestamp}.json`
- Model manifest: `test-results/model_manifest_{timestamp}.json`

**Requirements:**
- Docker and Docker Compose (validated before execution)
- Python 3.10+
- All service dependencies installed (validated before execution)
- Environment variables configured (validated before execution)
  - Required: `HA_HTTP_URL`, `HA_TOKEN`
  - Optional: `OPENAI_API_KEY` (for GNN synergy and soft prompt models)

---

### `delete_all_automations.py` ⭐
**Purpose:** Delete ALL automations from Home Assistant using the API

**Usage:**
```bash
python scripts/delete_all_automations.py
```

**Features:**
- Retrieves all automation entities
- Shows what will be deleted
- Requires confirmation ("DELETE ALL")
- Uses correct API endpoint and parameter format
- Reports success/failure for each deletion

**Requirements:**
- `.env` file with `HA_HTTP_URL` and `HA_TOKEN`
- Long-lived access token with appropriate permissions

---

## Documentation

### `HOME_ASSISTANT_AUTOMATION_API_RESEARCH.md`
**Purpose:** Comprehensive research findings on automation API

**Contents:**
- Critical discovery: API deletion IS possible
- Correct endpoint and parameter format
- Verification results with actual test data
- What works vs. what doesn't
- Best practices and recommendations

---

## Key Discovery (October 2025)

### ✅ API Deletion EXISTS!

**Correct Method:**
```
DELETE /api/config/automation/config/{id-from-attributes}
```

**Critical Finding:**
- Use the `id` from automation's `attributes` field
- NOT the `entity_id`
- Tested and verified on Home Assistant 2025.10.x

**Example:**
```python
automation = {
    "entity_id": "automation.test",
    "attributes": {
        "id": "test_abc123"  # ← Use THIS!
    }
}

# This works:
DELETE /api/config/automation/config/test_abc123  # ✅ 200 OK

# These don't work:
DELETE /api/config/automation/config/automation.test  # ❌ 400 Error
DELETE /api/config/automation/config/test            # ❌ 400 Error
```

---

## Test Results

**Date:** October 20, 2025  
**Home Assistant Version:** 2025.10.x  
**Status:** ✅ SUCCESS

**Results:**
- Connected to Home Assistant at `192.168.1.86:8123`
- Found 28 automations
- Disabled 28 automations initially (wrong method)
- Deleted 27 automations via API (correct method - 1 already deleted)
- Verified: 0 automations remaining

**Final Status:**
```
Remaining automations: 0
*** ALL AUTOMATIONS DELETED SUCCESSFULLY! ***
```

---

## Configuration

### `.env` File Required
```bash
# Home Assistant Configuration
HA_HTTP_URL=http://192.168.1.86:8123
HA_TOKEN=your_long_lived_access_token_here
```

### How to Get Token
1. Open Home Assistant
2. Go to Profile → Security
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Copy token to `.env` file

---

## Why This Matters

### Previous Understanding (Wrong)
- Many online sources claimed no API deletion exists
- Only disable/enable was thought possible
- Manual file editing required for deletion

### Current Reality (Correct)
- API deletion DOES exist
- Requires using correct parameter (`id` from attributes)
- Not well documented
- Works reliably when used correctly

---

## Related Scripts

### Testing and Training
- `run_full_test_and_training.py` - Test data generation and model training pipeline
- `simple-unit-tests.py` - Unit test runner

### Deployment
- `deploy.sh` - Production deployment script
- `deploy-with-validation.sh` - Deployment with validation checks

## Files

- `prepare_for_production.py` - Production readiness orchestration script
- `delete_all_automations.py` - Main script to delete all automations
- `HOME_ASSISTANT_AUTOMATION_API_RESEARCH.md` - Detailed research findings
- `README.md` - This file

---

## References

- [Home Assistant API Documentation](https://developers.home-assistant.io/docs/api/rest/)
- [Community Discussion on Automation API](https://community.home-assistant.io/t/rest-api-docs-for-automations/119997)
- [Context7 Home Assistant Docs](https://context7.com/home-assistant/core)

---

**Last Updated:** November 28, 2025  
**Status:** ✅ Verified and Working  
**Epic 42:** Enhanced with pre-flight validation, critical/optional classification, and improved error messages

