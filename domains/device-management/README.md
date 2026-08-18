# device-management

Device lifecycle — health monitoring, onboarding, and classification. Independent of automation features.

## Services

| Service | Port | Role |
|---------|------|------|
| device-health-monitor | 8019 | Device health tracking, battery monitoring |
| device-context-classifier | 8032 | Room/location inference |
| device-setup-assistant | 8021 | Guided device onboarding |
| device-database-client | 8022 | Device data access layer + caching |
| device-recommender | 8023 | Device upgrade suggestions |
| ha-setup-service | 8024 | HA health checks, integration monitoring |

## Depends On

core-platform (data-api), ml-engine (device-intelligence-service for classification)

## Depended On By

automation-core (automation uses device context)

## Compose

```bash
docker compose -f domains/device-management/compose.yml up -d
```
