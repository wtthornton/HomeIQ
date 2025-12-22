# Deployment Issues Review and Fix Plan

**Date:** January 2025  
**Status:** 🔍 Issues Identified - Fix Plan Created

## Executive Summary

Review of current deployment logs identified **5 critical issues** and **3 infrastructure improvements** needed:

### Critical Issues
1. ⚠️ **ai-pattern-service unhealthy** - Health check failing
2. ⚠️ **Missing endpoint** - `/internal/services/bulk_upsert` not implemented in data-api
3. ⚠️ **OpenTelemetry warnings** - Missing dependencies in ai-pattern-service
4. ⚠️ **MQTT connection failures** - ai-pattern-service cannot connect to MQTT broker
5. ⚠️ **Docker build context mismatch** - Dockerfiles expect root context but docker-compose uses service context

### Infrastructure Improvements
6. 🔧 **Test script syntax errors** - PowerShell build test script needs fixes
7. 📝 **Documentation gaps** - Missing endpoint documentation
8. 🏗️ **Build system** - Model-prep container created but not integrated

---

## Issue Details

### 1. ai-pattern-service Health Check Failure

**Status:** ⚠️ Unhealthy  
**Container:** `ai-pattern-service`  
**Port:** 8034 (external) → 8020 (internal)

**Symptoms:**
- Docker health check shows "unhealthy" status
- Service appears to be running (logs show startup complete)
- Health endpoint exists at `/health`

**Root Cause Analysis:**
```bash
# Health check in docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8020/health"]
```

**Actual Issue:**
- ✅ Health endpoint works (tested externally: `http://localhost:8034/health` returns `{"status": "ok", "database": "connected"}`)
- ❌ `curl` is not installed in the container (python:3.12-slim base image)
- Health check fails because `curl` command not found

**Fix:**
Replace `curl` with Python-based health check or install curl

**Investigation Needed:**
- Check if health endpoint is accessible: `GET /health` vs `GET /health/health`
- Verify database connectivity during health check
- Check health check timing (start_period: 30s may be insufficient)

**Fix Plan:**
1. ✅ Health endpoint works (tested: returns `{"status": "ok", "database": "connected"}`)
2. **Fix health check command** - Replace `curl` with Python-based check:
   ```yaml
   healthcheck:
     test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8020/health')"]
   ```
   OR install curl in Dockerfile:
   ```dockerfile
   RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
   ```
3. Test health check after fix
4. Verify container shows "healthy" status

---

### 2. Missing `/internal/services/bulk_upsert` Endpoint

**Status:** ❌ 404 Not Found  
**Service:** data-api  
**Caller:** websocket-ingestion

**Symptoms:**
```
⚠️  Services bulk_upsert endpoint returned 404 (Not Found)
   Endpoint: http://data-api:8006/internal/services/bulk_upsert
```

**Current State:**
- ✅ `/internal/devices/bulk_upsert` - **Implemented**
- ✅ `/internal/entities/bulk_upsert` - **Implemented**
- ❌ `/internal/services/bulk_upsert` - **Missing**

**Impact:**
- Service discovery from Home Assistant works
- Services are discovered but not stored in SQLite
- No impact on core functionality (graceful degradation)

**Fix Plan:**
1. Review `services/websocket-ingestion/src/discovery_service.py` to understand expected payload
2. Create `/internal/services/bulk_upsert` endpoint in `services/data-api/src/devices_endpoints.py`
3. Follow same pattern as devices/entities bulk_upsert
4. Add Service model if not exists
5. Test endpoint with sample service data
6. Update documentation

**Implementation Location:**
- File: `services/data-api/src/devices_endpoints.py`
- Pattern: Similar to `bulk_upsert_devices()` and `bulk_upsert_entities()`

---

### 3. OpenTelemetry Dependency Warnings

**Status:** ⚠️ Warning (Non-blocking)  
**Service:** ai-pattern-service

**Symptoms:**
```
OpenTelemetry not available. Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
OpenTelemetry not available, skipping FastAPI instrumentation
OpenTelemetry not available, skipping tracing setup
```

**Root Cause:**
- OpenTelemetry packages not in `requirements.txt`
- Service tries to use observability but gracefully degrades

**Impact:**
- ⚠️ No distributed tracing
- ⚠️ No OpenTelemetry metrics
- ✅ Service still functions (graceful degradation)

**Fix Plan:**
1. Add OpenTelemetry dependencies to `services/ai-pattern-service/requirements.txt`:
   ```txt
   opentelemetry-api>=1.24.0
   opentelemetry-sdk>=1.24.0
   opentelemetry-instrumentation-fastapi>=0.45b0
   ```
2. Verify observability setup in `services/ai-pattern-service/src/main.py`
3. Test that tracing works after adding dependencies
4. Consider adding to other AI services for consistency

---

### 4. MQTT Connection Failures

**Status:** ⚠️ Warning (Non-blocking)  
**Service:** ai-pattern-service

**Symptoms:**
```
❌ MQTT connection attempt 1 failed: [Errno -2] Name or service not known
❌ MQTT connection attempt 2 failed: [Errno -2] Name or service not known
❌ MQTT connection attempt 3 failed: [Errno -2] Name or service not known
❌ All MQTT connection attempts failed
```

**But then:**
```
✅ MQTT client connected to mqtt://192.168.1.86:1883:1883
```

**Root Cause:**
- MQTT broker URL configuration issue
- Initial connection attempts fail, then succeeds
- Possible DNS resolution issue or broker not ready

**Impact:**
- ⚠️ Pattern notifications may be delayed
- ✅ Service continues to function (MQTT is optional)

**Fix Plan:**
1. Review MQTT configuration in `.env` and docker-compose.yml
2. Check MQTT broker availability: `192.168.1.86:1883`
3. Add retry logic with exponential backoff
4. Improve error handling in MQTT client
5. Consider making MQTT truly optional (don't fail if unavailable)

---

### 5. Docker Build Context Mismatch

**Status:** ❌ Build Failure  
**Impact:** Cannot build services from service directory

**Root Cause:**
- Dockerfiles use `COPY ../shared/ ./shared/` (expects root context)
- docker-compose.yml uses `context: ./services/{service}` (service context)
- `../shared/` is outside build context → build fails

**Error:**
```
ERROR: failed to calculate checksum of ref: "/shared": not found
```

**Affected Services:**
- All services using `COPY ../shared/` (12+ services)

**Fix Plan (Option A - Recommended):**
1. Update docker-compose.yml to use root context:
   ```yaml
   build:
     context: .  # Root directory
     dockerfile: services/{service}/Dockerfile
   ```
2. Update Dockerfiles to use root-relative paths:
   ```dockerfile
   COPY shared/ ./shared/
   COPY services/{service}/src/ ./src/
   ```
3. Update `.dockerignore` to exclude unnecessary files
4. Test all builds

**Fix Plan (Option B - Alternative):**
1. Create build script that copies `shared/` into each service directory
2. Keep current docker-compose.yml structure
3. Clean up copied files after build

**Recommendation:** Option A (root context) - simpler and more maintainable

---

### 6. PowerShell Test Script Syntax Errors

**Status:** ⚠️ Script Errors  
**File:** `scripts/test-docker-builds.ps1`

**Symptoms:**
```
Missing closing '}' in statement block or type definition
```

**Root Cause:**
- PowerShell function parameter handling issues
- Write-Error function name conflict (built-in cmdlet)

**Fix Plan:**
1. ✅ Fixed function names (Write-ErrorMsg instead of Write-Error)
2. ✅ Fixed parameter handling in helper functions
3. ⏳ Test script execution
4. ⏳ Verify Docker build commands work correctly

**Status:** Partially fixed, needs testing

---

### 7. Documentation Gaps

**Status:** 📝 Missing Documentation

**Missing:**
- `/internal/services/bulk_upsert` endpoint documentation
- Build context requirements documentation
- Health check endpoint paths documentation

**Fix Plan:**
1. Document `/internal/services/bulk_upsert` endpoint (after implementation)
2. Add build context documentation to README
3. Document health check endpoints for all services
4. Update API documentation

---

### 8. Model-Prep Container Not Integrated

**Status:** ✅ Created, ⏳ Not Integrated

**Created:**
- `services/model-prep/Dockerfile`
- `services/model-prep/download_all_models.py`
- `services/model-prep/README.md`

**Missing:**
- Integration into docker-compose.yml
- CI/CD integration
- Usage documentation

**Fix Plan:**
1. Add model-prep service to docker-compose.yml
2. Create volume for model cache
3. Add model-prep to build pipeline
4. Document usage in main README

---

## Priority Fix Order

### 🔴 Critical (Fix Immediately)
1. **Docker build context** - Blocks all new builds
2. **ai-pattern-service health check** - Service marked unhealthy
3. **Missing bulk_upsert endpoint** - Functionality incomplete

### 🟡 High (Fix Soon)
4. **OpenTelemetry dependencies** - Missing observability
5. **MQTT connection handling** - Improve reliability

### 🟢 Medium (Nice to Have)
6. **Test script fixes** - Improve development workflow
7. **Documentation** - Improve maintainability
8. **Model-prep integration** - Optimize builds

---

## Implementation Steps

### Step 1: Fix Docker Build Context (Critical)

**Estimated Time:** 2-3 hours

1. Update docker-compose.yml for one service (test):
   ```yaml
   websocket-ingestion:
     build:
       context: .
       dockerfile: services/websocket-ingestion/Dockerfile
   ```

2. Update Dockerfile paths:
   ```dockerfile
   COPY shared/ ./shared/
   COPY services/websocket-ingestion/src/ ./src/
   ```

3. Test build: `docker-compose build websocket-ingestion`

4. If successful, apply to all services

5. Update `.dockerignore` to exclude unnecessary files

### Step 2: Fix ai-pattern-service Health Check

**Estimated Time:** 1 hour

1. Test health endpoint:
   ```bash
   curl http://localhost:8034/health
   ```

2. Check health router path:
   - Review `services/ai-pattern-service/src/api/health_router.py`
   - Verify router prefix in `main.py`

3. Add simple liveness check (no database):
   ```python
   @router.get("/live")
   async def liveness():
       return {"status": "live"}
   ```

4. Update health check to use `/live` endpoint

5. Test and verify healthy status

### Step 3: Implement Missing Endpoint

**Estimated Time:** 2 hours

1. Review service discovery payload structure
2. Create Service model (if needed)
3. Implement `/internal/services/bulk_upsert` endpoint
4. Add tests
5. Update documentation

### Step 4: Add OpenTelemetry Dependencies

**Estimated Time:** 30 minutes

1. Add to requirements.txt
2. Rebuild service
3. Verify warnings disappear

### Step 5: Improve MQTT Connection Handling

**Estimated Time:** 1 hour

1. Review MQTT client implementation
2. Add exponential backoff retry logic
3. Improve error messages
4. Test connection reliability

---

## Testing Plan

### After Each Fix

1. **Build Test:**
   ```bash
   docker-compose build {service}
   ```

2. **Health Check:**
   ```bash
   curl http://localhost:{port}/health
   ```

3. **Log Review:**
   ```bash
   docker-compose logs {service} --tail 50
   ```

### Full System Test

1. Rebuild all services
2. Restart deployment: `docker-compose up -d`
3. Wait for all services to be healthy
4. Check logs for errors
5. Test endpoints

---

## Success Criteria

### Critical Fixes
- ✅ All services build successfully from root context
- ✅ ai-pattern-service shows "healthy" status
- ✅ `/internal/services/bulk_upsert` returns 200 OK

### High Priority Fixes
- ✅ No OpenTelemetry warnings in logs
- ✅ MQTT connections succeed on first attempt (or gracefully degrade)

### Medium Priority
- ✅ Test script runs without errors
- ✅ Documentation updated
- ✅ Model-prep container integrated

---

## Related Files

### Files to Modify
- `docker-compose.yml` - Build context updates
- `services/*/Dockerfile` - Path updates (12+ files)
- `services/data-api/src/devices_endpoints.py` - Add bulk_upsert endpoint
- `services/ai-pattern-service/requirements.txt` - Add OpenTelemetry
- `services/ai-pattern-service/src/api/health_router.py` - Health check fixes
- `.dockerignore` - Context exclusions

### Documentation to Update
- `README.md` - Build instructions
- `services/data-api/README.md` - New endpoint
- `services/ai-pattern-service/README.md` - Health check info
- `implementation/DOCKER_BUILD_CONTEXT_ISSUE.md` - Resolution

---

## Next Steps

1. **Review this plan** - Confirm priorities and approach
2. **Start with critical fixes** - Docker build context first
3. **Test incrementally** - Fix one issue, test, move to next
4. **Document changes** - Update relevant documentation
5. **Verify deployment** - Full system test after all fixes

---

## Notes

- Most issues are non-blocking (graceful degradation)
- Service discovery works despite missing endpoint
- Health check issue may be cosmetic (service is running)
- Docker build context is the only blocking issue

**Estimated Total Time:** 6-8 hours for all fixes

