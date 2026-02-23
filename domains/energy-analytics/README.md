# energy-analytics

Energy intelligence — device-power causality analysis, consumption forecasting, and proactive energy recommendations.

## Services

| Service | Port | Role |
|---------|------|------|
| energy-correlator | 8017 | Device-power causality analysis |
| energy-forecasting | 8042 | 7-day energy consumption predictions |
| proactive-agent-service | 8031 | Proactive recommendations and suggestions |

## Depends On

core-platform (data-api, InfluxDB), ml-engine (for ML-powered forecasting)

## Depended On By

automation-core (energy context feeds automation suggestions)

## Compose

```bash
docker compose -f domains/energy-analytics/compose.yml up -d
```
