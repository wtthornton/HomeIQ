# energy-analytics

Energy intelligence — proactive energy recommendations built on Data API energy history.

## Services

| Service | Port | Role |
|---------|------|------|
| proactive-agent-service | 8031 | Proactive recommendations and suggestions |

## Depends On

core-platform (data-api, InfluxDB)

## Depended On By

automation-core (energy context feeds automation suggestions)

## Compose

```bash
docker compose -f domains/energy-analytics/compose.yml up -d
```
