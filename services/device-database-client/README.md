# Device Database Client Service

Phase 3.1: Client for external Device Database API.

## Overview

This service:
- Queries external Device Database API (when available)
- Caches device information locally
- Falls back to local intelligence if Device Database unavailable
- Syncs device capabilities periodically
- Updates Device model with enriched data

## Configuration

Environment variables:
- `DEVICE_DATABASE_CLIENT_PORT`: Service port (default: 8022)
- `DEVICE_DATABASE_API_URL`: Device Database API URL (optional)
- `DEVICE_DATABASE_API_KEY`: Device Database API key (optional)
- `LOG_LEVEL`: Logging level (default: info)
- `RELOAD`: Enable auto-reload (default: false)

## Data Sources Priority

1. Local cache (if fresh)
2. Device Database API (if available)
3. Local device intelligence (HA API inference)

## Integration

This service is used by data-api to enrich device metadata with Device Database information.

