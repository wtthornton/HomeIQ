# Device Type Quick Reference: Home Assistant 2025 Research-Based

**30 Days of Events per Home**  
**Based on 2025 Home Assistant Annual Surveys and Industry Data**

---

## Device Categories (10 Total) - Typical HA Home: 58 Devices

| Category | Avg Count | Range | % of Total | Key Devices |
|----------|-----------|-------|------------|-------------|
| **Lighting** | 22 | 15-25 | **38%** | Zigbee bulbs, switches, dimmers, strips |
| **Sensors** | 15 | 10-18 | **26%** | Motion, door/window, temp/humidity, leak |
| **Climate** | 3 | 2-5 | **5%** | Thermostat, room sensors, fans |
| **Energy/Power** | 6 | 4-10 | **10%** | Smart plugs, power monitors, EV chargers |
| **Security** | 4 | 3-8 | **7%** | Locks, cameras, alarms, doorbells |
| **Media/AV** | 7 | 5-10 | **12%** | TVs, speakers, Chromecast, game consoles |
| **Appliances** | 2 | 1-4 | **3%** | Robot vacuums, washers, dryers |
| **Presence** | 3 | 2-6 | **5%** | mmWave sensors, BLE beacons, phone tracking |
| **Networking** | 1 | 1-3 | **2%** | UniFi controller, router sensors |
| **Misc/Custom** | 3 | 2-6 | **5%** | ESPHome, MQTT, custom integrations |
| **TOTAL** | **58** | **45-70** | **100%** | |

---

## Protocol Distribution (2025)

| Protocol | % of Devices | Typical Devices |
|----------|--------------|-----------------|
| **Zigbee** | 55-65% | Sensors, lighting, switches (Zigbee2MQTT) |
| **WiFi** | 20-30% | Smart plugs, cameras, media players |
| **Z-Wave** | 5-12% | Legacy devices, locks |
| **Matter** | 5-18% (growing) | New lighting, bridges |
| **BLE** | 3-5% | Presence, beacons |

---

## Device Distribution (400 Homes)

| Category | Avg/Home | Total (400h) | % | Events (30d, 400h) |
|----------|----------|--------------|---|-------------------|
| Lighting | 22 | ~8,800 | 38% | ~5.5M |
| Sensors | 15 | ~6,000 | 26% | ~13.5M |
| Climate | 3 | ~1,200 | 5% | ~650K |
| Energy/Power | 6 | ~2,400 | 10% | ~3.7M |
| Security | 4 | ~1,600 | 7% | ~4.2M |
| Media/AV | 7 | ~2,800 | 12% | ~4.6M |
| Appliances | 2 | ~800 | 3% | ~390K |
| Presence | 3 | ~1,200 | 5% | ~1.1M |
| Networking | 1 | ~400 | 2% | ~80K |
| Misc/Custom | 3 | ~1,200 | 5% | ~600K |
| **TOTAL** | **58** | **~23,200** | **100%** | **~34.3M** |

---

## Top Event Generators

| Device Type | Events/Day | Total Events (400h, 30d) |
|-------------|------------|--------------------------|
| Motion sensors | 73 | ~13.1M |
| Media players | 55 | ~4.6M |
| Power sensors | 52 | ~3.7M |
| Lights | 21 | ~5.5M |
| Door/window | 30 | ~2.7M |

---

## Key Insights

### Largest Categories
1. **Lighting** - 38% of devices (most common)
2. **Sensors** - 26% of devices (automation foundation)
3. **Media/AV** - 12% of devices (entertainment)

### Highest Event Volume
1. **Motion sensors** - ~13.1M events (most events)
2. **Lights** - ~5.5M events
3. **Media players** - ~4.6M events

### Growing Categories (2025)
- **Energy/Power** - HA Energy Dashboard drives adoption
- **Presence** - mmWave sensors enable room-level automation
- **Matter** - Protocol adoption growing (5-18%)

---

**See:** `DEVICE_TYPE_BREAKDOWN.md` for detailed breakdown
