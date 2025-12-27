# Weather Service Action Plan

**Date:** October 10, 2025  
**Status:** Ready for Execution  
**Priority:** HIGH

---

## Task List

### PHASE 1: Update Default Weather Location (IMMEDIATE)

#### Task 1.1: Update Docker Compose Environment Variables
- **Status:** Pending
- **Priority:** P0 - Critical
- **Estimated Time:** 2 minutes
- **Description:** Change default weather location from `London,UK` to `Las Vegas,NV,US`
- **Files to Modify:**
  - `docker-compose.yml` - Line 56: `WEATHER_DEFAULT_LOCATION`
- **Changes:**
  ```yaml
  # Old:
  - WEATHER_DEFAULT_LOCATION=${WEATHER_DEFAULT_LOCATION:-London,UK}
  
  # New:
  - WEATHER_DEFAULT_LOCATION=${WEATHER_DEFAULT_LOCATION:-Las Vegas,NV,US}
  ```

#### Task 1.2: Update Infrastructure Environment Template
- **Status:** Pending
- **Priority:** P0 - Critical
- **Estimated Time:** 2 minutes
- **Description:** Update environment template with Las Vegas location
- **Files to Modify:**
  - `infrastructure/env.example`
  - `infrastructure/env.production`
- **Changes:**
  ```bash
  # Weather API Configuration
  WEATHER_DEFAULT_LOCATION=Las Vegas,NV,US
  ```

#### Task 1.3: Restart WebSocket Ingestion Service
- **Status:** Pending
- **Priority:** P0 - Critical
- **Estimated Time:** 30 seconds
- **Description:** Restart service to pick up new location
- **Commands:**
  ```powershell
  docker-compose restart websocket-ingestion
  ```

#### Task 1.4: Verify New Location
- **Status:** Pending
- **Priority:** P0 - Critical
- **Estimated Time:** 2 minutes
- **Description:** Verify weather data is coming from Las Vegas
- **Verification Steps:**
  1. Check health endpoint: `curl http://localhost:8001/health`
  2. Verify weather data temperature matches Las Vegas weather
  3. Check dashboard at http://localhost:3000/
  4. Confirm API calls increment

---

### PHASE 2: Architectural Cleanup (RECOMMENDED)

#### Task 2.1: Remove Standalone Weather Service from Docker Compose
- **Status:** Pending
- **Priority:** P1 - High
- **Estimated Time:** 5 minutes
- **Description:** Remove unused `weather-api` service definition
- **Files to Modify:**
  - `docker-compose.yml`
- **Changes:** Remove lines 121-151 (entire `weather-api` service block)
- **Verification:** Run `docker-compose config` to validate syntax

#### Task 2.2: Stop and Remove Weather API Container
- **Status:** Pending
- **Priority:** P1 - High
- **Estimated Time:** 1 minute
- **Description:** Stop the broken container
- **Commands:**
  ```powershell
  docker-compose stop weather-api
  docker-compose rm -f weather-api
  ```

#### Task 2.3: Archive Standalone Weather Service Code
- **Status:** Pending
- **Priority:** P2 - Medium
- **Estimated Time:** 2 minutes
- **Description:** Move code to archive for future reference
- **Commands:**
  ```powershell
  # Create archive directory if it doesn't exist
  New-Item -ItemType Directory -Force -Path services/archive
  
  # Move weather-api to archive
  Move-Item services/weather-api services/archive/weather-api-standalone
  
  # Add README explaining why it's archived
  ```

#### Task 2.4: Create Archive README
- **Status:** Pending
- **Priority:** P2 - Medium
- **Estimated Time:** 3 minutes
- **Description:** Document why service was archived
- **Files to Create:**
  - `services/archive/README.md`
- **Content:** Explanation of standalone service removal

---

### PHASE 3: Fix Data Retention Service (SEPARATE ISSUE)

#### Task 3.1: Investigate Data Retention Service Crash
- **Status:** Pending
- **Priority:** P1 - High
- **Estimated Time:** 10 minutes
- **Description:** Diagnose why data-retention service is crash-looping
- **Commands:**
  ```powershell
  docker-compose logs data-retention --tail=50
  ```

#### Task 3.2: Fix Data Retention Service
- **Status:** Pending (blocked by Task 3.1)
- **Priority:** P1 - High
- **Estimated Time:** TBD
- **Description:** Fix identified issues
- **Files to Modify:** TBD based on investigation

---

### PHASE 4: Documentation Updates (REQUIRED)

#### Task 4.1: Update Architecture Documentation
- **Status:** Pending
- **Priority:** P1 - High
- **Estimated Time:** 15 minutes
- **Description:** Update architecture docs to reflect embedded weather enrichment
- **Files to Modify:**
  - `docs/architecture.md`
  - `docs/architecture/service-architecture.md`
  - `docs/architecture/data-flow.md`
- **Changes:**
  - Remove references to standalone weather-api service
  - Document embedded enrichment approach
  - Update architecture diagrams
  - Update service dependency diagrams

#### Task 4.2: Update Docker Documentation
- **Status:** Pending
- **Priority:** P1 - High
- **Estimated Time:** 10 minutes
- **Description:** Update Docker-related documentation
- **Files to Modify:**
  - `docs/DOCKER_STRUCTURE_GUIDE.md`
  - `docs/DOCKER_COMPOSE_SERVICES_REFERENCE.md`
  - `docs/DEPLOYMENT_GUIDE.md`
- **Changes:**
  - Remove weather-api service references
  - Update service list
  - Update port mappings

#### Task 4.3: Update Weather Integration Story
- **Status:** Pending
- **Priority:** P2 - Medium
- **Estimated Time:** 10 minutes
- **Description:** Update weather integration story to reflect actual implementation
- **Files to Modify:**
  - `docs/stories/3.1.weather-api-integration.md`
- **Changes:**
  - Document embedded approach
  - Update sequence diagrams
  - Add Las Vegas as default location

#### Task 4.4: Create Weather Configuration Guide
- **Status:** Pending
- **Priority:** P2 - Medium
- **Estimated Time:** 20 minutes
- **Description:** Create comprehensive guide for weather configuration
- **Files to Create:**
  - `docs/WEATHER_CONFIGURATION_GUIDE.md`
- **Content:**
  - Environment variables explained
  - Location format (city,state,country vs coordinates)
  - API key setup
  - Cache configuration
  - Rate limiting
  - Troubleshooting

#### Task 4.5: Update README
- **Status:** Pending
- **Priority:** P2 - Medium
- **Estimated Time:** 5 minutes
- **Description:** Update main README with correct service list
- **Files to Modify:**
  - `README.md`
- **Changes:**
  - Update service count
  - Remove weather-api from service list
  - Add weather configuration section

---

### PHASE 5: Testing and Validation (CRITICAL)

#### Task 5.1: Run Smoke Tests
- **Status:** Pending
- **Priority:** P0 - Critical
- **Estimated Time:** 5 minutes
- **Description:** Verify system health after changes
- **Commands:**
  ```powershell
  python tests/smoke_tests.py
  ```

#### Task 5.2: Validate Weather Enrichment
- **Status:** Pending
- **Priority:** P0 - Critical
- **Estimated Time:** 5 minutes
- **Description:** Verify weather enrichment is working with Las Vegas
- **Verification Steps:**
  1. Check health endpoint weather stats
  2. Verify events have weather data
  3. Check InfluxDB for weather fields
  4. Verify dashboard shows correct metrics
  5. Confirm Las Vegas weather data (temp should be 60-90°F typically)

#### Task 5.3: Dashboard Visual Inspection
- **Status:** Pending
- **Priority:** P0 - Critical
- **Estimated Time:** 3 minutes
- **Description:** Manually inspect dashboard
- **URL:** http://localhost:3000/
- **Checks:**
  - Weather API Calls incrementing
  - Cache Hits incrementing
  - Weather Enrichment section shows "Enabled"
  - No errors in browser console
  - No 502 errors

#### Task 5.4: Load Testing (Optional)
- **Status:** Pending
- **Priority:** P3 - Low
- **Estimated Time:** 15 minutes
- **Description:** Verify weather cache is working under load
- **Method:** Send multiple events, verify cache hit rate increases

---

## Summary

### Must-Do Tasks (P0 - Critical)
1. ✓ Update default location to Las Vegas
2. ✓ Restart websocket-ingestion service
3. ✓ Verify new location working
4. ✓ Run smoke tests
5. ✓ Validate weather enrichment
6. ✓ Dashboard visual inspection

### Should-Do Tasks (P1 - High)
1. ✓ Remove standalone weather service from docker-compose
2. ✓ Stop and remove weather-api container
3. ✓ Update architecture documentation
4. ✓ Update Docker documentation
5. ✓ Investigate data-retention service crash
6. ✓ Fix data-retention service

### Nice-to-Do Tasks (P2 - Medium)
1. ✓ Archive standalone weather service code
2. ✓ Create archive README
3. ✓ Update weather integration story
4. ✓ Create weather configuration guide
5. ✓ Update main README

### Optional Tasks (P3 - Low)
1. ✓ Load testing
2. ✓ Performance monitoring setup
3. ✓ Additional weather locations configuration

---

## Estimated Total Time

- **Phase 1 (Immediate):** ~10 minutes
- **Phase 2 (Cleanup):** ~15 minutes
- **Phase 3 (Data Retention Fix):** ~20-60 minutes (depends on issue)
- **Phase 4 (Documentation):** ~60 minutes
- **Phase 5 (Testing):** ~15 minutes

**Total (excluding data-retention fix):** ~100 minutes (~1.5 hours)  
**Total (including data-retention fix):** ~120-160 minutes (~2-2.5 hours)

---

## Risk Assessment

### Low Risk
- ✓ Changing default location (easily reversible)
- ✓ Removing broken standalone service (not used)
- ✓ Documentation updates (no code impact)

### Medium Risk
- ⚠️ Data retention service fix (depends on root cause)

### No Risk
- ✓ All changes are to unused/broken components
- ✓ Working weather enrichment is not modified
- ✓ Can rollback by reverting docker-compose.yml

---

## Rollback Plan

If issues occur:

1. **Revert docker-compose.yml:**
   ```powershell
   git checkout docker-compose.yml
   ```

2. **Restart services:**
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

3. **Verify original state:**
   ```powershell
   docker-compose ps
   curl http://localhost:8001/health
   ```

---

## Success Criteria

✓ Weather enrichment shows Las Vegas location  
✓ Weather data temperature matches Las Vegas weather (60-90°F typical)  
✓ Dashboard shows "Weather Service: Enabled"  
✓ API calls and cache hits incrementing  
✓ No broken containers (except data-retention, separate issue)  
✓ Smoke tests pass  
✓ Documentation updated  

---

## Next Steps

**Awaiting User Approval to Proceed with:**
1. Phase 1: Update default location to Las Vegas ← **START HERE**
2. Phase 2: Remove standalone weather service (optional but recommended)
3. Phase 3: Investigate data-retention service (separate issue)
4. Phase 4: Update documentation
5. Phase 5: Testing and validation

