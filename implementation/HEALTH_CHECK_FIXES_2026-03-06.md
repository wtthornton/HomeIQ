# Health Check Fixes — March 6, 2026

## Overview

Fixed 4 degraded service health checks affecting Core Platform, Data Collectors, Energy Analytics, and Device Management groups.

**Before:** 4 Degraded groups, 26/27 services operational  
**After:** 7 Healthy groups, 1 Degraded group (expected), 27/27 services operational

## Issues Fixed

### 1. data-api: Database Health Check (Core Platform)

**Symptom:** `database` check always returned unhealthy despite PostgreSQL working correctly.

**Root Cause:** Status comparison mismatch in `_check_db_healthy()`:
- Code checked for `result.get("status") == "connected"`
- DatabaseManager actually returns `"healthy"` when working

**Fix:** Changed comparison from `"connected"` to `"healthy"` in `domains/core-platform/data-api/src/main.py`

```python
# Before
return result.get("status") == "connected"

# After
return result.get("status") == "healthy"
```

### 2. admin-api: Health Dashboard Connection (Core Platform)

**Symptom:** admin-api reported `Cannot connect to host health-dashboard:80` when checking health-dashboard status.

**Root Cause:** Port mismatch in default URL:
- admin-api defaulted to `http://health-dashboard:80`
- health-dashboard container actually listens on port 8080

**Fix:** Updated port in `domains/core-platform/admin-api/src/health_endpoints.py`

```python
# Before
"health-dashboard": os.getenv("HEALTH_DASHBOARD_URL", "http://health-dashboard:80"),

# After
"health-dashboard": os.getenv("HEALTH_DASHBOARD_URL", "http://health-dashboard:8080"),
```

### 3. device-health-monitor: HA Config (Device Management)

**Symptom:** `ha-config` check unhealthy because `HA_TOKEN` was empty inside the container.

**Root Cause:** Docker Compose variable substitution syntax issue:
- `${HOME_ASSISTANT_TOKEN:-}` doesn't read from .env file during compose parsing
- The .env file has `HA_TOKEN` set, but compose was looking for `HOME_ASSISTANT_TOKEN`

**Fix:** Updated `domains/device-management/compose.yml` to use proper fallback chain:

```yaml
# Before
- HA_TOKEN=${HOME_ASSISTANT_TOKEN:-}

# After
- HA_TOKEN=${HA_TOKEN:-${HOME_ASSISTANT_TOKEN:-}}
```

Applied to all services in the compose file (device-health-monitor, device-context-classifier, device-setup-assistant, device-intelligence-service).

### 4. calendar-service: Calendars Check (Data Collectors)

**Symptom:** `calendars` check unhealthy because configured calendar entity doesn't exist in Home Assistant.

**Root Cause:** 
- Default `CALENDAR_ENTITIES=calendar.primary` doesn't exist in HA
- Code didn't filter out empty calendar entity strings

**Fixes:**

1. Updated `domains/data-collectors/calendar-service/src/main.py` to filter empty entities:

```python
# Before
self.calendar_entities = [cal.strip() for cal in self.calendar_entities]

# After
self.calendar_entities = [cal.strip() for cal in self.calendar_entities if cal.strip()]
```

2. Changed compose default in `domains/data-collectors/compose.yml`:

```yaml
# Before
- CALENDAR_ENTITIES=${CALENDAR_ENTITIES:-calendar.primary}

# After
- CALENDAR_ENTITIES=${CALENDAR_ENTITIES:-}
```

## Remaining Degraded Service

**energy-forecasting** (Energy Analytics) reports `degraded` with `model_loaded: false`. This is **expected behavior** — the ML forecasting model hasn't been trained yet. The service is operational but cannot perform forecasting without a trained model.

## Files Changed

| File | Change |
|------|--------|
| `domains/core-platform/data-api/src/main.py` | Fixed database status comparison |
| `domains/core-platform/admin-api/src/health_endpoints.py` | Fixed health-dashboard port |
| `domains/device-management/compose.yml` | Fixed HA_TOKEN variable syntax |
| `domains/data-collectors/calendar-service/src/main.py` | Filter empty calendar entities |
| `domains/data-collectors/compose.yml` | Changed calendar default to empty |
| `.env` | Updated CALENDAR_ENTITIES documentation |

## Verification

All services now pass their health checks:

```
Core Platform:     5/5 healthy ✓
Data Collectors:   7/7 healthy ✓
ML Engine:         3/3 healthy ✓
Automation Intel:  1/1 healthy ✓
Energy Analytics:  2/3 healthy (1 degraded - expected, no model)
Blueprints:        3/3 healthy ✓
Pattern Analysis:  2/2 healthy ✓
Device Management: 3/3 healthy ✓
```
