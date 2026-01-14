# Service Metrics Implementation Guide

**Created:** 2026-01-14  
**Status:** Implementation Guide - Ready for Development  
**Epic:** Service Management Dashboard Enhancement

## Overview

This guide provides step-by-step instructions for implementing the service-specific metrics enhancement. The prototype skeleton code has been created and is ready for testing and refinement.

## Files Created

### Core Infrastructure
- ✅ `services/health-dashboard/src/services/serviceMetricsClient.ts` - Metrics fetching and caching
- ✅ `services/health-dashboard/src/types/serviceMetrics.ts` - TypeScript type definitions
- ✅ `services/health-dashboard/src/hooks/useServiceMetrics.ts` - React hook for metrics state

### Components
- ✅ `services/health-dashboard/src/components/ServiceMetrics.tsx` - Main metrics component
- ✅ `services/health-dashboard/src/components/MetricGroup.tsx` - Metric group display
- ✅ `services/health-dashboard/src/components/MetricCard.tsx` - Individual metric display

### Services & Configuration
- ✅ `services/health-dashboard/src/services/fetchers/websocketIngestionFetcher.ts` - WebSocket Ingestion fetcher
- ✅ `services/health-dashboard/src/config/serviceMetricsConfig.ts` - Service metrics configuration
- ✅ `services/health-dashboard/src/utils/metricFormatters.ts` - Metric formatting utilities

### Integration
- ✅ `services/health-dashboard/src/components/ServiceDetailsModal.tsx` - Updated to use ServiceMetrics

## Implementation Steps

### Step 1: Test Prototype

1. **Start Services:**
   ```bash
   # Ensure websocket-ingestion service is running
   docker-compose up websocket-ingestion
   ```

2. **Test Health Endpoint:**
   ```bash
   # Verify health endpoint is accessible
   curl http://localhost:8001/health
   ```

3. **Test in Dashboard:**
   - Open health dashboard
   - Navigate to Services tab
   - Click "Details" on websocket-ingestion service
   - Verify service-specific metrics display

### Step 2: Fix Any Issues

**Common Issues:**

1. **CORS Errors:**
   - Ensure services allow CORS from dashboard origin
   - Or use admin-api as proxy

2. **Type Errors:**
   - Check TypeScript compilation
   - Fix any import/type mismatches

3. **Missing Data:**
   - Verify health endpoint returns expected data
   - Check fetcher transformation logic

### Step 3: Enhance Prototype

**Add Features:**
- [ ] Real-time auto-refresh
- [ ] Better error messages
- [ ] Loading indicators
- [ ] Refresh button
- [ ] Accessibility improvements

### Step 4: Add More Services

**For Each Service:**

1. **Create Fetcher:**
   ```typescript
   // services/health-dashboard/src/services/fetchers/{serviceId}Fetcher.ts
   export async function fetch{Service}Metrics(
     serviceId: string
   ): Promise<ServiceMetrics | null> {
     // Fetch from service endpoint
     // Transform to unified format
     // Return metrics
   }
   ```

2. **Add Configuration:**
   ```typescript
   // In serviceMetricsConfig.ts
   export const {serviceId}Config: ServiceMetricsConfig = {
     serviceId: '{service-id}',
     fetcher: fetch{Service}Metrics,
     groups: [
       // Define metric groups
     ],
   };
   
   // Add to registry
   export const SERVICE_METRICS_CONFIG = {
     // ... existing
     '{service-id}': {serviceId}Config,
   };
   ```

3. **Test:**
   - Verify metrics display correctly
   - Test error handling
   - Test caching

### Step 5: Add Unit Tests

**Test Files to Create:**
- `services/health-dashboard/src/services/__tests__/serviceMetricsClient.test.ts`
- `services/health-dashboard/src/hooks/__tests__/useServiceMetrics.test.ts`
- `services/health-dashboard/src/components/__tests__/ServiceMetrics.test.tsx`
- `services/health-dashboard/src/utils/__tests__/metricFormatters.test.ts`

### Step 6: Add Integration Tests

**Test Scenarios:**
- Fetch metrics for configured service
- Fallback to generic metrics for unconfigured service
- Error handling when service unavailable
- Cache behavior
- Real-time updates

## Testing Checklist

### Functional Testing
- [ ] WebSocket Ingestion metrics display correctly
- [ ] Metrics update when service status changes
- [ ] Cache works (second open is faster)
- [ ] Error handling works (shows generic metrics on failure)
- [ ] Dark mode works
- [ ] All metric types format correctly

### Error Scenarios
- [ ] Service unavailable (shows generic metrics)
- [ ] Network timeout (shows error message)
- [ ] Invalid response (shows error message)
- [ ] Partial data (shows available metrics)

### Performance
- [ ] Modal opens quickly (< 500ms)
- [ ] Metrics load within 2 seconds
- [ ] Cache reduces API calls
- [ ] No performance impact on main dashboard

## Next Steps After Prototype

1. **Add Real-Time Updates:**
   - Enable auto-refresh in useServiceMetrics
   - Add refresh interval configuration
   - Test update behavior

2. **Add Remaining Services:**
   - Data API
   - Admin API
   - InfluxDB
   - External data services
   - AI services

3. **Enhance Components:**
   - Add StatusBadge component
   - Add ProgressBar component
   - Add TrendIndicator component
   - Add TimeAgo component

4. **Add Accessibility:**
   - ARIA labels
   - Keyboard navigation
   - Screen reader support
   - Focus management

5. **Optimize:**
   - Performance tuning
   - Bundle size optimization
   - Code splitting
   - Memoization

## Troubleshooting

### Metrics Not Displaying

1. **Check Configuration:**
   - Verify service is in SERVICE_METRICS_CONFIG
   - Check fetcher is registered

2. **Check Network:**
   - Verify service endpoint is accessible
   - Check CORS settings
   - Check network tab in browser dev tools

3. **Check Console:**
   - Look for error messages
   - Check fetch errors
   - Check transformation errors

### Type Errors

1. **Check Imports:**
   - Verify all imports are correct
   - Check type definitions

2. **Check Types:**
   - Verify ServiceMetrics type matches data
   - Check MetricDefinition types

### Performance Issues

1. **Check Cache:**
   - Verify cache is working
   - Check TTL settings

2. **Check API Calls:**
   - Verify no duplicate calls
   - Check request timing

## Code Review Checklist

- [ ] All TypeScript types are correct
- [ ] Error handling is comprehensive
- [ ] Code follows project conventions
- [ ] Components are accessible
- [ ] Dark mode is supported
- [ ] Performance is acceptable
- [ ] Tests are written
- [ ] Documentation is updated

---

**Document Status:** Implementation Guide - Ready for Development  
**Last Updated:** 2026-01-14
