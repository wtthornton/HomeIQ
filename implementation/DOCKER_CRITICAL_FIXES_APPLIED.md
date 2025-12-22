# Docker Critical Fixes Applied

**Date:** January 2025  
**Status:** ✅ COMPLETED  
**Fixes Applied:** 2 of 3 critical issues

---

## Fixes Applied

### ✅ 1. Fixed Admin API Port Mapping

**Issue:** `admin-api` service mapped port `8003:8004` instead of `8004:8004`

**File:** `docker-compose.yml`  
**Line:** 133  
**Change:**
```yaml
# Before
ports:
  - "8003:8004"

# After
ports:
  - "8004:8004"
```

**Impact:** 
- ✅ Port mapping now consistent with service port
- ✅ Eliminates confusion about which port to use
- ✅ Matches documentation and health check expectations

---

### ✅ 2. Removed Invalid SPORTS_DATA_URL Reference

**Issue:** `proactive-agent-service` referenced non-existent `sports-data` service

**File:** `docker-compose.yml`  
**Line:** 984  
**Change:**
```yaml
# Before
- SPORTS_DATA_URL=http://sports-data:8005

# After
# SPORTS_DATA_URL removed - sports data now accessed via data-api service (port 8006)
# See: implementation/sports-architecture-simplification-summary.md
```

**Rationale:**
- Sports data functionality was moved to `data-api` service (Epic 11)
- `sports-data` service was archived (see `implementation/sports-architecture-simplification-summary.md`)
- Sports data is now accessed via `data-api` at port 8006

**Impact:**
- ✅ Removes invalid service reference
- ✅ Prevents connection errors
- ✅ Documents the architectural change

---

## Verification Status

### ✅ Health Check Commands (curl)

**Status:** Verified - All services using curl have curl installed

**Verified Services:**
- ✅ `websocket-ingestion` - curl installed (line 25)
- ✅ `admin-api` - curl installed (line 25)
- ✅ `data-retention` - curl installed (line 32)
- ✅ `carbon-intensity-service` - curl installed (line 25)
- ✅ `health-dashboard` - curl installed (line 48)
- ✅ `influxdb` - Base image includes curl

**Note:** Services using Python-based health checks (e.g., `data-api`) don't require curl.

**Conclusion:** All health check commands are valid. No changes needed.

---

## Remaining Issues

### ⚠️ Missing `sports-data` Service (Non-Critical)

**Status:** Documented, not blocking

**Details:**
- `sports-data` service was intentionally archived
- Sports data functionality moved to `data-api` service
- Reference removed from `proactive-agent-service`
- No action needed - architecture change is correct

---

## Testing Recommendations

After applying these fixes, test:

1. **Port Mapping:**
   ```bash
   # Verify admin-api is accessible on port 8004
   curl http://localhost:8004/health
   ```

2. **Service Dependencies:**
   ```bash
   # Verify proactive-agent-service starts without errors
   docker compose logs proactive-agent-service
   ```

3. **Health Checks:**
   ```bash
   # Verify all services pass health checks
   docker compose ps
   # All services should show "healthy" status
   ```

---

## Files Modified

1. `docker-compose.yml`
   - Line 133: Fixed admin-api port mapping
   - Line 984: Removed SPORTS_DATA_URL reference

---

## Next Steps

### Immediate (Completed)
- ✅ Fix port mapping
- ✅ Remove invalid service reference
- ✅ Verify health check commands

### Short-Term (This Week)
- [ ] Standardize environment variable naming
- [ ] Fix hardcoded IP addresses
- [ ] Create root `.dockerignore`
- [ ] Add CPU limits consistently
- [ ] Fix empty frontend environment variables

### Medium-Term (This Month)
- [ ] Complete `docker-compose.prod.yml`
- [ ] Security hardening
- [ ] Performance optimization

---

## References

- **Full Review:** `implementation/DOCKER_DEPLOYMENT_REVIEW_2025.md`
- **Sports Architecture:** `implementation/sports-architecture-simplification-summary.md`
- **Deployment Guide:** `docs/DEPLOYMENT_GUIDE.md`

