# Service Status and Rebuild Plan

**Date:** December 2, 2025  
**Status:** Reviewing and Rebuilding Services

---

## 📊 Current Service Status

### ✅ Healthy Services (32 services)
- **ai-automation-service** - Up 17 minutes (healthy) - **JUST UPDATED**
- **ai-automation-ui** - Up 16 hours (healthy)
- **ai-code-executor** - Up 2 days (healthy) - **NEEDS REBUILD**
- **ai-query-service** - Up 2 days (healthy) - **NEEDS REBUILD**
- **ai-training-service** - Up 2 days (healthy) - **NEEDS REBUILD**
- **automation-miner** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-admin** - Up 16 hours (healthy)
- **homeiq-ai-core-service** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-air-quality** - Up 17 hours (healthy)
- **homeiq-calendar** - Up 17 hours (healthy)
- **homeiq-carbon-intensity** - Up 17 hours (healthy)
- **homeiq-dashboard** - Up 16 hours (healthy)
- **homeiq-data-api** - Up 16 hours (healthy)
- **homeiq-device-context-classifier** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-device-database-client** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-device-health-monitor** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-device-intelligence** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-device-recommender** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-device-setup-assistant** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-electricity-pricing** - Up 17 hours (healthy)
- **homeiq-energy-correlator** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-influxdb** - Up 2 days (healthy)
- **homeiq-log-aggregator** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-ml-service** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-ner-service** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-openai-service** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-openvino-service** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-setup-service** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-smart-meter** - Up 2 days (healthy) - **NEEDS REBUILD**
- **homeiq-weather-api** - Up 16 hours (healthy)

### ⚠️ Issues Found

#### 1. Unhealthy Service
- **homeiq-websocket** - Up 16 hours (unhealthy)
  - Errors: "Concurrent call to receive() is not allowed"
  - Impact: May affect event ingestion

#### 2. Service Without Health Status
- **ai-pattern-service** - Up 2 days (no health status) - **NEEDS REBUILD**

#### 3. Migration Issues

**data-api:**
- Current migration: 005
- Attempting: 005 → 006 → 007
- Error: `table statistics_meta already exists`
- **Fix:** Migration 007 is trying to create a table that already exists

**ai-automation-service:**
- Error: `Multiple head revisions are present`
- **Fix:** Need to resolve multiple migration heads

---

## 🔧 Fixes Needed

### 1. Database Migration Fixes

#### data-api Migration
**Issue:** Migration 007 tries to create `statistics_meta` table that already exists

**Solution Options:**
- Option A: Mark migration 007 as already applied (if table exists)
- Option B: Make migration 007 check if table exists before creating
- Option C: Drop and recreate (if safe)

#### ai-automation-service Migration
**Issue:** Multiple head revisions in alembic

**Solution:**
- Check alembic heads: `alembic heads`
- Merge heads or specify target revision
- Update to latest head

### 2. Service Rebuilds Needed

**21 services need rebuilding** (up for 2+ days):
1. ai-code-executor
2. ai-pattern-service
3. ai-query-service
4. ai-training-service
5. automation-miner
6. homeiq-ai-core-service
7. homeiq-device-context-classifier
8. homeiq-device-database-client
9. homeiq-device-health-monitor
10. homeiq-device-intelligence
11. homeiq-device-recommender
12. homeiq-device-setup-assistant
13. homeiq-energy-correlator
14. homeiq-log-aggregator
15. homeiq-ml-service
16. homeiq-ner-service
17. homeiq-openai-service
18. homeiq-openvino-service
19. homeiq-setup-service
20. homeiq-smart-meter

---

## 🚀 Rebuild Plan

### Phase 1: Fix Migrations (Priority 1)
1. Fix data-api migration (statistics_meta table issue)
2. Fix ai-automation-service migration (multiple heads)
3. Run migrations for all services

### Phase 2: Rebuild Services (Priority 2)
1. Rebuild services in batches (5-6 at a time)
2. Restart services after rebuild
3. Verify health status

### Phase 3: Fix Unhealthy Service (Priority 3)
1. Investigate websocket-ingestion issues
2. Fix concurrent receive() errors
3. Restart and verify

---

## 📝 Next Steps

1. **Fix migration issues** - Resolve table conflicts and multiple heads
2. **Rebuild services** - Ensure all services have latest code
3. **Run migrations** - Update all databases
4. **Verify health** - Check all services are healthy

---

**Last Updated:** December 2, 2025

