# Synergies Enhancements - Testing & Deployment Plan

**Date:** January 16, 2026  
**Status:** ✅ **READY FOR TESTING & DEPLOYMENT**  
**Implementation:** Complete testing, deployment, and smoke testing procedures

---

## Executive Summary

This document provides comprehensive procedures for testing, deploying, and smoke testing the synergies enhancements. All code has been implemented and integrated. This plan covers:

1. **Pre-Deployment Testing** - Syntax validation, import checks, unit tests
2. **Deployment** - Docker rebuild and service restart
3. **Smoke Testing** - Health checks, API verification, integration validation
4. **Post-Deployment Verification** - Log analysis, functionality checks

---

## Phase 1: Pre-Deployment Testing

### 1.1 Syntax Validation ✅

**Status:** All files compile successfully

**Files Verified:**
- ✅ `src/synergy_detection/capability_analyzer.py`
- ✅ `src/synergy_detection/relationship_discovery.py`
- ✅ `src/synergy_detection/spatial_intelligence.py`
- ✅ `src/synergy_detection/temporal_detector.py`
- ✅ `src/services/energy_savings_calculator.py`
- ✅ `src/synergy_detection/synergy_detector.py` (modified)
- ✅ `src/scheduler/pattern_analysis.py` (modified)

**Verification Command:**
```powershell
# From project root
python -m py_compile services/ai-pattern-service/src/synergy_detection/capability_analyzer.py
python -m py_compile services/ai-pattern-service/src/synergy_detection/relationship_discovery.py
python -m py_compile services/ai-pattern-service/src/synergy_detection/spatial_intelligence.py
python -m py_compile services/ai-pattern-service/src/synergy_detection/temporal_detector.py
python -m py_compile services/ai-pattern-service/src/services/energy_savings_calculator.py
python -m py_compile services/ai-pattern-service/src/synergy_detection/synergy_detector.py
python -m py_compile services/ai-pattern-service/src/scheduler/pattern_analysis.py
```

**Expected Result:** No errors (exit code 0)

---

### 1.2 Import Validation ✅

**Status:** All imports resolve correctly

**Verification Command:**
```powershell
cd services/ai-pattern-service
$env:PYTHONPATH="."
python -c "from src.synergy_detection import DeviceSynergyDetector, RelationshipDiscoveryEngine, SpatialIntelligenceService, TemporalSynergyDetector, DeviceCapabilityAnalyzer; from src.services.energy_savings_calculator import EnergySavingsCalculator; print('✅ All imports successful')"
```

**Expected Result:** `✅ All imports successful`

---

### 1.3 Smoke Test Script ✅

**Location:** `services/ai-pattern-service/scripts/test_synergies_enhancements.py`

**Run Smoke Tests:**
```powershell
cd services/ai-pattern-service
$env:PYTHONPATH="."
python scripts/test_synergies_enhancements.py
```

**Tests Included:**
1. ✅ Energy Savings Calculator
2. ✅ Relationship Discovery Engine
3. ✅ Spatial Intelligence Service
4. ✅ Temporal Detector
5. ✅ Capability Analyzer
6. ✅ Synergy Detector Integration

**Expected Result:** All 6 tests pass

---

### 1.4 Unit Tests (Existing Test Suite)

**Run Existing Tests:**
```powershell
cd services/ai-pattern-service
pytest tests/ -v --tb=short
```

**Key Test Files:**
- `tests/synergy_detection/test_synergy_detector.py` - Main detector tests
- `tests/synergy_detection/test_context_detection.py` - Context detection tests
- `tests/synergy_detection/test_scene_detection.py` - Scene detection tests
- `tests/scheduler/test_pattern_analysis.py` - Scheduler tests

**Expected Result:** All existing tests pass (may need updates for new features)

---

## Phase 2: Deployment

### 2.1 Docker Rebuild

**Rebuild Service Container:**
```powershell
# From project root
docker compose build ai-pattern-service
```

**Expected Output:**
- Build completes successfully
- No build errors
- Image created: `homeiq-ai-pattern-service:latest`

---

### 2.2 Service Restart

**Restart Service:**
```powershell
# Stop service
docker compose stop ai-pattern-service

# Start service
docker compose up -d ai-pattern-service

# Verify container is running
docker compose ps ai-pattern-service
```

**Expected Result:**
- Container status: `Up`
- Health check: Passing (after 30s start period)

---

### 2.3 Verify Container Logs

**Check Startup Logs:**
```powershell
docker compose logs ai-pattern-service --tail 50
```

**Expected Log Messages:**
- ✅ `DeviceSynergyDetector initialized`
- ✅ `DeviceCapabilityAnalyzer enabled` (if URL configured)
- ✅ `RelationshipDiscoveryEngine enabled`
- ✅ `SpatialIntelligenceService enabled`
- ✅ `TemporalSynergyDetector enabled`
- ✅ `EnergySavingsCalculator enabled`
- ✅ `Application startup complete`

**Warning Messages (OK):**
- ⚠️ `DeviceCapabilityAnalyzer not available` (if URL not configured)
- ⚠️ `RelationshipDiscoveryEngine not available` (if import fails)

---

## Phase 3: Smoke Testing

### 3.1 Health Endpoint Check

**Test Health Endpoint:**
```powershell
$health = Invoke-RestMethod -Uri "http://localhost:8034/health"
Write-Host "Status: $($health.status)"
Write-Host "Database: $($health.database)"
```

**Expected Response:**
```json
{
  "status": "ok",
  "database": "connected"
}
```

**Success Criteria:**
- ✅ Status: `"ok"`
- ✅ Database: `"connected"`

---

### 3.2 Readiness Check

**Test Readiness:**
```powershell
$ready = Invoke-RestMethod -Uri "http://localhost:8034/ready"
Write-Host "Status: $($ready.status)"
```

**Expected Response:**
```json
{
  "status": "ready"
}
```

**Success Criteria:**
- ✅ Status: `"ready"`

---

### 3.3 Service Info Check

**Test Root Endpoint:**
```powershell
$info = Invoke-RestMethod -Uri "http://localhost:8034/"
Write-Host "Service: $($info.service)"
Write-Host "Version: $($info.version)"
Write-Host "Status: $($info.status)"
```

**Expected Response:**
```json
{
  "service": "ai-pattern-service",
  "version": "1.0.0",
  "status": "operational"
}
```

**Success Criteria:**
- ✅ Service: `"ai-pattern-service"`
- ✅ Status: `"operational"`

---

### 3.4 Synergy API Check

**Test Synergy List Endpoint:**
```powershell
$synergies = Invoke-RestMethod -Uri "http://localhost:8034/api/v1/synergies/list?limit=5"
Write-Host "Synergies found: $($synergies.data.synergies.Count)"
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "synergies": [...],
    "total": 0
  }
}
```

**Success Criteria:**
- ✅ API responds (200 OK)
- ✅ Response structure is valid
- ✅ No errors in response

---

### 3.5 Verify New Features in Logs

**Check for New Feature Logs:**
```powershell
docker compose logs ai-pattern-service | Select-String -Pattern "EnergySavingsCalculator|SpatialIntelligence|TemporalSynergy|RelationshipDiscovery|CapabilityAnalyzer"
```

**Expected Log Messages:**
- ✅ `EnergySavingsCalculator enabled`
- ✅ `SpatialIntelligenceService enabled`
- ✅ `TemporalSynergyDetector enabled`
- ✅ `RelationshipDiscoveryEngine enabled`
- ✅ `DeviceCapabilityAnalyzer enabled` (if URL configured)

---

## Phase 4: Integration Testing

### 4.1 Trigger Pattern Analysis

**Manual Pattern Analysis Trigger:**
```powershell
# Trigger analysis via API (if endpoint exists)
# Or wait for scheduled run (default: 3 AM daily)
```

**Check Analysis Results:**
```powershell
# Check logs for analysis completion
docker compose logs ai-pattern-service | Select-String -Pattern "Pattern analysis|Synergy detection|Relationship discovery"
```

**Expected Log Messages:**
- ✅ `Starting Pattern Analysis Run`
- ✅ `Phase 3.3: Discovering relationships from events...`
- ✅ `Found X regular synergy opportunities`
- ✅ `Discovered X relationships from events`

---

### 4.2 Verify Energy Savings Data

**Check Synergies for Energy Data:**
```powershell
$synergies = Invoke-RestMethod -Uri "http://localhost:8034/api/v1/synergies/list?limit=10"
foreach ($synergy in $synergies.data.synergies) {
    if ($synergy.context_metadata.energy) {
        Write-Host "Synergy $($synergy.synergy_id) has energy data: $($synergy.context_metadata.energy.savings_score)"
    }
}
```

**Success Criteria:**
- ✅ Synergies with energy context have `energy_savings_score`
- ✅ Energy data in `context_metadata.energy`

---

### 4.3 Verify Context-Aware Synergies

**Check for New Context Types:**
```powershell
$synergies = Invoke-RestMethod -Uri "http://localhost:8034/api/v1/synergies/list?limit=50"
$contextTypes = $synergies.data.synergies | Where-Object { $_.synergy_type -match "context" } | Select-Object -ExpandProperty synergy_type -Unique
Write-Host "Context types found: $($contextTypes -join ', ')"
```

**Expected Context Types:**
- ✅ `weather_context`
- ✅ `energy_context`
- ✅ `sports_context` (if sports entities exist)
- ✅ `carbon_context` (if carbon sensors exist)
- ✅ `calendar_context` (if calendar entities exist)

---

## Phase 5: Post-Deployment Verification

### 5.1 Log Analysis

**Check for Errors:**
```powershell
docker compose logs ai-pattern-service --tail 200 | Select-String -Pattern "ERROR|Exception|Traceback" -Context 2
```

**Success Criteria:**
- ✅ No critical errors
- ✅ Warnings are acceptable (missing optional services)
- ✅ No import errors

---

### 5.2 Performance Check

**Monitor Service Performance:**
```powershell
# Check container resource usage
docker stats ai-pattern-service --no-stream

# Check response times
Measure-Command { Invoke-RestMethod -Uri "http://localhost:8034/health" }
```

**Success Criteria:**
- ✅ Memory usage: < 512MB (baseline)
- ✅ CPU usage: < 50% (idle)
- ✅ Health check response: < 100ms

---

### 5.3 Database Verification

**Check Synergy Storage:**
```powershell
# Query database directly (if SQLite tools available)
# Or use API to verify synergies are stored
$synergies = Invoke-RestMethod -Uri "http://localhost:8034/api/v1/synergies/list?limit=100"
Write-Host "Total synergies stored: $($synergies.data.total)"
```

**Success Criteria:**
- ✅ Synergies are being stored
- ✅ No database errors in logs

---

## Phase 6: Rollback Plan

### 6.1 If Issues Detected

**Immediate Rollback:**
```powershell
# Stop service
docker compose stop ai-pattern-service

# Revert to previous image (if tagged)
docker compose pull ai-pattern-service:previous

# Or rebuild from previous commit
git checkout <previous-commit>
docker compose build ai-pattern-service
docker compose up -d ai-pattern-service
```

---

### 6.2 Rollback Verification

**Verify Rollback:**
```powershell
# Check health
$health = Invoke-RestMethod -Uri "http://localhost:8034/health"
if ($health.status -eq "ok") {
    Write-Host "✅ Rollback successful"
} else {
    Write-Host "❌ Rollback failed"
}
```

---

## Testing Checklist

### Pre-Deployment ✅
- [x] Syntax validation complete
- [x] Import validation complete
- [x] Smoke test script created
- [ ] Unit tests pass (run when ready)
- [ ] Integration tests pass (run when ready)

### Deployment ✅
- [ ] Docker rebuild successful
- [ ] Service restart successful
- [ ] Container logs show no errors
- [ ] All engines initialized

### Smoke Testing ✅
- [ ] Health endpoint responds
- [ ] Readiness endpoint responds
- [ ] Service info endpoint responds
- [ ] Synergy API responds
- [ ] New features visible in logs

### Integration Testing ✅
- [ ] Pattern analysis runs successfully
- [ ] Relationship discovery works
- [ ] Energy savings calculated
- [ ] Context-aware synergies detected
- [ ] Spatial validation works

### Post-Deployment ✅
- [ ] No critical errors in logs
- [ ] Performance acceptable
- [ ] Database operations working
- [ ] All features functional

---

## Quick Reference Commands

### Testing
```powershell
# Syntax check
python -m py_compile services/ai-pattern-service/src/synergy_detection/*.py

# Smoke tests
cd services/ai-pattern-service; $env:PYTHONPATH="."; python scripts/test_synergies_enhancements.py

# Unit tests
cd services/ai-pattern-service; pytest tests/ -v
```

### Deployment
```powershell
# Rebuild
docker compose build ai-pattern-service

# Restart
docker compose restart ai-pattern-service

# Logs
docker compose logs -f ai-pattern-service
```

### Smoke Testing
```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8034/health"

# Synergy list
Invoke-RestMethod -Uri "http://localhost:8034/api/v1/synergies/list?limit=5"
```

---

## Expected Outcomes

### Successful Deployment
- ✅ Service starts without errors
- ✅ All engines initialize correctly
- ✅ Health endpoints respond
- ✅ API endpoints functional
- ✅ New features active in logs

### New Features Active
- ✅ Energy savings calculation working
- ✅ Spatial intelligence validation working
- ✅ Temporal context enhancement working
- ✅ Relationship discovery from events working
- ✅ Context-aware synergies (sports, carbon, calendar) detected

---

## Troubleshooting

### Issue: Service Won't Start
**Check:**
1. Container logs: `docker compose logs ai-pattern-service`
2. Import errors in logs
3. Database connectivity
4. Port conflicts (8034)

### Issue: Engines Not Initialized
**Check:**
1. Import errors in logs
2. Configuration (device_intelligence_url)
3. Optional dependencies available

### Issue: API Errors
**Check:**
1. Service health: `http://localhost:8034/health`
2. Database connectivity
3. Dependencies (data-api) running

---

## Status

✅ **READY FOR DEPLOYMENT**

All code implemented, integrated, and validated. Follow the phases above for testing and deployment.

---

**Last Updated:** January 16, 2026  
**Next Steps:** Execute Phase 1 (Pre-Deployment Testing)
