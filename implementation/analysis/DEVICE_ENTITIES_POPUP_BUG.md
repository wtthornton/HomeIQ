# Device Entities Popup Bug - Count Mismatch

**Date:** January 6, 2025  
**Issue:** Main device list shows "4 entities" but popup shows "Entities (0)"  
**Device:** Presence-Sensor-FP2-8B8A (device_id: `07765655ee253761bb57e33b0b04aa6b`)

## Problem

- **Main Device List:** Shows "4 entities" (correct)
- **Popup Modal:** Shows "Entities (0)" (incorrect)

## Root Cause Analysis

### API Verification ✅
The API correctly returns 4 entities when queried directly:
```bash
GET /api/entities?device_id=07765655ee253761bb57e33b0b04aa6b
→ Returns 4 entities:
  1. sensor.presence_sensor_fp2_8b8a_light_sensor_light_level
  2. button.presence_sensor_fp2_8b8a_identify
  3. binary_sensor.ps_fp2_office
  4. binary_sensor.ps_fp2_desk
```

### Frontend Issue ❌
The popup filters entities from the frontend `entities` state array:
```typescript
// services/health-dashboard/src/components/tabs/DevicesTab.tsx:85-88
const deviceEntities = useMemo(() => {
  if (!selectedDevice) return [];
  return entities.filter(e => e.device_id === selectedDevice.device_id);
}, [selectedDevice, entities]);
```

**Problem:** The `entities` array in the frontend state is not populated with all entities, or the entities are missing the correct `device_id` field.

## Code Flow

1. **Initial Load:** `useDevices()` hook calls `fetchEntities()` with `limit: 10000`
2. **Entity Storage:** Entities stored in React state: `setEntities(response.entities || [])`
3. **Popup Filter:** Filters from state array: `entities.filter(e => e.device_id === selectedDevice.device_id)`

## Possible Causes

1. **Entities not loaded:** The `fetchEntities()` call might be failing silently
2. **State not updating:** The `entities` state might not be populated correctly
3. **Race condition:** Entities might not be loaded when popup opens
4. **Device ID mismatch:** The `device_id` in the entities array might not match (case sensitivity, format)
5. **Limit issue:** Even though limit is 10000, if there are more entities, they won't be loaded

## Solution

The popup should query the API directly instead of filtering from the state array, OR we need to ensure all entities are loaded into state.

### Option 1: Query API Directly (Recommended)
Modify the popup to fetch entities directly from the API when a device is selected:
```typescript
useEffect(() => {
  if (selectedDevice) {
    dataApi.getEntities({ device_id: selectedDevice.device_id })
      .then(response => setDeviceEntities(response.entities || []))
      .catch(err => console.error('Failed to fetch device entities:', err));
  }
}, [selectedDevice]);
```

### Option 2: Fix State Loading
Ensure all entities are loaded into state on initial fetch, and verify the filtering logic works correctly.

## Status

- ✅ API returns correct data (4 entities)
- ✅ Device count query works correctly (SQL JOIN)
- ❌ Frontend state filtering fails (entities not in state array)

