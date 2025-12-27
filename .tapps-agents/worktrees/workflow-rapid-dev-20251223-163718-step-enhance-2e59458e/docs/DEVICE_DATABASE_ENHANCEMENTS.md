# Device Database Enhancements

**Last Updated:** January 20, 2025  
**Status:** ✅ Implemented - All phases complete  
**Epic:** Device Database Integration (Inspired by Home Assistant 2025 H1 Roadmap)

---

## Overview

This document describes the Device Database enhancements implemented in HomeIQ, inspired by the Home Assistant 2025 H1 roadmap's Device Database initiative. These enhancements add comprehensive device intelligence, health monitoring, context understanding, and automation capabilities.

**Key Principle:** All device data access is through Home Assistant API only (no direct protocol access like Zigbee2MQTT or Z-Wave).

---

## Architecture

### Service Overview

Five new services were added to support Device Database functionality:

1. **Device Health Monitor** (Port 8019) - Health analysis and maintenance insights
2. **Device Context Classifier** (Port 8032) - Device type classification from entity patterns
3. **Device Setup Assistant** (Port 8021) - Setup guides and issue detection
4. **Device Database Client** (Port 8022) - External Device Database integration
5. **Device Recommender** (Port 8023) - Device recommendations and comparisons

### Data Flow

```
Home Assistant API
    ↓
Device Discovery (websocket-ingestion)
    ↓
Device Classification (device-context-classifier)
    ↓
Device Enrichment (device-database-client)
    ↓
Device Health Monitoring (device-health-monitor)
    ↓
Automation Suggestions (ai-automation-service with device templates)
```

---

## Phase 1: Enhanced Device Metadata & Health

### 1.1 Extended Device Model

**File:** `services/data-api/src/models/device.py`  
**Migration:** `006_add_device_intelligence_fields.py`

**New Fields:**
- `device_type` - Device classification (fridge, light, sensor, thermostat, etc.)
- `device_category` - Category (appliance, lighting, security, climate)
- `power_consumption_idle_w` - Standby power consumption
- `power_consumption_active_w` - Active power consumption
- `power_consumption_max_w` - Peak power consumption
- `infrared_codes_json` - IR codes (if applicable)
- `setup_instructions_url` - Link to setup guide
- `troubleshooting_notes` - Common issues and solutions
- `device_features_json` - Structured capabilities (JSON)
- `community_rating` - Rating from Device Database
- `last_capability_sync` - When capabilities were last updated

### 1.2 Device Health Monitor

**Service:** `services/device-health-monitor/`  
**Port:** 8019

**Features:**
- Analyze device response times from HA State API
- Check battery levels from entity attributes
- Monitor last_seen timestamps
- Detect power consumption anomalies
- Generate health reports with severity levels
- Provide maintenance recommendations

**API Endpoints (via data-api):**
- `GET /api/devices/{device_id}/health` - Device health report
- `GET /api/devices/health-summary` - Overall health summary
- `GET /api/devices/maintenance-alerts` - Devices needing attention

### 1.3 Power Consumption Intelligence

**Enhancement:** `services/energy-correlator/`

**New Features:**
- Compare actual power usage vs. device specifications
- Detect power anomalies (devices consuming more than expected)
- Calculate device efficiency scores
- Generate power optimization recommendations

**New Endpoints (via data-api):**
- `GET /api/devices/{device_id}/power-analysis` - Power consumption analysis
- `GET /api/devices/{device_id}/efficiency` - Efficiency report
- `GET /api/devices/power-anomalies` - Devices with power issues

---

## Phase 2: Device Context & Automation

### 2.1 Device Context Classifier

**Service:** `services/device-context-classifier/`  
**Port:** 8020

**Features:**
- Analyze entities to infer device types (fridge, car, 3D printer, etc.)
- Group related entities into logical devices
- Extract device context metadata
- Store classifications in Device model

**Device Patterns:**
- Fridge: temperature sensors + door sensor + light
- Car: location + battery + charging status
- 3D Printer: temperature + progress + status
- Thermostat: temperature + humidity + mode
- Light: brightness + state + color
- Sensor: state + battery + measurements
- (Extensible pattern library)

**API Endpoint:**
- `POST /api/devices/{device_id}/classify` - Classify device and update model

### 2.2 Device-Specific Automation Templates

**Enhancement:** `services/ai-automation-service/src/automation_templates/`

**Features:**
- Library of device-specific automation templates
- Template rendering based on device type
- Check for existing similar automations
- Generate suggestions with device context

**Templates Include:**
- Fridge: "Door left open alert", "Water leakage detection"
- Car: "Charging complete notification", "Low battery alert"
- 3D Printer: "Print complete notification", "Temperature monitoring"
- Thermostat: "Energy-saving schedules", "Comfort optimization"

**Integration:**
- Automatically included in daily suggestion generation
- Prioritized for new devices
- Filtered by device type

### 2.3 Device Setup Assistant

**Service:** `services/device-setup-assistant/`  
**Port:** 8021

**Features:**
- Generate step-by-step setup instructions for new devices
- Detect common setup issues:
  - Device not responding (no events in 24h)
  - Missing expected entities
  - Incorrect area assignment
  - Integration configuration errors
- Provide troubleshooting tips
- Link to Device Database setup instructions (when available)

**API Endpoints (via data-api):**
- `GET /api/devices/{device_id}/setup-guide` - Setup instructions
- `GET /api/devices/{device_id}/setup-issues` - Detected problems
- `POST /api/devices/{device_id}/setup-complete` - Mark setup complete

---

## Phase 3: Device Database Integration & Advanced Features

### 3.1 Device Database Client

**Service:** `services/device-database-client/`  
**Port:** 8022

**Features:**
- Query external Device Database API (when available)
- Cache device information locally
- Fallback to local intelligence if Device Database unavailable
- Sync device capabilities periodically
- Update Device model with enriched data

**Data Sources Priority:**
1. Local cache (if fresh)
2. Device Database API (if available)
3. Local device intelligence (HA API inference)

**Configuration:**
- `DEVICE_DATABASE_API_URL` - Device Database API URL (optional)
- `DEVICE_DATABASE_API_KEY` - API key (optional)
- Cache TTL: 24 hours (configurable)

### 3.2 Universal Capability Discovery (HA API Only)

**Enhancement:** `services/device-intelligence-service/src/capability_discovery/`

**Features:**
- Infer capabilities from HA Entity Registry API
- Analyze entity attributes from HA State API
- Use device_class and state_class metadata
- Cross-reference with Device Database (when available)

**Capability Inference:**
- Entity domains → device capabilities (light → lighting control)
- Entity attributes → features (brightness → dimming, rgb_color → color control)
- Device class → functionality (battery → battery-powered)
- State class → measurement types (measurement → sensor, total → counter)

**API Endpoint:**
- `POST /api/devices/{device_id}/discover-capabilities` - Discover and update capabilities

### 3.3 Device Comparison & Recommendations

**Service:** `services/device-recommender/`  
**Port:** 8023

**Features:**
- Recommend devices based on user requirements
- Compare devices in user's home
- Find similar devices
- Provide device ratings and reviews (from Device Database)

**API Endpoints (via data-api):**
- `GET /api/devices/recommendations?device_type={type}` - Device recommendations
- `GET /api/devices/compare?device_ids={ids}` - Compare devices
- `GET /api/devices/similar/{device_id}` - Find similar devices

---

## API Reference

All new endpoints are exposed through the Data API service (Port 8006).

### Device Health Endpoints

```http
GET /api/devices/{device_id}/health
GET /api/devices/health-summary
GET /api/devices/maintenance-alerts
```

### Device Classification

```http
POST /api/devices/{device_id}/classify
```

### Device Setup

```http
GET /api/devices/{device_id}/setup-guide
GET /api/devices/{device_id}/setup-issues
POST /api/devices/{device_id}/setup-complete
```

### Power Analysis

```http
GET /api/devices/{device_id}/power-analysis
GET /api/devices/{device_id}/efficiency
GET /api/devices/power-anomalies
```

### Capability Discovery

```http
POST /api/devices/{device_id}/discover-capabilities
```

### Device Recommendations

```http
GET /api/devices/recommendations?device_type={type}
GET /api/devices/compare?device_ids={id1},{id2}
GET /api/devices/similar/{device_id}
```

---

## Configuration

### Environment Variables

**Device Health Monitor:**
```bash
DEVICE_HEALTH_MONITOR_PORT=8019
HA_URL=http://192.168.1.86:8123
HA_TOKEN=your-token
```

**Device Database Client:**
```bash
DEVICE_DATABASE_CLIENT_PORT=8022
DEVICE_DATABASE_API_URL=https://api.devicedatabase.org  # Optional
DEVICE_DATABASE_API_KEY=your-key  # Optional
DEVICE_CACHE_DIR=data/device_cache
```

**All Services:**
```bash
LOG_LEVEL=info
RELOAD=false
```

---

## Database Schema Changes

### Migration 006: Device Intelligence Fields

**File:** `services/data-api/alembic/versions/006_add_device_intelligence_fields.py`

**New Columns:**
- `device_type` (String, indexed)
- `device_category` (String, indexed)
- `power_consumption_idle_w` (Float)
- `power_consumption_active_w` (Float)
- `power_consumption_max_w` (Float)
- `infrared_codes_json` (Text)
- `setup_instructions_url` (String)
- `troubleshooting_notes` (Text)
- `device_features_json` (Text)
- `community_rating` (Float)
- `last_capability_sync` (DateTime)

**Indexes:**
- `idx_device_type` on `device_type`
- `idx_device_category` on `device_category`

---

## Integration with Existing Services

### Data API Integration

All new functionality is integrated into the Data API service:
- Health endpoints call `device-health-monitor` service logic
- Classification uses `device-context-classifier` patterns
- Setup assistance uses `device-setup-assistant` logic
- Device Database enrichment happens during device upsert
- Capability discovery updates `device_features_json` field

### AI Automation Service Integration

Device-specific templates are automatically included in suggestion generation:
- Templates are checked for each device type
- Suggestions are generated with device context
- Duplicate checking prevents redundant automations

---

## Best Practices

### HA API Only

- ✅ Use Home Assistant REST API for all device data
- ✅ Use Entity Registry API for entity information
- ✅ Use State API for current states and attributes
- ✅ Use History API for historical patterns
- ❌ Do NOT access Zigbee2MQTT directly
- ❌ Do NOT access Z-Wave directly
- ❌ Do NOT use protocol-specific APIs

### Epic 31 Compliance

- ✅ All services are standalone
- ✅ Direct InfluxDB writes (no intermediate services)
- ✅ SQLite for metadata (fast queries)
- ✅ Backward compatible with existing functionality

### Performance

- Device classification: <100ms per device
- Health analysis: <500ms per device
- Capability discovery: <1s per device
- All endpoints cached where appropriate

---

## Future Enhancements

### Planned Features

1. **Device Database API Integration** - When official API is available
2. **Advanced ML Models** - Predictive device failure detection
3. **Community Ratings** - User-contributed device ratings
4. **Device Compatibility Matrix** - Check device compatibility before purchase
5. **Automated Device Optimization** - AI-powered device configuration

### Roadmap

- Q1 2025: Device Database API integration
- Q2 2025: Advanced ML models for predictions
- Q3 2025: Community features and ratings
- Q4 2025: Automated optimization

---

## References

- [Home Assistant 2025 H1 Roadmap](https://www.home-assistant.io/blog/2025/05/09/roadmap-2025h1/)
- [Device Database Project](https://github.com/home-assistant/device-database)
- [Epic 31 Architecture Pattern](.cursor/rules/epic-31-architecture.mdc)
- [Device Data Field Review](implementation/DEVICE_DATA_FIELD_REVIEW.md)

---

## Support

For issues or questions:
- Check service logs: `docker compose logs {service-name}`
- Review API documentation: `http://localhost:8006/docs`
- See troubleshooting guide: `docs/TROUBLESHOOTING_GUIDE.md`

