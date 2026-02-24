# HomeIQ Cross-Group Resilience

Shared resilience utilities for services that make HTTP calls across service-group boundaries.

## Modules

| Module | Export | Purpose |
|--------|--------|---------|
| `circuit_breaker.py` | `CircuitBreaker`, `CircuitOpenError` | 3-state circuit breaker (CLOSED → OPEN → HALF_OPEN) |
| `cross_group_client.py` | `CrossGroupClient` | httpx wrapper with retry, circuit breaker, Bearer auth, OTel trace propagation |
| `health.py` | `GroupHealthCheck`, `DependencyStatus` | Structured `/health` response with dependency probes |
| `startup.py` | `wait_for_dependency` | Non-fatal startup probe for cross-group dependencies |

## Usage Pattern

```python
from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

# Module-level shared breaker (one per target group)
_core_platform_breaker = CircuitBreaker(name="core-platform")

class DataAPIClient:
    def __init__(self, base_url="http://data-api:8006", api_key=None):
        self._cross_client = CrossGroupClient(
            base_url=base_url,
            group_name="core-platform",
            timeout=30.0,
            max_retries=3,
            auth_token=api_key,
            circuit_breaker=_core_platform_breaker,
        )

    async def fetch_entities(self):
        try:
            response = await self._cross_client.call("GET", "/api/entities")
            response.raise_for_status()
            return response.json().get("entities", [])
        except CircuitOpenError:
            return []  # Graceful degradation
```

## Service Groups & Breaker Mapping

| Domain | Name | Key Services | Breaker Name |
|--------|------|-------------|-------------|
| D1 | core-platform | data-api, websocket-ingestion, admin-api | `core-platform` |
| D2 | data-collectors | weather-api, smart-meter, carbon-intensity | `data-collectors` |
| D3 | ml-engine | device-intelligence, ai-core, openvino | `ml-engine` |
| D4 | automation-core | ha-ai-agent, ai-automation-service-new, ai-query | N/A (same-domain) |
| D5 | blueprints | blueprint-index, blueprint-suggestion, automation-miner | N/A (same-domain) |
| D6 | energy-analytics | energy-correlator, energy-forecasting, proactive-agent | N/A (same-domain) |
| D7 | device-management | device-health-monitor, device-setup-assistant | N/A (same-domain) |
| D8 | pattern-analysis | ai-pattern-service, api-automation-edge | N/A (same-domain) |
| D9 | frontends | health-dashboard, ai-automation-ui | N/A (same-domain) |

**Rule**: Only cross-domain HTTP calls get circuit breakers. Same-domain calls use direct httpx.

## Rollout Status

| Service | Domain | Cross-Domain Targets | Status |
|---------|--------|---------------------|--------|
| ha-ai-agent-service | D4 | data-api (D1), device-intelligence (D3) | Done (PoC) |
| blueprint-suggestion-service | D5 | data-api (D1) | Done |
| ai-pattern-service | D8 | data-api (D1) | Done |
| ai-automation-service-new | D4 | data-api (D1) | Done |
| proactive-agent-service | D6 | data-api (D1), weather-api (D2) | Done |
| device-health-monitor | D7 | data-api (D1), device-intelligence (D3) | Done |

## Group-Level Alerting Rules

The `GroupHealthCheck.to_dict()` response includes a `group` field. Use this for differentiated alerting:

| Domain | Severity | Response Time | Rationale |
|--------|----------|--------------|-----------|
| core-platform (D1) | P1 (page) | Immediate | All services depend on data-api |
| ml-engine (D3) | P2 (alert) | 5 min | AI features degrade but basic function continues |
| automation-core (D4) | P2 (alert) | 5 min | Automation suggestions stop but HA control works |
| data-collectors (D2) | P3 (notify) | 15 min | Weather/energy data stale but not blocking |
| blueprints (D5) | P3 (notify) | 15 min | Blueprint suggestions stop but automations work |
| energy-analytics (D6) | P3 (notify) | 10 min | Energy forecasting delayed but system works |
| device-management (D7) | P3 (notify) | 10 min | Health monitoring delayed but devices work |
| pattern-analysis (D8) | P3 (notify) | 10 min | Pattern detection delayed but core works |
| frontends (D9) | P3 (notify) | 10 min | Dashboard unavailable but backend functional |

### Example Prometheus Alert

```yaml
groups:
  - name: homeiq-group-health
    rules:
      - alert: CorePlatformDown
        expr: homeiq_group_health_status{group="core-platform"} == 0
        for: 1m
        labels:
          severity: page
        annotations:
          summary: "Core platform group unhealthy"

      - alert: MLEngineDown
        expr: homeiq_group_health_status{group="ml-engine"} == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "ML engine group unhealthy"
```

## Distributed Tracing

`CrossGroupClient` automatically injects `traceparent` and `tracestate` headers when OpenTelemetry is installed. No configuration needed — the OTel import is optional (`try/except ImportError`).

Each cross-group call also sets the span attribute `homeiq.target_group` for group-level trace filtering.

## Structured Logging

All services use `setup_logging(service_name, group_name="...")` which embeds the group name in every JSON log line:

```json
{
  "timestamp": "2026-02-23T10:00:00Z",
  "level": "INFO",
  "service": "ai-pattern-service",
  "group": "automation-core",
  "message": "Fetched 150 events from Data API"
}
```

This enables log aggregation and filtering by group in Loki/Elasticsearch.
