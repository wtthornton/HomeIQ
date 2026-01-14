# Service Metrics Enhancement - Prototype Design

**Created:** 2026-01-14  
**Status:** Prototype Design - Ready for Implementation  
**Epic:** Service Management Dashboard Enhancement

## Prototype Goal

Create a working prototype for **websocket-ingestion** service metrics to validate the architecture and approach before implementing for all services.

## Prototype Scope

### What's Included
- ✅ ServiceMetricsClient with basic caching
- ✅ useServiceMetrics hook
- ✅ MetricCard and MetricGroup components
- ✅ WebSocket Ingestion fetcher
- ✅ WebSocket Ingestion configuration
- ✅ Integration with ServiceDetailsModal

### What's Excluded (for now)
- ❌ Real-time auto-refresh (manual refresh only)
- ❌ All other services (just websocket-ingestion)
- ❌ Advanced error handling
- ❌ Accessibility features (basic only)
- ❌ Unit tests (manual testing)

## Prototype Architecture

```
ServiceDetailsModal (existing)
  └── ServiceMetrics (new)
       └── useServiceMetrics hook
            └── ServiceMetricsClient
                 └── fetchWebSocketIngestionMetrics
```

## Implementation Steps

### Step 1: Create ServiceMetricsClient

**File:** `services/health-dashboard/src/services/serviceMetricsClient.ts`

**Features:**
- Basic fetch functionality
- Simple in-memory cache
- Error handling
- Timeout support

### Step 2: Create useServiceMetrics Hook

**File:** `services/health-dashboard/src/hooks/useServiceMetrics.ts`

**Features:**
- State management (metrics, loading, error)
- Manual refresh function
- Basic cleanup

### Step 3: Create Metric Components

**Files:**
- `services/health-dashboard/src/components/ServiceMetrics.tsx`
- `services/health-dashboard/src/components/MetricGroup.tsx`
- `services/health-dashboard/src/components/MetricCard.tsx`

**Features:**
- Basic metric display
- Dark mode support
- Status indicators

### Step 4: Create WebSocket Ingestion Fetcher

**File:** `services/health-dashboard/src/services/fetchers/websocketIngestionFetcher.ts`

**Features:**
- Call `/health` endpoint
- Transform response
- Error handling

### Step 5: Create Configuration

**File:** `services/health-dashboard/src/config/serviceMetricsConfig.ts`

**Features:**
- WebSocket Ingestion configuration
- Metric definitions
- Basic formatters

### Step 6: Integrate with ServiceDetailsModal

**File:** `services/health-dashboard/src/components/ServiceDetailsModal.tsx`

**Changes:**
- Add ServiceMetrics component
- Pass serviceId prop
- Handle loading/error states

## Prototype Data Flow

```
1. User clicks "Details" on websocket-ingestion service
   │
   ▼
2. ServiceDetailsModal opens
   │
   ▼
3. ServiceMetrics component mounts
   │
   ▼
4. useServiceMetrics hook calls fetchMetrics('websocket-ingestion')
   │
   ▼
5. ServiceMetricsClient checks cache
   │
   ├─► Cache hit & fresh → Return cached metrics
   │
   └─► Cache miss or stale → Fetch from http://localhost:8001/health
       │
       ├─► Success → Transform & cache → Return metrics
       │
       └─► Failure → Return null → Show generic metrics
```

## Expected Results

### Success Criteria
- ✅ WebSocket Ingestion service shows service-specific metrics
- ✅ Metrics display correctly in modal
- ✅ Cache works (second open is faster)
- ✅ Error handling works (shows generic metrics on failure)
- ✅ Dark mode works

### Metrics to Display

**Connection Status Group:**
- Connection Status (Connected/Disconnected)
- Connection Attempts (number)
- Last Connection (time)

**Event Processing Group:**
- Events Per Minute (number with unit)
- Total Events (number)
- Last Event (time)

**Errors Group:**
- Failed Connections (number)
- Circuit Breaker State (status)
- Last Error (text or "None")

**Resources Group:**
- Memory Usage (MB)
- CPU Usage (%)

## Testing Plan

### Manual Testing
1. **Happy Path:**
   - Open websocket-ingestion details
   - Verify metrics display
   - Close and reopen (test cache)
   - Verify metrics update

2. **Error Path:**
   - Stop websocket-ingestion service
   - Open details
   - Verify fallback to generic metrics
   - Verify error message

3. **Edge Cases:**
   - Service returns partial data
   - Service returns invalid data
   - Network timeout

## Validation Questions

After prototype, answer:
1. ✅ Does the architecture work as designed?
2. ✅ Is the data transformation correct?
3. ✅ Are the components reusable?
4. ✅ Is the configuration system flexible?
5. ✅ Is the caching effective?
6. ✅ Is error handling sufficient?

## Next Steps After Prototype

If prototype successful:
1. Add real-time auto-refresh
2. Add remaining services one by one
3. Add unit tests
4. Add accessibility features
5. Optimize performance

If prototype needs changes:
1. Refactor architecture based on learnings
2. Update technical design
3. Update requirements if needed
4. Re-prototype if major changes

---

**Document Status:** Prototype Design - Ready for Implementation  
**Last Updated:** 2026-01-14
