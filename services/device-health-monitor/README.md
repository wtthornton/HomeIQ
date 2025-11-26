# Device Health Monitor Service

Phase 1.2: Monitor device health and provide maintenance insights.

## Overview

This service analyzes device health by:
- Monitoring device response times from HA State API
- Checking battery levels from entity attributes
- Tracking last_seen timestamps
- Detecting power consumption anomalies
- Generating health reports with severity levels
- Providing maintenance recommendations

## Configuration

Environment variables:
- `DEVICE_HEALTH_MONITOR_PORT`: Service port (default: 8019)
- `HA_URL`: Home Assistant URL
- `HA_TOKEN`: Home Assistant access token
- `LOG_LEVEL`: Logging level (default: info)
- `RELOAD`: Enable auto-reload (default: false)

## API Endpoints

- `GET /health` - Service health check
- `GET /` - Service info

Note: Health endpoints are exposed via data-api service at:
- `GET /api/devices/{device_id}/health`
- `GET /api/devices/health-summary`
- `GET /api/devices/maintenance-alerts`

## Integration

This service is called by data-api service to provide device health information.

