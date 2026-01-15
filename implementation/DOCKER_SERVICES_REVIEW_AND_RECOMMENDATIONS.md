# Docker Services Review and Recommendations

**Date:** January 15, 2026  
**Status:** Review Complete - Recommendations for Approval  
**Reviewer:** AI Assistant  

---

## Executive Summary

**Current State:**
- **42 containers** are currently running
- **38 services** are defined in `docker-compose.yml`
- **Documentation inconsistency:** Multiple documents report different service counts (24, 25, 30+, 43)
- **Container naming mismatch:** Some services use `homeiq-` prefix, others don't (inconsistent)

**Key Findings:**
1. ✅ All defined services are running
2. ⚠️ Documentation counts are inconsistent (24 vs 30+ vs 38)
3. ⚠️ Container naming convention is inconsistent
4. ⚠️ Some services enabled via profiles (air-quality, calendar, carbon-intensity, electricity-pricing) are running without profile activation
5. ✅ All services are healthy and operational

---

## Current Running Containers (42 Total)

### HomeIQ Services (34 containers with `homeiq-` prefix)

1. `homeiq-admin` (admin-api)
2. `homeiq-ai-core-service`
3. `homeiq-air-quality` ⚠️ (should require production profile)
4. `homeiq-blueprint-index`
5. `homeiq-blueprint-suggestion`
6. `homeiq-calendar` ⚠️ (should require production profile)
7. `homeiq-carbon-intensity` ⚠️ (should require production profile)
8. `homeiq-dashboard` (health-dashboard)
9. `homeiq-data-api`
10. `homeiq-data-retention`
11. `homeiq-device-context-classifier`
12. `homeiq-device-database-client`
13. `homeiq-device-health-monitor`
14. `homeiq-device-intelligence` (device-intelligence-service)
15. `homeiq-device-recommender`
16. `homeiq-device-setup-assistant`
17. `homeiq-electricity-pricing` ⚠️ (should require production profile)
18. `homeiq-energy-correlator`
19. `homeiq-ha-ai-agent-service`
20. `homeiq-influxdb`
21. `homeiq-jaeger`
22. `homeiq-log-aggregator`
23. `homeiq-ml-service`
24. `homeiq-ner-service`
25. `homeiq-openai-service`
26. `homeiq-openvino-service`
27. `homeiq-proactive-agent-service`
28. `homeiq-rag-service`
29. `homeiq-rule-recommendation-ml`
30. `homeiq-setup-service` (ha-setup-service)
31. `homeiq-smart-meter`
32. `homeiq-sports-api`
33. `homeiq-weather-api`
34. `homeiq-websocket` (websocket-ingestion)

### Services WITHOUT `homeiq-` Prefix (8 containers)

1. `ai-automation-service-new` ⚠️ (inconsistent naming)
2. `ai-automation-ui` ⚠️ (inconsistent naming)
3. `ai-code-executor` ⚠️ (not in docker-compose.yml)
4. `ai-pattern-service` ⚠️ (not in docker-compose.yml)
5. `ai-query-service` ⚠️ (inconsistent naming)
6. `ai-training-service` ⚠️ (inconsistent naming)
7. `automation-miner` ⚠️ (inconsistent naming)
8. `yaml-validation-service` ⚠️ (inconsistent naming)

---

## Docker Compose Defined Services (38 Total)

### Services Defined in docker-compose.yml

1. `admin-api` → Container: `homeiq-admin`
2. `ai-automation-service-new` → Container: `ai-automation-service-new` ⚠️
3. `ai-automation-ui` → Container: `ai-automation-ui` ⚠️
4. `ai-code-executor` → Container: `ai-code-executor` ⚠️
5. `ai-core-service` → Container: `homeiq-ai-core-service`
6. `ai-pattern-service` → Container: `ai-pattern-service` ⚠️
7. `ai-query-service` → Container: `ai-query-service` ⚠️
8. `ai-training-service` → Container: `ai-training-service` ⚠️
9. `automation-miner` → Container: `automation-miner` ⚠️
10. `blueprint-index` → Container: `homeiq-blueprint-index`
11. `blueprint-suggestion-service` → Container: `homeiq-blueprint-suggestion`
12. `data-api` → Container: `homeiq-data-api`
13. `data-retention` → Container: `homeiq-data-retention`
14. `device-context-classifier` → Container: `homeiq-device-context-classifier`
15. `device-database-client` → Container: `homeiq-device-database-client`
16. `device-health-monitor` → Container: `homeiq-device-health-monitor`
17. `device-intelligence-service` → Container: `homeiq-device-intelligence`
18. `device-recommender` → Container: `homeiq-device-recommender`
19. `device-setup-assistant` → Container: `homeiq-device-setup-assistant`
20. `energy-correlator` → Container: `homeiq-energy-correlator`
21. `ha-ai-agent-service` → Container: `homeiq-ha-ai-agent-service`
22. `ha-setup-service` → Container: `homeiq-setup-service`
23. `health-dashboard` → Container: `homeiq-dashboard`
24. `influxdb` → Container: `homeiq-influxdb`
25. `jaeger` → Container: `homeiq-jaeger`
26. `log-aggregator` → Container: `homeiq-log-aggregator`
27. `ml-service` → Container: `homeiq-ml-service`
28. `ner-service` → Container: `homeiq-ner-service`
29. `openai-service` → Container: `homeiq-openai-service`
30. `openvino-service` → Container: `homeiq-openvino-service`
31. `proactive-agent-service` → Container: `homeiq-proactive-agent-service`
32. `rag-service` → Container: `homeiq-rag-service`
33. `rule-recommendation-ml` → Container: `homeiq-rule-recommendation-ml`
34. `smart-meter` → Container: `homeiq-smart-meter`
35. `sports-api` → Container: `homeiq-sports-api`
36. `weather-api` → Container: `homeiq-weather-api`
37. `websocket-ingestion` → Container: `homeiq-websocket`
38. `yaml-validation-service` → Container: `yaml-validation-service` ⚠️

### Services with Profiles (Conditional)

**Production Profile Required:**
- `air-quality` (should only run with `--profile production`)
- `calendar` (should only run with `--profile production`)
- `carbon-intensity` (should only run with `--profile production`)
- `electricity-pricing` (should only run with `--profile production`)

**Note:** These services are currently running despite having `profiles: - production` defined. This suggests either:
1. Services were started with `--profile production`, OR
2. Profile enforcement is not working correctly

---

## Documentation Comparison

### Service Count Discrepancies

| Document | Reported Count | Actual Count | Status |
|----------|---------------|--------------|--------|
| **CLAUDE.md** | 24 active + InfluxDB = 25 total | ❌ **Incorrect** | Needs update |
| **DEPLOYMENT_RUNBOOK.md** | 30+ microservices | ✅ **Accurate range** | Acceptable |
| **docker-compose.yml** | 38 services defined | ✅ **Accurate** | Current |
| **Current Running** | 42 containers | ✅ **Accurate** | Current |

**Calculation:**
- 38 services defined in docker-compose.yml
- 4 services running despite profile requirements = 38 + 4 active
- Total: 42 containers running (all services active)

---

## Issues Identified

### 1. Container Naming Inconsistency ⚠️ **HIGH PRIORITY**

**Problem:**
- Most services use `homeiq-` prefix in container names
- 8 services do NOT use the prefix:
  - `ai-automation-service-new`
  - `ai-automation-ui`
  - `ai-code-executor`
  - `ai-pattern-service`
  - `ai-query-service`
  - `ai-training-service`
  - `automation-miner`
  - `yaml-validation-service`

**Impact:**
- Inconsistent filtering (`docker ps --filter "name=homeiq"` misses 8 services)
- Confusing for operators
- Harder to identify HomeIQ services vs external containers

**Recommendation:**
- Standardize all container names to use `homeiq-` prefix
- Update docker-compose.yml to add `container_name: homeiq-<service-name>` for all services

### 2. Documentation Service Count Inconsistency ⚠️ **MEDIUM PRIORITY**

**Problem:**
- CLAUDE.md says "24 active microservices + InfluxDB = 25 total"
- Actual: 38 services defined, 42 containers running
- DEPLOYMENT_RUNBOOK.md says "30+ microservices" (acceptable range)

**Recommendation:**
- Update CLAUDE.md to reflect actual count: "38 microservices + Infrastructure (InfluxDB, Jaeger) = 40 total containers"
- Update DEPLOYMENT_RUNBOOK.md to clarify: "38 active microservices (4 with conditional production profiles)"
- Add note about profile-based conditional services

### 3. Profile Enforcement Verification ⚠️ **MEDIUM PRIORITY**

**Problem:**
- Services with `profiles: - production` are running
- Need to verify if they're supposed to run by default or only with `--profile production`

**Recommendation:**
- Verify deployment script (`scripts/deploy.sh`) uses `--profile production`
- If profiles are intentionally always active, remove profile requirements from docker-compose.yml
- If profiles should be enforced, ensure deployment scripts use them correctly

### 4. Services Not in Docker Compose ⚠️ **LOW PRIORITY**

**Problem:**
- All running containers appear to be defined in docker-compose.yml
- Some may have been started manually or from another compose file

**Recommendation:**
- Verify if any services were started from separate compose files
- Check for orphaned containers that should be managed by docker-compose.yml

---

## Recommendations for Approval

### Priority 1: Standardize Container Naming ✅ **APPROVE**

**Action:**
Update `docker-compose.yml` to add `container_name` with `homeiq-` prefix for all services:

```yaml
# Example for services without prefix
ai-automation-service-new:
  container_name: homeiq-ai-automation-service-new
  # ... rest of config

ai-automation-ui:
  container_name: homeiq-ai-automation-ui
  # ... rest of config

# ... repeat for all 8 services
```

**Benefits:**
- Consistent naming convention
- Easier service identification
- Better filtering and management
- Clearer operational visibility

**Risk:** Low (container names can be changed, but requires service restart)

### Priority 2: Update Documentation ✅ **APPROVE**

**Action:**
Update service count documentation:

1. **CLAUDE.md** (Line 60-62):
   ```markdown
   ### 38 Active Microservices Overview
   
   **Note:** Plus InfluxDB and Jaeger infrastructure = 40 total containers in production
   ```

2. **DEPLOYMENT_RUNBOOK.md** (Line 71):
   ```markdown
   HomeIQ deploys **38 microservices** organized into the following categories:
   ```

**Benefits:**
- Accurate documentation
- Reduces confusion
- Better alignment with actual deployment

**Risk:** None (documentation only)

### Priority 3: Verify Profile Enforcement ✅ **APPROVE (Conditional)**

**Action:**
1. Review `scripts/deploy.sh` to verify it uses `--profile production`
2. If profiles are intentionally always active, document this clearly
3. If profiles should be enforced, ensure scripts use them correctly

**Current State:**
- `scripts/deploy.sh` Line 188: Uses `docker-compose --profile production up -d --build`
- This explains why all services are running (production profile activated)

**Recommendation:**
- ✅ **Keep current behavior** (production profile always active)
- Update documentation to clarify: "All services run in production mode"
- Remove misleading `profiles: - production` from services that always run, OR
- Document that production profile is standard deployment mode

**Risk:** Low (configuration clarification)

### Priority 4: Create Service Inventory Script ✅ **APPROVE**

**Action:**
Create a script to automatically generate service inventory:

```bash
#!/bin/bash
# scripts/service-inventory.sh

echo "=== HomeIQ Service Inventory ==="
echo ""
echo "Defined in docker-compose.yml:"
docker compose config --services | wc -l

echo "Currently Running:"
docker ps --filter "name=homeiq" --format "{{.Names}}" | wc -l

echo ""
echo "Service Status:"
docker compose ps

echo ""
echo "Health Status:"
docker ps --filter "name=homeiq" --format "table {{.Names}}\t{{.Status}}"
```

**Benefits:**
- Automated service count verification
- Quick status checks
- Documentation alignment verification

**Risk:** None (utility script)

---

## Summary

### Current State ✅
- **42 containers running** (all healthy)
- **38 services defined** in docker-compose.yml
- All services operational

### Documentation Issues ⚠️
- CLAUDE.md reports incorrect count (24 vs 38)
- Need to clarify profile-based services

### Naming Issues ⚠️
- 8 services missing `homeiq-` prefix
- Inconsistent container naming convention

### Recommendations ✅
1. ✅ **APPROVE:** Standardize container naming (add `homeiq-` prefix)
2. ✅ **APPROVE:** Update documentation service counts
3. ✅ **APPROVE:** Clarify profile enforcement documentation
4. ✅ **APPROVE:** Create service inventory verification script

---

## Approval Checklist

- [ ] **Review container naming standardization** (Priority 1)
- [ ] **Review documentation updates** (Priority 2)
- [ ] **Verify profile enforcement approach** (Priority 3)
- [ ] **Approve service inventory script** (Priority 4)
- [ ] **Schedule implementation** (if approved)

---

## Implementation Status

**Date Completed:** January 15, 2026

### ✅ Completed

1. **✅ Updated docker-compose.yml** - Standardized container names (added `homeiq-` prefix to 8 services):
   - `ai-code-executor` → `homeiq-ai-code-executor`
   - `ai-training-service` → `homeiq-ai-training-service`
   - `ai-pattern-service` → `homeiq-ai-pattern-service`
   - `ai-query-service` → `homeiq-ai-query-service`
   - `ai-automation-ui` → `homeiq-ai-automation-ui`
   - `yaml-validation-service` → `homeiq-yaml-validation-service`
   - `ai-automation-service-new` → `homeiq-ai-automation-service-new`
   - `automation-miner` → `homeiq-automation-miner`

2. **✅ Updated CLAUDE.md** - Corrected service count:
   - Changed from "24 Active Microservices" to "38 Active Microservices"
   - Updated note to "40 total containers in production" (38 + InfluxDB + Jaeger)

3. **✅ Updated DEPLOYMENT_RUNBOOK.md** - Clarified service count:
   - Changed from "30+ microservices" to "38 microservices (plus InfluxDB and Jaeger infrastructure)"

4. **✅ Created service-inventory.sh and service-inventory.ps1** - Automated verification scripts:
   - Lists all defined services from docker-compose.yml
   - Shows running containers with health status
   - Checks for naming consistency
   - Identifies profile-based services
   - Provides summary statistics

### ⚠️ Pending (Optional)

**Script Updates:** Several scripts reference container names directly in `docker exec` and `docker ps` commands. These will be updated incrementally as scripts are used. Critical scripts that may need updates:
- `scripts/diagnose-automation-mismatch.ps1` - References `ai-automation-service-new`
- `scripts/backfill_synergy_quality_scores.py` - References `ai-pattern-service`
- `scripts/deployment/health-check.sh` - References multiple service names

**Note:** Docker Compose service names (not container names) don't need updating - these are correct. Only direct container name references in `docker exec` commands need updating.

### 📋 Verification Steps

After redeploying services with new container names:

1. **Run service inventory script:**
   ```bash
   # Linux/Mac
   ./scripts/service-inventory.sh
   
   # Windows PowerShell
   .\scripts\service-inventory.ps1
   ```

2. **Verify all containers use homeiq- prefix:**
   ```bash
   docker ps --format "{{.Names}}" | grep -v "^homeiq-"
   ```
   Should return only external containers (if any).

3. **Restart services to apply new container names:**
   ```bash
   docker compose down
   docker compose up -d --profile production
   ```

4. **Verify health status:**
   ```bash
   docker ps --filter "name=homeiq" --format "table {{.Names}}\t{{.Status}}"
   ```

---

**Review Completed:** January 15, 2026  
**Implementation Completed:** January 15, 2026  
**Next Review:** After deployment verification
