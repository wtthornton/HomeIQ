# Device Recommender Service

Phase 3.3: Device recommendations and comparisons.

## Overview

This service:
- Recommends devices based on user requirements
- Compares devices in user's home
- Finds similar devices
- Provides device ratings and reviews (from Device Database)

## Configuration

Environment variables:
- `DEVICE_RECOMMENDER_PORT`: Service port (default: 8023)
- `HA_URL`: Home Assistant URL
- `HA_TOKEN`: Home Assistant access token
- `DEVICE_DATABASE_API_URL`: Device Database API URL (optional)
- `LOG_LEVEL`: Logging level (default: info)
- `RELOAD`: Enable auto-reload (default: false)

## Integration

This service is used by data-api to provide device recommendations and comparisons.

