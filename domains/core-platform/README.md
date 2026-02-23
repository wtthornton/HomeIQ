# core-platform

The data backbone. If this is down, everything is down.

## Services

| Service | Port | Role |
|---------|------|------|
| websocket-ingestion | 8001 | Primary HA event capture, InfluxDB writer |
| data-api | 8006 | Central query hub — every service reads through this |
| admin-api | 8003/8004 | System control plane, health checks, config |
| health-dashboard | 3000 | Primary user UI (React/Vite/TypeScript) |
| data-retention | 8080 | Data lifecycle — cleanup, compression, rotation |
| ha-simulator | — | HA websocket simulator for testing/development |
| influxdb | 8086 | Time-series database (external image) |

## Depends On

Nothing — root of the dependency tree.

## Depended On By

All other domains.

## Compose

```bash
docker compose -f domains/core-platform/compose.yml up -d
```
