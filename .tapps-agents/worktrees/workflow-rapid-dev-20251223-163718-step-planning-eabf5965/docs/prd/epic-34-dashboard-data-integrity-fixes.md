# Epic 34: Dashboard Data Integrity Fixes - Brownfield Enhancement

## Epic Goal

Fix 3 critical bugs preventing Health Dashboard from displaying real-time metrics and per-API statistics.

## Epic Description

### Existing System Context

**Current functionality:**
- Health Dashboard (http://localhost:3000/) with 13 tabs
- Admin API (port 8003) provides real-time metrics endpoint
- Dependencies tab should show per-API statistics for 12 services
- Overview tab shows system-wide event rates

**Technology stack:**
- Frontend: React + TypeScript, Backend: Python + FastAPI

**Integration:** Frontend → `/api/v1/metrics/realtime` → admin-api → service health endpoints

### Enhancement Details

**Three simple bug fixes:**

1. **Python Runtime Error** - `stats_endpoints.py` uses undefined variable `start_time` (lines 833, 1007), causing ALL per-API metrics to fail

2. **API Endpoint Mismatch** - Frontend calls `/api/v1/metrics/realtime` but backend has `/api/v1/real-time-metrics` (wrong path)

3. **Wrong Metric Label** - Overview tab shows "Events per Minute" but displays events per hour data (confusing)

**Impact:** Dependencies tab shows "No metrics available" (symptom of bug #1)

**How it integrates:**
- Minimal changes (add 2 variable declarations, fix 1 path, update 2 labels)
- No API contract changes
- No database changes
- Backwards compatible

**Success criteria:**
1. Dependencies tab displays 12 services with metrics
2. Overview tab shows correct "Events per Hour" label  
3. No Python errors in logs

## Stories

### Story 34.1: Fix Python Error and API Endpoint

**Description:** Fix undefined `start_time` variable causing all per-API metrics to fail, and correct API endpoint path mismatch.

**Changes:**
```python
# File: services/admin-api/src/stats_endpoints.py
# Line 792 - Add after function definition
async def _get_api_metrics(self, service_name: str, service_url: str) -> Dict[str, Any]:
    """Get metrics from a specific API service"""
    start_time = datetime.now()  # ← ADD THIS LINE
    try:
        # ... rest of function

# Line 901 - Add after function definition  
async def _get_api_metrics_with_timeout(self, service_name: str, service_url: str, timeout: int) -> Dict[str, Any]:
    """Get metrics from a specific API service with individual timeout"""
    start_time = datetime.now()  # ← ADD THIS LINE
    try:
        # ... rest of function
```

```typescript
// File: services/health-dashboard/src/services/api.ts
// Line 246 - Fix endpoint path
async getRealTimeMetrics(): Promise<any> {
  return this.fetchWithErrorHandling<any>(`${this.baseUrl}/api/v1/real-time-metrics`);
  // Changed from: /api/v1/metrics/realtime
}
```

**Acceptance Criteria:**
- No "name 'start_time' is not defined" errors in logs
- All 12 services return valid metrics (not "error" status)
- Dependencies tab displays 12 services with green/yellow/red status colors
- Real-time metrics update every 5 seconds

**Testing:**
```bash
# Should show no errors
curl http://localhost:8003/api/v1/real-time-metrics | jq '.api_metrics[] | select(.status == "error")'
```

### Story 34.2: Fix Misleading Metric Label

**Description:** Update Overview tab to show "Events per Hour" instead of "Events per Minute" to match actual data.

**Changes:**
```typescript
// File: services/health-dashboard/src/components/tabs/OverviewTab.tsx
// Lines 331-332
metrics={{
  primary: {
    label: 'Events per Hour',  // Changed from 'Events per Minute'
    value: websocketMetrics?.events_per_minute || 0,
    unit: 'evt/h'  // Changed from 'evt/min'
  },
}}
```

**Acceptance Criteria:**
- Overview tab INGESTION card shows "Events per Hour" label
- Unit displays as "evt/h"
- No other labels incorrectly changed

**Testing:**
- Navigate to http://localhost:3000/, verify label shows "Events per Hour"

## Risk Assessment

**Risk Level:** ✅ Low - Simple variable declarations and label changes

**Rollback Plan:**
```bash
# Revert containers to previous images (< 2 min)
docker-compose stop admin-api health-dashboard
docker-compose up -d admin-api health-dashboard
```

**No breaking changes:** No API changes, no database changes, no service dependencies

## Definition of Done

- [ ] Story 34.1: Dependencies tab shows 12 services with metrics
- [ ] Story 34.2: Overview tab shows "Events per Hour" label
- [ ] No "start_time" errors in admin-api logs
- [ ] All 13 dashboard tabs still functional (no regressions)

## Implementation Summary

**Total changes:** 5 lines of code across 3 files

**Timeline:** 2-3 hours total (Story 34.1: 2 hrs, Story 34.2: 30 min)

**Files modified:**
- `services/admin-api/src/stats_endpoints.py` - Add 2 lines
- `services/health-dashboard/src/services/api.ts` - Change 1 line  
- `services/health-dashboard/src/components/tabs/OverviewTab.tsx` - Change 2 lines

## Epic Status

- **Status**: Ready for Implementation
- **Priority**: High - Dashboard broken
- **Effort**: 2-3 hours
- **Risk**: Low - Simple bug fixes
- **Impact**: Restores Dependencies tab + fixes confusing labels

