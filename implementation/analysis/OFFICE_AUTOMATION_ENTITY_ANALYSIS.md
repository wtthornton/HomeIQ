# Office Automation YAML Deep Dive Analysis

**Date:** December 31, 2025  
**Automation ID:** `office_themed_interactive_motion_lighting`  
**Status:** ❌ **CRITICAL ISSUES FOUND** - Multiple non-existent entities referenced

## Executive Summary

This automation references **8 entities that do not exist** in the deployed Home Assistant system. The automation was likely created using placeholder/fictional entity names rather than actual discovered entities. **This automation will fail to execute** when triggered.

## Entity Validation Results

### ❌ NON-EXISTENT ENTITIES (8 total)

| Entity ID | Domain | Status | Notes |
|-----------|--------|--------|-------|
| `binary_sensor.office_motion_1` | binary_sensor | ❌ NOT FOUND | Referenced in triggers |
| `binary_sensor.office_motion_2` | binary_sensor | ❌ NOT FOUND | Referenced in triggers |
| `binary_sensor.office_motion_3` | binary_sensor | ❌ NOT FOUND | Referenced in triggers |
| `counter.office_motion_burst` | counter | ❌ NOT FOUND | Referenced in actions (increment/reset) |
| `light.office_main` | light | ❌ NOT FOUND | Referenced in scene snapshots and actions |
| `light.office_desk_lamp` | light | ❌ NOT FOUND | Referenced in scene snapshots and actions |
| `light.office_accent_strip` | light | ❌ NOT FOUND | Referenced in scene snapshots and actions |
| `binary_sensor.office_occupied_90min` | binary_sensor | ❌ NOT FOUND | Referenced in condition check |

### ✅ EXISTING ENTITIES (Similar/Related)

| Entity ID | Domain | Status | Notes |
|-----------|--------|--------|-------|
| `binary_sensor.office_motion_area` | binary_sensor | ✅ EXISTS | Single motion sensor (not 3 separate ones) |
| `binary_sensor.ps_fp2_office` | binary_sensor | ✅ EXISTS | Presence sensor (FP2) |
| `light.office` | light | ✅ EXISTS | Single office light (not "office_main") |
| `light.hue_office_back_left` | light | ✅ EXISTS | Hue downlight in office |
| `scene.office_work` | scene | ✅ EXISTS | Has `area_id: office` |

### ✅ AREA VALIDATION

| Area ID | Status | Notes |
|---------|--------|-------|
| `office` | ✅ EXISTS | Confirmed via `scene.office_work` entity |

## Detailed Analysis

### 1. Motion Sensor References

**Automation References:**
```yaml
entity_id:
  - binary_sensor.office_motion_1
  - binary_sensor.office_motion_2
  - binary_sensor.office_motion_3
```

**Actual System:**
- `binary_sensor.office_motion_area` - Single motion sensor (Hue platform)
- `binary_sensor.ps_fp2_office` - Presence sensor (HomeKit controller)

**Issue:** Automation expects 3 separate motion sensors, but only 1 motion sensor exists (`office_motion_area`).

### 2. Counter Entity

**Automation References:**
```yaml
entity_id: counter.office_motion_burst
action: counter.increment
action: counter.reset
```

**Actual System:**
- ❌ No `counter.office_motion_burst` exists

**Issue:** Counter is used to track motion bursts (increment on motion, reset after 10s). This counter must be created manually in Home Assistant configuration.

### 3. Light Entities

**Automation References:**
```yaml
snapshot_entities:
  - light.office_main
  - light.office_desk_lamp
  - light.office_accent_strip
```

**Actual System:**
- `light.office` - Single office light (Hue platform)
- `light.hue_office_back_left` - Hue downlight

**Issue:** Automation expects 3 separate lights (main, desk lamp, accent strip), but only 2 lights exist in office area.

### 4. Occupancy Sensor

**Automation References:**
```yaml
condition: state
entity_id: binary_sensor.office_occupied_90min
state: 'on'
```

**Actual System:**
- `binary_sensor.ps_fp2_office` - Presence sensor (but not named "office_occupied_90min")

**Issue:** The automation checks for a 90-minute occupancy sensor, but the actual presence sensor has a different entity ID.

### 5. Area-Based Light Control

**Automation References:**
```yaml
target:
  area_id: office
action: light.turn_on
```

**Status:** ✅ **VALID** - The `office` area exists (confirmed via `scene.office_work`).

## Automation Logic Issues

### Issue 1: Motion Detection Logic
The automation triggers on 3 motion sensors that don't exist. Even if one motion sensor exists (`office_motion_area`), the automation won't work as designed because:
- It expects 3 separate sensors for redundancy/coverage
- The variable `any_motion_on` checks all 3 sensors

### Issue 2: Counter Dependency
The "celebration easter egg" feature depends on `counter.office_motion_burst` which doesn't exist. This will cause:
- `counter.increment` action to fail
- `counter.reset` action to fail
- Celebration logic to never trigger

### Issue 3: Scene Snapshots
All scene creation actions reference non-existent lights:
- `scene.office_themed_interactive_motion_lighting_restore` - Will fail (lights don't exist)
- `scene.office_focus_mode_restore` - Will fail (lights don't exist)
- `scene.office_themed_interactive_motion_lighting_dimming_restore` - Will fail (lights don't exist)

### Issue 4: Focus Mode Condition
The focus mode sequence checks `binary_sensor.office_occupied_90min` which doesn't exist. This condition will always fail, preventing focus mode from activating.

## Recommendations

### Option 1: Fix Automation to Use Real Entities

**Replace motion sensors:**
```yaml
entity_id:
  - binary_sensor.office_motion_area  # Use existing motion sensor
  # Remove office_motion_2 and office_motion_3
```

**Create missing counter:**
Add to `configuration.yaml`:
```yaml
counter:
  office_motion_burst:
    name: Office Motion Burst
    initial: 0
    step: 1
```

**Replace light entities:**
```yaml
snapshot_entities:
  - light.office  # Use existing office light
  - light.hue_office_back_left  # Use existing Hue downlight
  # Remove light.office_desk_lamp and light.office_accent_strip
```

**Replace occupancy sensor:**
```yaml
condition: state
entity_id: binary_sensor.ps_fp2_office  # Use existing presence sensor
state: 'on'
```

### Option 2: Create Missing Entities

If the automation design requires these specific entities:
1. **Create counter:** Add `counter.office_motion_burst` to configuration
2. **Rename/alias lights:** Use Home Assistant entity registry to create aliases or rename existing lights
3. **Create helper sensors:** Use template sensors or helpers to create `binary_sensor.office_occupied_90min` from `binary_sensor.ps_fp2_office`

### Option 3: Simplify Automation

Given the actual entities available, simplify the automation:
- Use single motion sensor (`office_motion_area`)
- Use 2 lights instead of 3
- Remove counter-based celebration (or use simpler logic)
- Use existing presence sensor directly

## Validation Commands

To verify entities exist, use:
```powershell
# Check motion sensors
Invoke-RestMethod -Uri "http://localhost:8006/api/entities?domain=binary_sensor&limit=1000" | ConvertTo-Json | Select-String -Pattern "office"

# Check lights
Invoke-RestMethod -Uri "http://localhost:8006/api/entities?domain=light&limit=1000" | ConvertTo-Json | Select-String -Pattern "office"

# Check counters
Invoke-RestMethod -Uri "http://localhost:8006/api/entities?domain=counter&limit=1000" | ConvertTo-Json

# Check all office entities
$entities = Invoke-RestMethod -Uri "http://localhost:8006/api/entities?limit=10000"
$entities.entities | Where-Object { $_.entity_id -like "*office*" } | Select-Object entity_id, domain, area_id
```

## Conclusion

**This automation was created with fictional entity names and will not work in the deployed system.** All 8 referenced entities either don't exist or have different names. The automation needs to be updated to use actual discovered entities or the missing entities need to be created/configured in Home Assistant.

**Priority:** 🔴 **CRITICAL** - Automation is non-functional and will generate errors when triggered.
