# Epic 41: Testing Checklist

**Date:** January 2025  
**Status:** Ready for Execution  
**Purpose:** Verify all Epic 41 dependency updates work correctly

---

## Pre-Deployment Testing

### ✅ 1. Dependency Verification (COMPLETE)

- [x] Created verification script: `scripts/verify-epic41-dependencies.py`
- [x] Updated all production requirements files
- [x] Fixed remaining version conflicts

**Commands:**
```bash
# List all versions
python scripts/verify-epic41-dependencies.py --list-versions

# Check for conflicts
python scripts/verify-epic41-dependencies.py --check-conflicts
```

### 2. Dependency Resolution Tests

**Objective:** Verify all updated dependencies can be installed without conflicts

**Tests:**
- [ ] Run `pip check` on all updated requirements.txt files
- [ ] Verify Docker builds succeed for all services
- [ ] Check for dependency conflicts in pip install logs

**Commands:**
```bash
# Test individual service builds
cd services/ml-service && docker build -t test-ml-service .
cd services/openvino-service && docker build -t test-openvino-service .
cd services/ai-automation-service && docker build -t test-ai-automation-service .
cd services/data-api && docker build -t test-data-api .

# Test all services
docker-compose build --no-cache
```

### 3. Unit Tests

**Objective:** Verify Python services work with updated dependencies

**Target Services:**
- [ ] `ml-service` - Test NumPy 1.26.x compatibility
- [ ] `openvino-service` - Test PyTorch 2.4.0+cpu compatibility
- [ ] `ai-automation-service` - Test all dependency updates
- [ ] `data-api` - Test FastAPI 0.115.x compatibility
- [ ] `admin-api` - Test FastAPI 0.115.x compatibility

**Commands:**
```bash
# Run Python unit tests
python scripts/simple-unit-tests.py --python-only

# Test specific services
cd services/ml-service && pytest -v
cd services/openvino-service && pytest -v
cd services/data-api && pytest -v
cd services/ai-automation-service && pytest -v
```

### 4. Frontend Build Tests

**Objective:** Verify frontend works with Node.js 20 and updated Playwright

**Target Services:**
- [ ] `health-dashboard` - Test with Node.js 20 LTS
- [ ] `ai-automation-ui` - Test with Node.js 20 LTS
- [ ] E2E tests - Test with Playwright 1.56.1

**Commands:**
```bash
# Build health-dashboard
cd services/health-dashboard && npm run build

# Build ai-automation-ui
cd services/ai-automation-ui && npm run build

# Run E2E tests
npm run test:e2e
# Or
cd tests/e2e && npx playwright test
```

### 5. Service Startup Tests

**Objective:** Verify all services start successfully

**Tests:**
- [ ] Start all services with `docker-compose up -d`
- [ ] Verify all health endpoints respond
- [ ] Check service logs for dependency errors
- [ ] Verify service-to-service communication

**Commands:**
```bash
# Start all services
docker-compose up -d

# Check health endpoints
curl http://localhost:8001/health  # websocket-ingestion
curl http://localhost:8006/health  # data-api
curl http://localhost:8007/health  # admin-api
curl http://localhost:8019/health  # openvino-service
curl http://localhost:8021/health  # ml-service
curl http://localhost:3000/health  # health-dashboard

# Check logs
docker-compose logs -f [service-name]
```

### 6. Integration Tests

**Objective:** Verify service-to-service communication works

**Tests:**
- [ ] Test AI services integration (OpenVINO, ML, NER)
- [ ] Test data flow (websocket-ingestion → InfluxDB → data-api)
- [ ] Test API endpoints with updated FastAPI

**Commands:**
```bash
# Run integration tests
pytest tests/integration/ -v

# Test specific integrations
pytest tests/integration/test_phase1_services.py -v
```

### 7. ML/AI Functional Tests

**Objective:** Verify ML models work correctly with updated libraries

**Tests:**
- [ ] Test PyTorch 2.4.0+cpu inference
- [ ] Test transformers 4.46.1 model loading
- [ ] Test OpenVINO 2024.5.0 optimization
- [ ] Test NumPy 1.26.x array operations

**Commands:**
```bash
# Test OpenVINO service
curl -X POST http://localhost:8019/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# Test ML service
curl -X POST http://localhost:8021/api/v1/cluster \
  -H "Content-Type: application/json" \
  -d '{"data": [[1,2,3]]}'
```

### 8. Performance Tests

**Objective:** Verify no performance regressions

**Tests:**
- [ ] Measure service startup times
- [ ] Verify memory usage within NUC constraints
- [ ] Check dependency loading time

**Commands:**
```bash
# Measure startup times
time docker-compose up -d

# Check memory usage
docker stats

# Check service resource usage
docker-compose top
```

---

## Test Execution Priority

### 🔴 Critical (Must Pass Before Deployment)

1. **Dependency Resolution** - No conflicts ✅
2. **Service Startup** - All services start
3. **Health Checks** - All health endpoints respond
4. **Python Unit Tests** - Core functionality works

### 🟡 High Priority (Should Pass)

1. **ML/AI Functional Tests** - Models work correctly
2. **API Functional Tests** - Endpoints work
3. **Frontend Build** - Frontend compiles

### 🟢 Medium Priority (Nice to Have)

1. **E2E Tests** - Full user flows
2. **Performance Tests** - Resource usage
3. **Integration Tests** - Service communication

---

## Success Criteria

### ✅ Ready for Deployment When:

- [ ] All dependency checks pass (no conflicts) ✅
- [ ] All services start successfully
- [ ] All health endpoints respond
- [ ] Python unit tests pass
- [ ] Frontend builds successfully
- [ ] No dependency-related errors in logs

---

## Quick Test Commands

### Python Services
```bash
# All Python tests
python scripts/simple-unit-tests.py

# Specific service
cd services/ml-service && pytest -v

# With coverage
pytest --cov=src --cov-report=html
```

### Frontend Services
```bash
# Build test
cd services/health-dashboard && npm run build

# Unit tests
npm run test

# Type check
npm run type-check
```

### Docker Services
```bash
# Build all
docker-compose build

# Start all
docker-compose up -d

# Check logs
docker-compose logs -f [service-name]

# Stop all
docker-compose down
```

### E2E Tests
```bash
# Run all E2E tests
npm run test:e2e

# Or from tests directory
cd tests/e2e && npx playwright test

# With UI
npx playwright test --ui
```

---

## Issues Found & Fixed

### ✅ Fixed Issues

1. **energy-correlator/requirements-prod.txt** - Updated aiohttp (3.9.5 → 3.13.2) and influxdb-client (1.44.0 → 1.49.0)
2. **weather-api/requirements-prod.txt** - Updated aiohttp (3.9.5 → 3.13.2) and influxdb-client (1.44.0 → 1.49.0)
3. **websocket-ingestion/requirements-prod.txt** - Updated aiohttp (3.10.0 → 3.13.2) and influxdb-client (1.40.0 → 1.49.0)

---

**Last Updated:** January 2025  
**Next Steps:** Execute critical tests (service startup, health checks, unit tests)

