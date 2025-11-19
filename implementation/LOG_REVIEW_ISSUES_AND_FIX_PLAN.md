# Log Review Issues and Fix Plan

**Date**: November 19, 2025  
**Review Scope**: All running services in HomeIQ  
**Total Issues Found**: 7

---

## 🎯 Priority Matrix

### 🔴 CRITICAL (P0) - Fix Immediately
1. **InfluxDB Dispatcher Panic** - Memory access violation causing query failures
2. **Duplicate Automations** - Wasting resources and causing confusion

### 🟠 HIGH (P1) - Fix Soon
3. **AI-Automation Import Errors** - Blocking service validation functionality
4. **Websocket Discovery Cache Stale** - 195+ min old (TTL: 30 min), causing thousands of warnings

### 🟡 MEDIUM (P2) - Fix When Possible
5. **AI-Automation YAML Validation** - Non-standard field names
6. **InfluxDB Unauthorized Access** - Authentication failures

### 🟢 LOW (P3) - Monitor
7. **Weather-API Connection Issues** - Resolved after restart (monitor only)

---

## 📋 Detailed Issue Analysis

### P0-1: InfluxDB Dispatcher Panic 🔴
**Service**: homeiq-influxdb  
**Error**: `runtime error: invalid memory address or nil pointer dereference`  
**Impact**: 
- Query failures in flux queries
- Potential data loss
- Service instability

**Root Cause**: Memory corruption in flux dispatcher (storage-reads component)  
**Affected**: All services querying InfluxDB (dashboard, data-api, etc.)

**Fix Strategy**:
- Check InfluxDB version (may need upgrade)
- Review query patterns causing panic
- Add null safety checks
- Consider InfluxDB restart if persistent

---

### P0-2: Duplicate Automations 🔴
**Service**: ai-automation-service  
**Issue**: Created 3 automations (2 named "Office Light Show", 1 "Office Light Party")  
**Impact**:
- Automations trigger multiple times
- Resource waste
- User confusion

**Root Cause**: AI service creating multiple automations for single request  
**Fix Strategy**:
- Delete duplicates via Home Assistant API
- Fix automation creation logic to prevent duplicates
- Add idempotency checks

---

### P1-3: AI-Automation Import Errors 🟠
**Service**: ai-automation-service  
**Error**: `attempted relative import beyond top-level package`  
**Occurrences**: 4 times for different light entities  
**Impact**:
- Cannot validate light entity services
- Incomplete automation validation

**Root Cause**: Incorrect import statements in service code  
**Fix Strategy**:
- Fix relative imports to absolute imports
- Update package structure if needed

---

### P1-4: Websocket Discovery Cache Stale 🟠
**Service**: homeiq-websocket (websocket-ingestion)  
**Issue**: Discovery cache 195+ minutes old (TTL: 30 minutes)  
**Frequency**: Thousands of repeated warnings  
**Impact**:
- Outdated device/area mappings
- Log spam (thousands of messages)
- Potential incorrect event processing

**Root Cause**: Discovery refresh not triggering automatically  
**Fix Strategy**:
- Trigger manual discovery refresh
- Fix auto-refresh mechanism
- Reduce log verbosity for this warning

---

### P2-5: AI-Automation YAML Validation 🟡
**Service**: ai-automation-service  
**Issues**:
- Using `triggers:` instead of `trigger:`
- Using `actions:` instead of `action:`
- Using `action:` field instead of `service:`

**Impact**: Non-standard YAML (but works)  
**Fix Strategy**:
- Update YAML generation to use correct field names
- Ensure HA API compatibility

---

### P2-6: InfluxDB Unauthorized Access 🟡
**Service**: homeiq-influxdb  
**Error**: `Unauthorized: authorization not found`  
**Occurrences**: 3 times  
**Impact**: Some service failing to authenticate  

**Fix Strategy**:
- Identify which service is failing auth
- Verify token/credentials
- Check InfluxDB user permissions

---

### P3-7: Weather-API Connection Issues 🟢
**Service**: homeiq-weather-dev  
**Status**: Resolved after restart  
**Impact**: None (currently working)  
**Action**: Monitor only

---

## 🛠️ Fix Plan

### Phase 1: Critical Fixes (Immediate)
**Estimated Time**: 30 minutes

#### Task 1.1: Clean Up Duplicate Automations
- [ ] List all automations via HA API
- [ ] Identify duplicates
- [ ] Delete extras, keep best one
- [ ] Verify single automation remains

#### Task 1.2: Investigate InfluxDB Panic
- [ ] Check InfluxDB version
- [ ] Review recent queries causing panic
- [ ] Check memory usage
- [ ] Consider restart if needed
- [ ] Monitor for recurrence

---

### Phase 2: High Priority Fixes (Next 1 hour)
**Estimated Time**: 1 hour

#### Task 2.1: Fix Discovery Cache Staleness
- [ ] Find discovery refresh endpoint/mechanism
- [ ] Trigger manual refresh
- [ ] Fix auto-refresh timer
- [ ] Reduce log verbosity for this warning
- [ ] Add cache monitoring

**Files to Check**:
- `services/websocket-ingestion/src/main.py`
- `services/websocket-ingestion/src/discovery.py` (if exists)

#### Task 2.2: Fix AI-Automation Import Errors
- [ ] Locate import statements causing errors
- [ ] Convert relative imports to absolute
- [ ] Test service validation
- [ ] Verify light entity service calls work

**Files to Fix**:
- `services/ai-automation-service/src/**/*.py` (find relative imports)

---

### Phase 3: Medium Priority Fixes (Next 1-2 hours)
**Estimated Time**: 1-2 hours

#### Task 3.1: Fix YAML Generation
- [ ] Update YAML generator to use singular field names
- [ ] Use `service:` instead of `action:` in action blocks
- [ ] Test generated YAML
- [ ] Verify HA API validation passes

**Files to Fix**:
- `services/ai-automation-service/src/yaml_generator.py` (or similar)

#### Task 3.2: Fix InfluxDB Authentication
- [ ] Check InfluxDB logs for which service is failing
- [ ] Verify tokens in environment variables
- [ ] Test connection from failing service
- [ ] Update credentials if needed

---

### Phase 4: Monitoring and Verification (Ongoing)
**Estimated Time**: 30 minutes

- [ ] Monitor InfluxDB for panic recurrence
- [ ] Monitor websocket cache refresh
- [ ] Check automation triggers working correctly
- [ ] Review logs for new issues

---

## 📊 Success Criteria

### Phase 1 (Critical)
- ✅ Only 1 automation exists (duplicates removed)
- ✅ No InfluxDB panics for 1 hour

### Phase 2 (High)
- ✅ Discovery cache refreshes within TTL (< 30 min)
- ✅ No import errors in ai-automation-service
- ✅ Log spam reduced by 90%

### Phase 3 (Medium)
- ✅ All generated YAML uses correct field names
- ✅ No unauthorized errors in InfluxDB logs

### Phase 4 (Monitoring)
- ✅ All services healthy for 24 hours
- ✅ No critical errors in logs

---

## 🎯 Execution Order

1. **DELETE DUPLICATE AUTOMATIONS** (5 min)
2. **FIX DISCOVERY CACHE** (20 min)
3. **FIX IMPORT ERRORS** (20 min)
4. **INVESTIGATE INFLUXDB PANIC** (15 min)
5. **FIX YAML GENERATION** (30 min)
6. **FIX INFLUXDB AUTH** (15 min)
7. **MONITOR & VERIFY** (ongoing)

**Total Estimated Time**: ~2-3 hours

---

## 📝 Notes

- Some fixes may require service restarts
- Test fixes in development environment if possible
- Create backups before making changes
- Document all changes for future reference

---

## 🔗 Related Files to Review

1. `services/websocket-ingestion/src/main.py` - Discovery cache
2. `services/ai-automation-service/src/**/*.py` - Import errors & YAML generation
3. `docker-compose.yml` - InfluxDB configuration
4. `infrastructure/env.influxdb.template` - InfluxDB credentials
5. `services/websocket-ingestion/src/config.py` - Cache TTL settings

