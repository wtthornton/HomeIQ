# Device Setup Assistant Service

Phase 2.3: Provide setup guides and detect setup issues for new devices.

## Overview

This service:
- Generates step-by-step setup instructions for new devices
- Detects common setup issues:
  - Device not responding (no events in 24h)
  - Missing expected entities
  - Incorrect area assignment
  - Integration configuration errors
- Provides troubleshooting tips
- Links to Device Database setup instructions (when available)

## Configuration

Environment variables:
- `DEVICE_SETUP_ASSISTANT_PORT`: Service port (default: 8021)
- `HA_URL`: Home Assistant URL
- `HA_TOKEN`: Home Assistant access token
- `LOG_LEVEL`: Logging level (default: info)
- `RELOAD`: Enable auto-reload (default: false)

## Integration

This service is used by data-api to provide setup assistance when new devices are detected.

