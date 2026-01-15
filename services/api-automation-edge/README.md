# HomeIQ API Automation Edge Service

API-driven automation engine that transitions from YAML-based automations to typed, versioned automation specs executed via Home Assistant REST and WebSocket APIs.

## Features

- **Capability Graph**: Discovers and maintains entity/service inventory from Home Assistant
- **Validation Pipeline**: Validates specs with target resolution, service compatibility, and policy gates
- **Execution Engine**: Deterministic executor with idempotency, retry, circuit breaker, and confirmation
- **Observability**: Structured logging, metrics, and explainability
- **Rollout Management**: Canary rollouts, rollback, and kill switch
- **Security**: Encrypted secrets and webhook hardening

## Architecture

```
HomeIQ Control Plane (Spec Registry, Policy, Rollout)
    ↓
HomeIQ Edge Agent (this service)
    ├── Capability Graph Builder
    ├── Validator + Planner
    ├── Executor
    └── Observability
    ↓
Home Assistant (REST API + WebSocket API)
```

## Configuration

Environment variables:

- `HA_URL` / `HOME_ASSISTANT_URL`: Home Assistant URL
- `HA_TOKEN` / `HOME_ASSISTANT_TOKEN`: Home Assistant access token
- `HOME_ID`: Home ID (default: "default")
- `DATABASE_URL`: Database URL (default: SQLite)
- `INFLUXDB_URL`: InfluxDB URL for metrics
- `INFLUXDB_TOKEN`: InfluxDB token
- `INFLUXDB_ORG`: InfluxDB organization
- `INFLUXDB_BUCKET`: InfluxDB bucket (default: "homeiq_metrics")
- `SERVICE_PORT`: Service port (default: 8025)
- `LOG_LEVEL`: Log level (default: "INFO")

## API Endpoints

- `GET /health` - Health check
- `POST /api/specs` - Create/update spec
- `GET /api/specs/{spec_id}` - Get spec
- `GET /api/specs/{spec_id}/history` - Get spec history
- `POST /api/specs/{spec_id}/deploy` - Deploy spec version
- `GET /api/specs` - List active specs
- `POST /api/execute/{spec_id}` - Execute spec
- `GET /api/observability/explain/{correlation_id}` - Get execution explanation
- `GET /api/observability/kill-switch/status` - Get kill switch status
- `POST /api/observability/kill-switch/pause` - Pause automations
- `POST /api/observability/kill-switch/resume` - Resume automations

## Usage

### Validate Spec

```bash
python -m tools.cli.validate_spec path/to/spec.yaml
```

### Create Spec

```bash
curl -X POST http://localhost:8025/api/specs \
  -H "Content-Type: application/json" \
  -d @spec.json
```

### Execute Spec

```bash
curl -X POST http://localhost:8025/api/execute/{spec_id} \
  -H "Content-Type: application/json" \
  -d '{"trigger_data": {...}}'
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python -m src.main
```

## Docker

```bash
docker build -t api-automation-edge services/api-automation-edge/
docker run -p 8025:8025 \
  -e HA_URL=http://home-assistant:8123 \
  -e HA_TOKEN=your-token \
  api-automation-edge
```

## References

- PRD: `implementation/HomeIQ_API_Driven_Automations_Docs/HomeIQ_PRD_API_Driven_Automations.md`
- Architecture: `implementation/HomeIQ_API_Driven_Automations_Docs/HomeIQ_Architecture_and_Interfaces.md`
- Spec Schema: `implementation/HomeIQ_API_Driven_Automations_Docs/HomeIQ_AutomationSpec_v1.schema.json`
