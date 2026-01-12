# HomeIQ Improvement Plan: Home Assistant 2026.1 Release

**Date:** January 8, 2026  
**Source:** [Home Assistant 2026.1 Release Notes](https://www.home-assistant.io/blog/2026/01/07/release-20261/)  
**Focus Areas:** Devices and Automation Improvements

---

## Executive Summary

Home Assistant 2026.1 introduces significant improvements to device management, automation triggers, and protocol organization. This plan outlines how HomeIQ can leverage these new features to enhance device tracking, automation generation, and user experience.

**Key Improvements in HA 2026.1:**
- ✅ New Devices page for unassigned devices
- ✅ Purpose-specific triggers and conditions (Home Assistant Labs)
- ✅ Enhanced protocol dashboards (Zigbee, Z-Wave, Thread, Matter, Bluetooth, KNX, Insteon)
- ✅ New trigger types: Button, Climate (expanded), Device tracker, Humidifier, Light, Lock, Scene, Siren, Update
- ✅ Better targeting (areas, floors, labels)

---

## 1. Device Management Improvements

### 1.1 Unassigned Devices Page (High Priority)

**Home Assistant Feature:**
- New **Devices** page showing all devices not assigned to any area
- Makes it easy to find and manage "orphaned" devices

**HomeIQ Implementation:**

#### 1.1.1 Data-API Enhancement
**Service:** `data-api` (Port 8006)  
**Endpoint:** `GET /api/v1/devices/unassigned`

**Requirements:**
- Add new endpoint to filter devices where `area_id IS NULL`
- Support filtering by integration (e.g., `?integration=zigbee2mqtt`)
- Include device metadata (manufacturer, model, integration, labels)
- Support pagination for large device lists

**Files to Modify:**
- `services/data-api/src/routers/devices_router.py`
- `services/data-api/src/services/device_service.py`

**Database Query:**
```sql
SELECT * FROM devices 
WHERE area_id IS NULL 
ORDER BY integration, name
```

#### 1.1.2 Dashboard UI Enhancement
**Service:** `health-dashboard` (Port 3000)

**Requirements:**
- Add new "Unassigned Devices" page/section
- Display device list with:
  - Device name, manufacturer, model
  - Integration (with protocol badge)
  - Suggested area (if available)
  - Action buttons: Assign to area, View details, Configure
- Support filtering by integration/protocol
- Link to protocol-specific configuration (see 1.2)

**UI Components:**
- `components/devices/UnassignedDevicesPage.tsx`
- `components/devices/UnassignedDeviceCard.tsx`
- Update navigation/routing

**Priority:** High  
**Estimated Effort:** 2-3 days  
**Dependencies:** None

---

### 1.2 Protocol Dashboard Integration (Medium Priority)

**Home Assistant Feature:**
- Protocols section now appears prominently in Settings
- Dedicated dashboards for Zigbee, Z-Wave, Thread, Matter, Bluetooth, KNX, Insteon
- Easy navigation to protocol-specific configurations

**HomeIQ Implementation:**

#### 1.2.1 Protocol Detection and Classification
**Service:** `data-api`  
**Endpoint:** `GET /api/v1/devices/protocols`

**Requirements:**
- Detect protocol from integration field (zigbee2mqtt → Zigbee, zwave_js → Z-Wave, etc.)
- Group devices by protocol
- Provide protocol statistics (device count, health status)
- Link to protocol configuration URLs

**Protocol Mapping:**
```python
PROTOCOL_MAPPING = {
    "zigbee2mqtt": "Zigbee",
    "zwave_js": "Z-Wave",
    "thread": "Thread",
    "matter": "Matter",
    "bluetooth": "Bluetooth",
    "knx": "KNX",
    "insteon": "Insteon",
}
```

**Files to Modify:**
- `services/data-api/src/routers/devices_router.py`
- Add `services/data-api/src/services/protocol_service.py`

#### 1.2.2 Protocol Dashboard UI
**Service:** `health-dashboard`

**Requirements:**
- Add "Protocols" section to navigation (after core settings)
- Display protocol cards with:
  - Protocol name and icon
  - Device count
  - Health status (all devices online, some offline, etc.)
  - Link to protocol configuration (if available)
  - Link to protocol device list
- Only show protocols that have devices (matches HA behavior)

**UI Components:**
- `components/settings/ProtocolsSection.tsx`
- `components/protocols/ProtocolCard.tsx`
- `components/protocols/ProtocolDeviceList.tsx`

**Priority:** Medium  
**Estimated Effort:** 3-4 days  
**Dependencies:** 1.2.1 (protocol detection)

---

### 1.3 Enhanced Label Support (Low Priority)

**Home Assistant Feature:**
- Labels are now more prominent in device organization
- Used for filtering and grouping across devices

**Current HomeIQ Status:**
- ✅ Labels are already stored in database (`Device.labels` JSON column)
- ✅ Labels are captured from HA device registry
- ❌ Labels are not exposed in API endpoints
- ❌ Labels are not used in filtering/grouping

**HomeIQ Implementation:**

#### 1.3.1 Label Filtering API
**Service:** `data-api`  
**Endpoint:** `GET /api/v1/devices?labels=label1,label2`

**Requirements:**
- Add label filtering to device query endpoints
- Support filtering by multiple labels (AND/OR logic)
- Return devices that have any/all of the specified labels

**Files to Modify:**
- `services/data-api/src/routers/devices_router.py`
- `services/data-api/src/services/device_service.py`

#### 1.3.2 Label Management UI
**Service:** `health-dashboard`

**Requirements:**
- Display labels on device cards
- Add label filtering to device list
- Show label badges/chips
- Allow filtering by label in device views

**UI Components:**
- `components/devices/DeviceLabelBadge.tsx`
- Update `components/devices/DeviceList.tsx` with label filters

**Priority:** Low  
**Estimated Effort:** 2 days  
**Dependencies:** 1.3.1 (label filtering API)

---

## 2. Automation Improvements

### 2.1 Purpose-Specific Triggers Support (High Priority)

**Home Assistant Feature:**
- Purpose-specific triggers and conditions (Home Assistant Labs)
- Human-friendly language instead of technical state changes
- New trigger types: Button, Climate (expanded), Device tracker, Humidifier, Light, Lock, Scene, Siren, Update

**HomeIQ Implementation:**

#### 2.1.1 Schema Enhancement
**Service:** `shared/homeiq_automation`  
**File:** `shared/homeiq_automation/schema.py`

**Requirements:**
- Extend `HomeIQTrigger` to support purpose-specific trigger types
- Add new trigger platforms:
  - `button` - Button press triggers
  - `climate` - Expanded climate triggers (HVAC mode, temperature changes, humidity)
  - `device_tracker` - Device arrival/departure triggers
  - `humidifier` - Humidifier state changes
  - `light` - Brightness changes and thresholds
  - `lock` - Lock/unlock/jam triggers
  - `scene` - Scene activation triggers
  - `siren` - Siren on/off triggers
  - `update` - Update available triggers

**Schema Changes:**
```python
class HomeIQTrigger(BaseModel):
    platform: str = Field(..., description="Trigger platform")
    # Existing fields...
    
    # Purpose-specific trigger fields
    # Button triggers
    button_entity: str | None = None
    button_action: str | None = None  # "press", "double_press", etc.
    
    # Climate triggers
    climate_entity: str | None = None
    climate_mode: str | None = None  # "heating", "cooling", etc.
    temperature_threshold: float | None = None
    humidity_threshold: float | None = None
    
    # Device tracker triggers
    device_tracker_entity: str | None = None
    tracker_action: str | None = None  # "entered_home", "left_home", "first_arrived", "last_left"
    
    # Light triggers
    light_entity: str | None = None
    brightness_threshold: int | None = None
    
    # Lock triggers
    lock_entity: str | None = None
    lock_action: str | None = None  # "locked", "unlocked", "opened", "jammed"
    
    # Scene triggers
    scene_entity: str | None = None
    
    # Siren triggers
    siren_entity: str | None = None
    siren_state: str | None = None  # "on", "off"
    
    # Update triggers
    update_entity: str | None = None
    
    # Enhanced targeting (areas, floors, labels)
    target: dict[str, Any] | None = Field(None, description="Target specification (area_id, floor_id, labels)")
```

**Priority:** High  
**Estimated Effort:** 3-4 days  
**Dependencies:** None

#### 2.1.2 YAML Converter Enhancement
**Service:** `shared/homeiq_automation`  
**File:** `shared/homeiq_automation/yaml_transformer.py`

**Requirements:**
- Update YAML transformer to convert purpose-specific triggers to HA YAML format
- Handle new trigger types in both directions (HomeIQ → YAML, YAML → HomeIQ)
- Support enhanced targeting (areas, floors, labels) in YAML output

**Conversion Logic:**
- Button triggers: `platform: button`, `entity_id: button_entity`, `action: button_action`
- Climate triggers: `platform: climate`, `entity_id: climate_entity`, `mode: climate_mode`
- Device tracker triggers: `platform: device_tracker`, `entity_id: device_tracker_entity`, `event: tracker_action`
- etc.

**Priority:** High  
**Estimated Effort:** 4-5 days  
**Dependencies:** 2.1.1 (schema enhancement)

#### 2.1.3 Automation Generator Updates
**Service:** `ai-pattern-service`  
**File:** `services/ai-pattern-service/src/services/automation_generator.py`

**Requirements:**
- Update automation generation to use purpose-specific triggers when appropriate
- Prefer purpose-specific triggers over generic state triggers for better readability
- Use human-friendly language in generated automations

**Example:**
```python
# Before (generic state trigger)
trigger = HomeIQTrigger(
    platform="state",
    entity_id="button.living_room_button",
    to="pressed"
)

# After (purpose-specific trigger)
trigger = HomeIQTrigger(
    platform="button",
    button_entity="button.living_room_button",
    button_action="press"
)
```

**Priority:** High  
**Estimated Effort:** 3-4 days  
**Dependencies:** 2.1.1, 2.1.2

#### 2.1.4 UI Support for Purpose-Specific Triggers
**Service:** `ai-automation-ui`  
**File:** `services/ai-automation-ui/` (multiple files)

**Requirements:**
- Update automation editor to support purpose-specific trigger types
- Provide trigger type selector with human-friendly names
- Show trigger configuration UI based on selected trigger type
- Support enhanced targeting (areas, floors, labels) in trigger configuration

**UI Components:**
- `components/automation/TriggerEditor.tsx` - Enhanced trigger editor
- `components/automation/TriggerTypeSelector.tsx` - Trigger type selection
- `components/automation/TargetSelector.tsx` - Area/floor/label targeting

**Priority:** Medium  
**Estimated Effort:** 5-6 days  
**Dependencies:** 2.1.1, 2.1.2

---

### 2.2 Enhanced Targeting Support (Medium Priority)

**Home Assistant Feature:**
- Triggers and conditions can target areas, floors, or labels (not just entities)
- Redesigned automation flow display for better readability

**HomeIQ Implementation:**

#### 2.2.1 Schema Updates for Enhanced Targeting
**Service:** `shared/homeiq_automation`  
**File:** `shared/homeiq_automation/schema.py`

**Requirements:**
- Enhance `HomeIQTrigger`, `HomeIQCondition`, and `HomeIQAction` to support enhanced targeting
- Add `target` field to support area_id, floor_id, labels, device_id

**Schema Changes:**
```python
class Target(BaseModel):
    """Enhanced targeting for triggers, conditions, and actions."""
    area_id: str | list[str] | None = None
    floor_id: str | list[str] | None = None
    labels: list[str] | None = None
    device_id: str | list[str] | None = None
    entity_id: str | list[str] | None = None

class HomeIQTrigger(BaseModel):
    # Existing fields...
    target: Target | None = None  # Enhanced targeting
```

**Priority:** Medium  
**Estimated Effort:** 2 days  
**Dependencies:** None

#### 2.2.2 YAML Converter for Enhanced Targeting
**Service:** `shared/homeiq_automation`  
**File:** `shared/homeiq_automation/yaml_transformer.py`

**Requirements:**
- Convert enhanced targeting to HA YAML format
- Support area_id, floor_id, labels in YAML output
- Expand targets to entity_ids when converting to YAML (if needed)

**YAML Format:**
```yaml
trigger:
  platform: button
  target:
    area_id: living_room
    # OR
    labels:
      - outdoor
      - security
```

**Priority:** Medium  
**Estimated Effort:** 3-4 days  
**Dependencies:** 2.2.1

---

### 2.3 Automation Flow Display Improvements (Low Priority)

**Home Assistant Feature:**
- Redesigned automation flow display
- Better visualization of automation purpose and structure
- Clearer representation of targets (areas, floors, labels)

**HomeIQ Implementation:**

#### 2.3.1 Automation Visualization Enhancement
**Service:** `ai-automation-ui`  
**File:** `services/ai-automation-ui/` (automation visualization components)

**Requirements:**
- Enhance automation flow visualization to show:
  - Purpose-specific trigger types with icons
  - Enhanced targeting (areas, floors, labels) visually
  - Clearer connection between triggers, conditions, and actions
  - Human-readable trigger/condition/action descriptions

**UI Components:**
- `components/automation/AutomationFlowDiagram.tsx` - Enhanced flow visualization
- `components/automation/TriggerNode.tsx` - Purpose-specific trigger visualization
- `components/automation/TargetBadge.tsx` - Area/floor/label badges

**Priority:** Low  
**Estimated Effort:** 4-5 days  
**Dependencies:** 2.1.1, 2.2.1

---

## 3. Integration Improvements

### 3.1 Home Assistant Labs Feature Detection (Medium Priority)

**Home Assistant Feature:**
- Purpose-specific triggers and conditions are in Home Assistant Labs
- Requires enabling via Settings > System > Labs

**HomeIQ Implementation:**

#### 3.1.1 Labs Feature Detection
**Service:** `ha-ai-agent-service` or `websocket-ingestion`  
**Endpoint:** Check HA Labs configuration

**Requirements:**
- Detect if purpose-specific triggers are enabled in HA
- Provide feedback in automation generation about available trigger types
- Warn users if trying to use purpose-specific triggers when not enabled

**Implementation:**
- Query HA config to check Labs settings
- Store labs feature status in service configuration
- Use status to determine available trigger types in automation generation

**Priority:** Medium  
**Estimated Effort:** 2 days  
**Dependencies:** None

---

## 4. Implementation Priority

### Phase 1: High Priority (Immediate)
1. **2.1.1** - Purpose-Specific Triggers Schema Enhancement (3-4 days)
2. **2.1.2** - YAML Converter Enhancement (4-5 days)
3. **1.1.1** - Unassigned Devices API (1-2 days)
4. **1.1.2** - Unassigned Devices UI (1-2 days)

**Total Phase 1:** ~10-13 days

### Phase 2: Medium Priority (Next Sprint)
1. **2.1.3** - Automation Generator Updates (3-4 days)
2. **2.2.1** - Enhanced Targeting Schema (2 days)
2. **2.2.2** - Enhanced Targeting YAML Converter (3-4 days)
3. **1.2.1** - Protocol Detection (2 days)
4. **1.2.2** - Protocol Dashboard UI (3-4 days)
5. **3.1.1** - Labs Feature Detection (2 days)

**Total Phase 2:** ~15-20 days

### Phase 3: Low Priority (Future)
1. **2.1.4** - UI Support for Purpose-Specific Triggers (5-6 days)
2. **2.3.1** - Automation Flow Display Improvements (4-5 days)
3. **1.3.1** - Label Filtering API (1-2 days)
4. **1.3.2** - Label Management UI (1-2 days)

**Total Phase 3:** ~11-15 days

---

## 5. Testing Requirements

### 5.1 Device Management Testing
- Test unassigned devices endpoint with various device configurations
- Test protocol detection with multiple integrations
- Test label filtering with devices having multiple labels
- Verify protocol dashboard displays correctly

### 5.2 Automation Testing
- Test purpose-specific trigger generation for all new trigger types
- Test YAML conversion for all trigger types (bidirectional)
- Test enhanced targeting in triggers, conditions, and actions
- Test automation generator with purpose-specific triggers
- Verify automation visualization displays enhanced targeting correctly

### 5.3 Integration Testing
- Test with Home Assistant 2026.1 instance
- Test with Labs features enabled/disabled
- Test backward compatibility with HA 2025.x instances
- Verify protocol detection works with all supported protocols

---

## 6. Documentation Requirements

### 6.1 API Documentation
- Document new unassigned devices endpoint
- Document protocol detection endpoints
- Document label filtering parameters
- Document purpose-specific trigger types in automation schema

### 6.2 User Documentation
- Document unassigned devices page usage
- Document protocol dashboard features
- Document purpose-specific triggers in automation creation
- Document enhanced targeting capabilities

### 6.3 Developer Documentation
- Document schema changes for purpose-specific triggers
- Document YAML conversion patterns
- Document automation generator updates
- Document protocol detection implementation

---

## 7. Migration Considerations

### 7.1 Backward Compatibility
- **Purpose-Specific Triggers:** Maintain support for generic state triggers
- **Enhanced Targeting:** Support both entity_id and target fields during transition
- **Protocol Detection:** Handle missing protocol information gracefully
- **Labs Features:** Detect and handle Labs feature availability

### 7.2 Data Migration
- No database schema changes required (labels already supported)
- Existing automations continue to work (generic triggers still supported)
- Protocol information can be derived from integration field (no migration needed)

---

## 8. Success Criteria

### 8.1 Device Management
- ✅ Unassigned devices page displays all devices without areas
- ✅ Protocol dashboard shows all protocols with device counts
- ✅ Label filtering works for device queries
- ✅ Protocol detection accurately identifies device protocols

### 8.2 Automation
- ✅ Purpose-specific triggers are supported in schema and YAML conversion
- ✅ Automation generator creates purpose-specific triggers when appropriate
- ✅ Enhanced targeting works in triggers, conditions, and actions
- ✅ Automation visualization clearly shows enhanced targeting

### 8.3 Integration
- ✅ HomeIQ works with Home Assistant 2026.1
- ✅ Labs feature detection works correctly
- ✅ Backward compatibility maintained with HA 2025.x

---

## 9. References

- [Home Assistant 2026.1 Release Notes](https://www.home-assistant.io/blog/2026/01/07/release-20261/)
- [HomeIQ Architecture Documentation](docs/architecture/)
- [HomeIQ Automation Schema](shared/homeiq_automation/schema.py)
- [Home Assistant Labs Documentation](https://www.home-assistant.io/labs/)
- [Home Assistant Purpose-Specific Triggers](https://www.home-assistant.io/docs/automation/trigger/#purpose-specific-triggers)

---

## 10. Next Steps

1. **Review and Approve Plan** - Review this plan with team
2. **Create Epic** - Create Epic document for Home Assistant 2026.1 improvements
3. **Create Stories** - Break down into user stories for implementation
4. **Start Phase 1** - Begin high-priority items
5. **Track Progress** - Update plan with implementation status

---

**Plan Created:** January 8, 2026  
**Last Updated:** January 8, 2026  
**Status:** Draft - Awaiting Review
