# Epic 41: Testing Plan for Dependency Updates

**Date:** January 2025  
**Status:** Ready for Execution  
**Target:** Verify all dependency updates work correctly on NUC

## Testing Strategy

### Phase 1: Pre-Deployment Validation (Current)

#### 1.1 Dependency Resolution Tests

**Objective:** Verify all updated dependencies can be installed without conflicts

**Tests:**
- [ ] Run `pip check` on all updated requirements.txt files
- [ ] Verify Docker builds succeed for all services
- [ ] Check for dependency conflicts in pip install logs

**Commands:**
```bash
# Check Python dependencies
for service in services/*/requirements.txt; do
  echo "Checking $service..."
  pip check -r "$service"
done

# Test Docker builds
docker-compose build --no-cache
```

#### 1.2 Linting & Formatting

**Status:** ✅ Already verified - No linter errors

#### 1.3 Version Verification

**Objective:** Confirm all versions are correct

**Manual Verification:**
- [x] FastAPI: 0.115.x series
- [x] Uvicorn: 0.32.x series
- [x] NumPy: 1.26.x
- [x] PyTorch: 2.4.0+cpu
- [x] Node.js: 20.11.0
- [x] Playwright: 1.56.1

### Phase 2: Unit Tests (Recommended Next)

#### 2.1 Python Service Tests

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
cd services/ml-service && pytest
cd services/openvino-service && pytest
cd services/data-api && pytest
```

#### 2.2 Frontend Tests

**Objective:** Verify frontend works with Node.js 20 and updated Playwright

**Target Services:**
- [ ] `health-dashboard` - Test with Node.js 20 LTS
- [ ] `ai-automation-ui` - Test with Node.js 20 LTS
- [ ] E2E tests - Test with Playwright 1.56.1

**Commands:**
```bash
# Build frontend services
cd services/health-dashboard && npm install && npm run build
cd services/ai-automation-ui && npm install && npm run build

# Run frontend unit tests
cd services/health-dashboard && npm run test
```

### Phase 3: Integration Tests

#### 3.1 Service Startup Tests

**Objective:** Verify all services start successfully

**Tests:**
- [ ] Start all services with docker-compose
- [ ] Verify health endpoints respond
- [ ] Check for startup errors in logs

**Commands:**
```bash
# Start all services
docker-compose up -d

# Check health endpoints
curl http://localhost:8001/health  # websocket-ingestion
curl http://localhost:8003/api/v1/health  # admin-api
curl http://localhost:8006/health  # data-api
curl http://localhost:3000  # health-dashboard
```

#### 3.2 Database Connectivity

**Objective:** Verify database connections work with updated versions

**Tests:**
- [ ] InfluxDB 2.7.12 connectivity
- [ ] SQLite 3.51.0 via aiosqlite 0.21.0
- [ ] Data migration verification

### Phase 4: Functional Tests

#### 4.1 ML/AI Services

**Objective:** Verify ML libraries work correctly

**Tests:**
- [ ] PyTorch 2.4.0+cpu model inference
- [ ] NumPy 1.26.x array operations
- [ ] OpenVINO model loading
- [ ] Transformers 4.46.1 inference

#### 4.2 API Services

**Objective:** Verify API services work with FastAPI 0.115.x

**Tests:**
- [ ] API endpoint responses
- [ ] OpenAPI documentation generation
- [ ] Request/response validation
- [ ] Error handling

### Phase 5: Performance Tests

#### 5.1 Memory Usage

**Objective:** Verify services stay within NUC memory constraints

**Tests:**
- [ ] Monitor memory usage per service
- [ ] Verify <256M-512M per service
- [ ] Check for memory leaks

#### 5.2 Startup Time

**Objective:** Verify services start quickly

**Tests:**
- [ ] Measure service startup times
- [ ] Verify <30s for most services
- [ ] Check dependency loading time

### Phase 6: E2E Tests

#### 6.1 Frontend E2E

**Objective:** Verify frontend works end-to-end

**Commands:**
```bash
# Run E2E tests
npm run test:e2e

# Or specifically
cd tests/e2e && npx playwright test
```

## Test Execution Priority

### 🔴 Critical (Must Pass Before Deployment)

1. **Dependency Resolution** - No conflicts
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

## Testing Commands Quick Reference

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

## Success Criteria

### ✅ Ready for Deployment When:

- [ ] All dependency checks pass (no conflicts)
- [ ] All services start successfully
- [ ] All health endpoints respond
- [ ] Core Python unit tests pass (>80% pass rate)
- [ ] Frontend builds successfully
- [ ] No critical errors in logs

### ✅ Ready for Production When:

- [ ] All tests pass (unit, integration, E2E)
- [ ] Performance tests pass (memory, startup time)
- [ ] 24-hour monitoring shows stability
- [ ] No regressions detected

## Rollback Plan

If critical issues are found:

1. **Immediate Rollback:** Revert docker-compose.yml version changes
2. **Partial Rollback:** Revert specific service requirements.txt files
3. **Full Rollback:** Revert all Epic 41 changes via git

**Rollback Commands:**
```bash
# Revert specific files
git checkout HEAD~1 -- docker-compose.yml
git checkout HEAD~1 -- services/ml-service/requirements.txt

# Full rollback (if needed)
git revert <epic-41-commit-hash>
```

## Next Steps

1. **Execute Phase 1** - Dependency resolution tests
2. **Execute Phase 2** - Unit tests
3. **Review Results** - Assess test outcomes
4. **Execute Phase 3** - Integration tests (if Phase 1-2 pass)
5. **Deploy to Staging** - If all tests pass

