# Data Sources UI Fix Plan

## Problem Analysis

### Issues Identified

1. **Test Button Not Working**
   - Location: `services/health-dashboard/src/components/DataSourcesPanel.tsx` line 337
   - Current: Empty onClick handler with TODO comment
   - Required: Call service health endpoint and show result

2. **Configure Button Not Working**
   - Location: `services/health-dashboard/src/components/DataSourcesPanel.tsx` line 327
   - Current: Empty onClick handler with TODO comment
   - Required: Open configuration modal or navigate to config page

3. **Error Status Not Resolving**
   - Services showing error status even after environment variables are fixed
   - Need to verify services are running and health endpoints are accessible
   - Need to ensure admin-api properly reports service health

## Solution Plan

### Phase 1: Implement Test Button Functionality

**Requirements:**
- Test button should call the service's `/health` endpoint
- Show loading state during test
- Display success/error message with details
- Update service status after test

**Implementation:**
1. Create API method in `api.ts` to test service health
2. Add state management for test results
3. Implement test handler in DataSourcesPanel
4. Add UI feedback (toast notifications or inline messages)

**Service Ports:**
- Weather API: 8009
- Carbon Intensity: 8010
- Electricity Pricing: 8011
- Air Quality: 8012
- Calendar: 8013
- Smart Meter: 8014

### Phase 2: Implement Configure Button Functionality

**Requirements:**
- Configure button should open configuration modal
- Modal should show current configuration (non-sensitive)
- Allow editing of configuration values
- Save changes via admin-api config endpoints

**Implementation Options:**
1. **Option A:** Simple modal with form (recommended for MVP)
2. **Option B:** Navigate to dedicated configuration page
3. **Option C:** Open external configuration file editor

**Recommended:** Option A - Modal with form

**Configuration Fields per Service:**

**Carbon Intensity:**
- WATTTIME_USERNAME
- WATTTIME_PASSWORD (masked)
- GRID_REGION

**Air Quality:**
- WEATHER_API_KEY (masked)
- LATITUDE
- LONGITUDE

**Electricity Pricing:**
- PRICING_PROVIDER
- PRICING_API_KEY (masked, optional)

**Calendar:**
- CALENDAR_ENTITIES
- CALENDAR_FETCH_INTERVAL

**Smart Meter:**
- METER_TYPE
- METER_DEVICE_ID

### Phase 3: Fix Error Status Reporting

**Requirements:**
- Ensure services are running with production profile
- Verify health endpoints are accessible
- Fix admin-api health endpoint to properly report service status
- Handle missing credentials gracefully

**Implementation:**
1. Check if services are running: `docker-compose --profile production ps`
2. Verify health endpoints respond correctly
3. Update admin-api health endpoint to include credential status
4. Update DataSourcesPanel to show credential status clearly

### Phase 4: Enhance Error Messages

**Requirements:**
- Show specific error messages for each service
- Display credential missing status clearly
- Provide actionable guidance

**Implementation:**
- Update DataSourcesPanel to show error_message from health response
- Add credential status indicator (🔑 icon)
- Show helpful tooltips with setup instructions

## Implementation Steps

### Step 1: Add Test Service API Method

File: `services/health-dashboard/src/services/api.ts`

Add method to test individual service health:
```typescript
async testServiceHealth(serviceName: string, port: number): Promise<{success: boolean, message: string, data?: any}>
```

### Step 2: Create Configuration Modal Component

File: `services/health-dashboard/src/components/DataSourceConfigModal.tsx`

Create reusable modal component for service configuration.

### Step 3: Update DataSourcesPanel Component

File: `services/health-dashboard/src/components/DataSourcesPanel.tsx`

- Add state for test results
- Add state for config modal
- Implement test button handler
- Implement configure button handler
- Add toast notifications for feedback

### Step 4: Update Admin API Health Endpoint

File: `services/admin-api/src/health_endpoints.py`

Ensure external data source services are properly checked and their status is reported with credential information.

### Step 5: Verify Services Are Running

- Check docker-compose services status
- Ensure services are started with production profile
- Verify health endpoints are accessible

## Testing Checklist

- [ ] Test button works for all services
- [ ] Test shows loading state
- [ ] Test displays success/error messages
- [ ] Configure button opens modal
- [ ] Configuration modal shows current values
- [ ] Configuration can be saved
- [ ] Error status updates after fixing credentials
- [ ] Services show correct status after restart
- [ ] Credential missing status is clearly indicated

## Files to Modify

1. `services/health-dashboard/src/services/api.ts` - Add test service method
2. `services/health-dashboard/src/components/DataSourcesPanel.tsx` - Implement buttons
3. `services/health-dashboard/src/components/DataSourceConfigModal.tsx` - New component
4. `services/admin-api/src/health_endpoints.py` - Enhance health reporting (if needed)

## Dependencies

- React hooks (useState, useEffect)
- Toast notification library (or custom implementation)
- Modal component (or create custom)

