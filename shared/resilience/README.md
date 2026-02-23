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
from shared.resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

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

| Group | Name | Key Services | Breaker Name |
|-------|------|-------------|-------------|
| G1 | core-platform | data-api, websocket-ingestion, admin-api | `core-platform` |
| G2 | data-collectors | weather-api, smart-meter, carbon-intensity | `data-collectors` |
| G3 | ml-engine | device-intelligence, ai-core, openvino | `ml-engine` |
| G4 | automation-intelligence | ha-ai-agent, ai-automation, ai-pattern, blueprint-suggestion, proactive-agent | N/A (same-group) |
| G5 | device-management | device-health-monitor, device-setup-assistant | N/A (same-group) |
| G6 | frontends | health-dashboard | N/A (same-group) |

**Rule**: Only cross-group HTTP calls get circuit breakers. Same-group calls use direct httpx.

## Rollout Status

| Service | Group | Cross-Group Targets | Status |
|---------|-------|-------------------|--------|
| ha-ai-agent-service | G4 | data-api (G1), device-intelligence (G3) | Done (PoC) |
| blueprint-suggestion-service | G4 | data-api (G1) | Done |
| ai-pattern-service | G4 | data-api (G1) | Done |
| ai-automation-service-new | G4 | data-api (G1) | Done |
| proactive-agent-service | G4 | data-api (G1), weather-api (G2) | Done |
| device-health-monitor | G5 | data-api (G1), device-intelligence (G3) | Done |

## Group-Level Alerting Rules

The `GroupHealthCheck.to_dict()` response includes a `group` field. Use this for differentiated alerting:

| Group | Severity | Response Time | Rationale |
|-------|----------|--------------|-----------|
| core-platform (G1) | P1 (page) | Immediate | All services depend on data-api |
| ml-engine (G3) | P2 (alert) | 5 min | AI features degrade but basic function continues |
| automation-intelligence (G4) | P2 (alert) | 5 min | Automation suggestions stop but HA control works |
| data-collectors (G2) | P3 (notify) | 15 min | Weather/energy data stale but not blocking |
| device-management (G5) | P3 (notify) | 10 min | Health monitoring delayed but devices work |
| frontends (G6) | P3 (notify) | 10 min | Dashboard unavailable but backend functional |

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
  "group": "automation-intelligence",
  "message": "Fetched 150 events from Data API"
}
```

This enables log aggregation and filtering by group in Loki/Elasticsearch.
