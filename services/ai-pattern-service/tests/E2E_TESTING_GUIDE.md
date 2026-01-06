# E2E Testing Guide for AI Pattern Service

## Overview

This guide documents the end-to-end (E2E) tests for verifying deployed AI Pattern Service functionality.

## Test Files

### E2E Tests
- **`test_e2e_patterns_synergies.py`** - Comprehensive e2e tests for deployed service verification
  - Health endpoint tests
  - Pattern API endpoint tests
  - Synergy API endpoint tests
  - Database connectivity tests
  - End-to-end flow tests
  - Performance tests

### Integration Tests (Mocked)
- **`test_integration_synergy_improvements.py`** - Integration tests with mocked dependencies
  - Tests 2025 synergy improvements (XAI, RL, GNN, etc.)
  - Uses TestClient (not real HTTP)
  - Good for development but doesn't verify deployed service

## Running E2E Tests

### Prerequisites
1. Service must be running (local or deployed)
2. Set `PATTERN_SERVICE_URL` environment variable if service is not on `http://localhost:8020`

### Run All E2E Tests
```bash
cd services/ai-pattern-service
pytest -m e2e -v
```

### Run Specific E2E Test Categories
```bash
# Health endpoints only
pytest -m e2e tests/test_e2e_patterns_synergies.py::TestE2EHealthEndpoints -v

# Pattern endpoints only
pytest -m e2e tests/test_e2e_patterns_synergies.py::TestE2EPatternEndpoints -v

# Synergy endpoints only
pytest -m e2e tests/test_e2e_patterns_synergies.py::TestE2ESynergyEndpoints -v

# Performance tests (slow)
pytest -m e2e -m slow tests/test_e2e_patterns_synergies.py::TestE2EPerformance -v
```

### Run Against Deployed Service
```bash
# Set service URL
export PATTERN_SERVICE_URL=http://your-deployed-service:8020

# Run e2e tests
pytest -m e2e -v
```

## What E2E Tests Verify

### 1. Health Endpoints ✅
- `/health` - Service health status
- `/ready` - Readiness check
- `/live` - Liveness check
- `/database/integrity` - Database integrity status

### 2. Pattern API Endpoints ✅
- `GET /api/v1/patterns/list` - List patterns with filters
- `GET /api/v1/patterns/stats` - Pattern statistics

### 3. Synergy API Endpoints ✅
- `GET /api/v1/synergies/statistics` - Synergy statistics
- `GET /api/v1/synergies` - List synergies (if available)

### 4. Database Connectivity ✅
- Database connection via health endpoint
- Database integrity checks

### 5. End-to-End Flows ✅
- Pattern detection flow (health → list → stats)
- Synergy detection flow (health → statistics)
- Error handling for invalid requests

### 6. Service Integration ✅
- Data-API integration (graceful degradation)
- Service startup time verification

### 7. Performance ✅
- Pattern list endpoint performance (<5s)
- Synergy statistics performance (<3s)

## Integration Tests vs E2E Tests

### Integration Tests (`test_integration_synergy_improvements.py`)
- **Purpose**: Test business logic with mocked dependencies
- **Uses**: TestClient (FastAPI test client, no real HTTP)
- **When to use**: During development, CI/CD unit test phase
- **Limitations**: Doesn't verify deployed service, network, or real dependencies

### E2E Tests (`test_e2e_patterns_synergies.py`)
- **Purpose**: Verify deployed service works correctly
- **Uses**: Real HTTP client (httpx) hitting actual endpoints
- **When to use**: Pre-deployment verification, post-deployment smoke tests
- **Advantages**: Verifies real deployment, network, dependencies, configuration

## How to Know Deployed Code is Working

### Quick Verification (Smoke Tests)
```bash
# 1. Health check
curl http://localhost:8020/health

# 2. Pattern stats
curl http://localhost:8020/api/v1/patterns/stats

# 3. Synergy stats
curl http://localhost:8020/api/v1/synergies/statistics
```

### Full E2E Test Suite
```bash
# Run all e2e tests
pytest -m e2e -v

# Expected: All tests pass
```

### Using tapps-agents for Verification
```bash
# Review e2e tests
python -m tapps_agents.cli reviewer review tests/test_e2e_patterns_synergies.py

# Score e2e tests
python -m tapps_agents.cli reviewer score tests/test_e2e_patterns_synergies.py

# Run e2e tests with coverage
pytest -m e2e --cov=src --cov-report=html
```

## Test Coverage

### Current Coverage
- ✅ Health endpoints: 100%
- ✅ Pattern endpoints: 80% (list, stats)
- ✅ Synergy endpoints: 60% (statistics, list if available)
- ✅ Database connectivity: 100%
- ✅ Error handling: 70%
- ✅ Performance: 50% (basic tests)

### Missing Coverage
- ❌ Pattern detection trigger endpoint (if exists)
- ❌ Synergy detection trigger endpoint (if exists)
- ❌ Scheduler endpoints (if exposed)
- ❌ Community pattern endpoints
- ❌ Feedback submission flow
- ❌ Database repair endpoint

## CI/CD Integration

### Pre-Deployment
```bash
# Run unit + integration tests
pytest -m "unit or integration" -v

# Run e2e tests against staging
PATTERN_SERVICE_URL=http://staging:8020 pytest -m e2e -v
```

### Post-Deployment
```bash
# Run e2e tests against production
PATTERN_SERVICE_URL=http://production:8020 pytest -m e2e -v
```

## Troubleshooting

### Service Not Responding
- Check service is running: `docker ps | grep ai-pattern-service`
- Check logs: `docker logs homeiq-ai-pattern-service`
- Verify port: Service runs on port 8020

### Tests Failing
- Verify service URL is correct
- Check service health: `curl http://localhost:8020/health`
- Review service logs for errors
- Verify database is accessible

### Performance Issues
- Check service resource usage
- Verify database performance
- Check data-api connectivity

## Related Documentation

- [Test README](README.md) - General test structure
- [API Documentation](../docs/API_DOCUMENTATION.md) - API endpoint details
- [Deployment Guide](../docs/DEPLOYMENT_GUIDE.md) - Deployment instructions
