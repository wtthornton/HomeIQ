# Feature Validation Report
Generated: Sat Nov 29 18:16:53 PST 2025

## Phase 2: Feature Validation

This report validates all features are implemented and working correctly.

[0;34m[INFO][0m Starting Phase 2: Feature Validation...
[0;34m[INFO][0m 2.1 Validating Event Ingestion (websocket-ingestion)...

### 2.1 Event Ingestion

[0;32m[✓ PASS][0m WebSocket service health - HTTP 200
**WebSocket Health Response:**
```json
{"status": "healthy", "service": "websocket-ingestion", "uptime": "5:23:05.340772", "timestamp": "2025-11-29T18:16:53.517213", "connection": {"is_running": true, "connection_attempts": 1, "successful_connections": 1, "failed_connections": 0}, "subscription": {"is_subscribed": true, "active_subscriptions": 0, "total_events_received": 1022468, "session_events_received": 5326, "historical_events_received": 1017142, "events_by_type": {"state_changed": 5326}, "last_event_time": "2025-11-29T18:16:14.049644", "event_rate_per_minute": 16.52}}
```

[1;33m[⚠ WARN][0m Home Assistant connection status unclear
⚠️ **HA Connection:** Status unclear
[0;34m[INFO][0m Checking for recent events...
[0;32m[✓ PASS][0m Recent events query - HTTP 200
[1;33m[⚠ WARN][0m No recent events found
⚠️ **Recent Events:** None found
[0;34m[INFO][0m 2.2 Validating Data API Endpoints...

### 2.2 Data API Endpoints

| Endpoint | Method | Status |
|----------|--------|--------|
[0;32m[✓ PASS][0m GET /api/v1/events - HTTP 200
| GET /api/v1/events | GET | ✓ |
[0;32m[✓ PASS][0m GET /api/v1/events/stats - HTTP 200
| GET /api/v1/events/stats | GET | ✓ |
[0;31m[✗ FAIL][0m GET /api/v1/devices - Connection failed
| GET /api/v1/devices | GET | ✗ |
[0;31m[✗ FAIL][0m GET /api/v1/entities - Connection failed
| GET /api/v1/entities | GET | ✗ |
[0;31m[✗ FAIL][0m GET /api/v1/analytics/realtime - Connection failed
| GET /api/v1/analytics/realtime | GET | ✗ |
[0;31m[✗ FAIL][0m GET /api/v1/analytics/entity-activity - Connection failed
| GET /api/v1/analytics/entity-activity | GET | ✗ |
[0;34m[INFO][0m 2.3 Validating Device Intelligence Features...

### 2.3 Device Intelligence Features

[0;31m[✗ FAIL][0m Device Intelligence Service health - HTTP 307
✗ Device Intelligence Service: Unhealthy
[0;32m[✓ PASS][0m Device Health Monitor health - HTTP 200
✅ Device Health Monitor: Healthy
[0;32m[✓ PASS][0m Device Context Classifier health - HTTP 200
✅ Device Context Classifier: Healthy
[0;34m[INFO][0m 2.4 Validating AI Automation Features...

### 2.4 AI Automation Features

[0;32m[✓ PASS][0m AI Automation Service health - HTTP 200
✅ AI Automation Service: Healthy
[0;32m[✓ PASS][0m AI Core Service health - HTTP 200
✅ AI Core Service: Healthy
[0;34m[INFO][0m 2.5 Validating Frontend Dashboards...

### 2.5 Frontend Dashboards

[0;32m[✓ PASS][0m Health Dashboard - HTTP 200
✅ Health Dashboard: Accessible
[0;32m[✓ PASS][0m AI Automation UI - HTTP 200
✅ AI Automation UI: Accessible
[0;34m[INFO][0m 2.6 Validating External Service Integrations...

### 2.6 External Service Integrations

[0;31m[✗ FAIL][0m Weather API - Connection failed
⚠️ Weather API: Not healthy (may be optional)
[0;31m[✗ FAIL][0m Carbon Intensity Service - Connection failed
⚠️ Carbon Intensity Service: Not healthy (may be optional)
[0;31m[✗ FAIL][0m Electricity Pricing Service - Connection failed
⚠️ Electricity Pricing Service: Not healthy (may be optional)
[0;31m[✗ FAIL][0m Air Quality Service - Connection failed
⚠️ Air Quality Service: Not healthy (may be optional)
[0;32m[✓ PASS][0m Smart Meter Service - HTTP 200
✅ Smart Meter Service: Healthy

## Summary

- **Features Tested:** 20
- **Features Passed:** 11
- **Success Rate:** 55.0%

**Status:** ⚠️ Some features need attention
[1;33m[⚠ WARN][0m Phase 2 validation complete - Some issues found
