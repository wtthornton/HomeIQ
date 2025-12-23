# Device Distribution Comparison: Current vs Research-Based

**Comparison of current implementation vs Home Assistant 2025 research data**

---

## Current Implementation vs Research Target

### Current Distribution (Template-Based)

| Category | Current % | Current Base | Notes |
|----------|-----------|--------------|-------|
| Lighting | 30% | 8 devices | Close but needs increase |
| Security | 18% | 5 devices | Too high |
| Appliances | 15% | 4 devices | Too high, includes media |
| Monitoring | 11% | 3 devices | Mixed with energy |
| Climate | 11% | 3 devices | Slightly high |
| **TOTAL** | **85%** | **23 devices** | Missing categories |

**Missing Categories:**
- Media/AV (currently in appliances)
- Energy/Power (currently in monitoring)
- Presence (not tracked)
- Networking (not tracked)
- Sensors (scattered across categories)

---

### Research-Based Target (Home Assistant 2025)

| Category | Target % | Target Count | Research Range |
|----------|----------|--------------|----------------|
| Lighting | 38% | 22 devices | 15-25 |
| Sensors | 26% | 15 devices | 10-18 |
| Media/AV | 12% | 7 devices | 5-10 |
| Energy/Power | 10% | 6 devices | 4-10 |
| Security | 7% | 4 devices | 3-8 |
| Presence | 5% | 3 devices | 2-6 |
| Climate | 5% | 3 devices | 2-5 |
| Misc/Custom | 5% | 3 devices | 2-6 |
| Appliances | 3% | 2 devices | 1-4 |
| Networking | 2% | 1 device | 1-3 |
| **TOTAL** | **100%** | **58 devices** | 45-70 |

---

## Gap Analysis

### Categories to Increase

| Category | Current | Target | Gap | Action |
|----------|---------|--------|-----|--------|
| **Lighting** | 30% (8) | 38% (22) | +8% (+14 devices) | **Increase significantly** |
| **Sensors** | 20%* (mixed) | 26% (15) | +6% (+15 devices) | **Extract and expand** |
| **Media/AV** | 0% (in appliances) | 12% (7) | +12% (+7 devices) | **Create new category** |
| **Energy/Power** | 11%* (in monitoring) | 10% (6) | -1% (+3 devices) | **Extract and adjust** |
| **Presence** | 0% | 5% (3) | +5% (+3 devices) | **Create new category** |

### Categories to Decrease

| Category | Current | Target | Gap | Action |
|----------|---------|--------|-----|--------|
| **Security** | 18% (5) | 7% (4) | -11% (-1 device) | **Reduce slightly** |
| **Appliances** | 15% (4) | 3% (2) | -12% (-2 devices) | **Reduce significantly** |
| **Climate** | 11% (3) | 5% (3) | -6% (0 devices) | **Keep same count** |

### Categories to Add

| Category | Current | Target | Action |
|----------|---------|--------|--------|
| **Networking** | 0% | 2% (1) | **Add new category** |
| **Misc/Custom** | 0% | 5% (3) | **Add new category** |

---

## Device Count Comparison

### Current Implementation

```
Total: ~23 devices per home (base)
- Lighting: 8 devices (30%)
- Security: 5 devices (18%)
- Appliances: 4 devices (15%)
- Monitoring: 3 devices (11%)
- Climate: 3 devices (11%)
- Other: Mixed across categories
```

### Research Target

```
Total: ~58 devices per home (average)
- Lighting: 22 devices (38%)
- Sensors: 15 devices (26%)
- Media/AV: 7 devices (12%)
- Energy/Power: 6 devices (10%)
- Security: 4 devices (7%)
- Presence: 3 devices (5%)
- Climate: 3 devices (5%)
- Misc/Custom: 3 devices (5%)
- Appliances: 2 devices (3%)
- Networking: 1 device (2%)
```

**Difference: +35 devices per home (152% increase)**

---

## Recommendations for Code Updates

### Priority 1: Major Structural Changes

1. **Create new categories:**
   - `media` - Media/AV devices (TVs, speakers, Chromecast)
   - `energy` - Energy/Power monitoring (smart plugs, power monitors)
   - `presence` - Presence sensors (mmWave, BLE beacons)
   - `networking` - Networking devices (UniFi controller)
   - `sensors` - Dedicated sensor category (extract from mixed)

2. **Separate mixed categories:**
   - Extract sensors from security/climate/monitoring
   - Extract energy from monitoring
   - Extract media from appliances

### Priority 2: Adjust Base Counts

**Current base counts:**
```python
base_counts = {
    'security': 5,      # → 4 (reduce)
    'climate': 3,       # → 3 (keep)
    'lighting': 8,      # → 22 (increase)
    'appliances': 4,    # → 2 (reduce)
    'monitoring': 3     # → Split into energy(6) + monitoring(3)
}
```

**Target base counts:**
```python
base_counts = {
    'lighting': 22,     # 38% - Most common
    'sensors': 15,      # 26% - Automation foundation
    'media': 7,         # 12% - Entertainment
    'energy': 6,        # 10% - Energy dashboard
    'security': 4,      # 7% - Security systems
    'presence': 3,      # 5% - mmWave/BLE
    'climate': 3,       # 5% - HVAC
    'misc': 3,          # 5% - Custom/ESPHome
    'appliances': 2,    # 3% - Robot vacuums, etc.
    'networking': 1     # 2% - UniFi/router
}
```

### Priority 3: Update Device Templates

**Add new device types:**

**Media/AV:**
- `media_player` (TV, Chromecast, Apple TV)
- `media_player` (Speaker - Sonos, Echo)
- Media control entities

**Energy/Power:**
- `sensor` (power) - Already exists
- `sensor` (energy) - Already exists
- `switch` (smart plug) - Extract from appliances
- EV charger integrations

**Presence:**
- `binary_sensor` (presence) - mmWave
- `device_tracker` (phone tracking)
- BLE beacon sensors
- Person entities

**Networking:**
- UniFi controller integration
- Router sensors
- WiFi presence tracking

**Sensors (extract):**
- Motion sensors (from security)
- Door/window sensors (from security)
- Temperature/humidity (from climate)
- Leak detectors
- Vibration sensors

---

## Migration Path

### Phase 1: Add New Categories (Non-Breaking)
- Add new categories without removing old ones
- Start generating devices in new categories
- Maintain backward compatibility

### Phase 2: Adjust Proportions
- Gradually adjust base counts
- Move devices between categories
- Update templates

### Phase 3: Cleanup
- Remove deprecated category mappings
- Update documentation
- Validate against research targets

---

## Expected Impact (400 Homes)

### Current Implementation
- **Total Devices:** ~9,200 (23 × 400)
- **Categories:** 5
- **Missing:** Media, Presence, Networking, dedicated Sensors

### Research-Based Target
- **Total Devices:** ~23,200 (58 × 400)
- **Categories:** 10
- **Complete:** All research categories included

### Difference
- **+14,000 devices** total (+152%)
- **+5 categories**
- **+~22 million events** (30 days)

---

## Validation Criteria

### Target Metrics
- ✅ Lighting: 38% ± 3% (22 ± 2 devices)
- ✅ Sensors: 26% ± 3% (15 ± 2 devices)
- ✅ Media: 12% ± 2% (7 ± 1 devices)
- ✅ Energy: 10% ± 2% (6 ± 1 devices)
- ✅ Total: 58 devices ± 5 (45-70 range)

### Protocol Distribution
- ✅ Zigbee: 55-65% of devices
- ✅ WiFi: 20-30% of devices
- ✅ Z-Wave/Matter/BLE: 15-25% combined

---

**Last Updated:** December 2, 2025  
**Status:** Research-based targets defined - Code updates recommended

