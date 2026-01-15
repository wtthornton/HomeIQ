# HomeIQ API Automation Edge Service

API-driven automation engine that transitions from YAML-based automations to typed, versioned automation specs executed via Home Assistant REST and WebSocket APIs.

## Features

- **Capability Graph**: Discovers and maintains entity/service inventory from Home Assistant
- **Validation Pipeline**: Validates specs with target resolution, service compatibility, and policy gates
- **Execution Engine**: Deterministic executor with idempotency, retry, circuit breaker, and confirmation
- **Task Queue**: Asynchronous execution with Huey SQLite backend (prioritization, persistent retry, delayed execution)
- **Scheduling**: Cron-based periodic task scheduling for automation specs
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

### Task Queue Configuration (Huey)

- `USE_TASK_QUEUE`: Enable task queue (default: "true")
- `HUEY_DATABASE_PATH`: SQLite database path for task queue (default: "./data/automation_queue.db")
- `HUEY_WORKERS`: Number of worker threads (default: 4)
- `HUEY_RESULT_TTL`: Result storage TTL in seconds (default: 604800 = 7 days)
- `HUEY_SCHEDULER_INTERVAL`: Periodic task check interval in seconds (default: 1.0)

## API Endpoints

### Spec Management

- `GET /health` - Health check (includes queue status)
- `POST /api/specs` - Create/update spec
- `GET /api/specs/{spec_id}` - Get spec
- `GET /api/specs/{spec_id}/history` - Get spec history
- `POST /api/specs/{spec_id}/deploy` - Deploy spec version
- `GET /api/specs` - List active specs

### Execution

- `POST /api/execute/{spec_id}` - Execute spec (queues task if USE_TASK_QUEUE=true)
  - Query params: `delay` (seconds), `eta` (ISO datetime), `use_queue` (override config)
- `GET /api/tasks/{task_id}` - Get task status and result
- `GET /api/tasks` - List tasks (with filters: status, spec_id, limit)
- `POST /api/tasks/{task_id}/cancel` - Cancel pending task
- `GET /api/tasks/queue/status` - Get queue health metrics
- `GET /api/tasks/history` - Get task execution history

### Scheduling

- `GET /api/schedules` - List all scheduled automations
- `POST /api/schedules/{spec_id}/enable` - Enable schedule for automation
- `POST /api/schedules/{spec_id}/disable` - Disable schedule for automation
- `GET /api/schedules/{spec_id}/next-run` - Get next run time

### Observability

- `GET /api/observability/explain/{correlation_id}` - Get execution explanation
- `GET /api/observability/kill-switch/status` - Get kill switch status
- `POST /api/observability/kill-switch/pause` - Pause automations (revokes queued tasks)
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

**Synchronous execution (USE_TASK_QUEUE=false):**
```bash
curl -X POST http://localhost:8025/api/execute/{spec_id} \
  -H "Content-Type: application/json" \
  -d '{"trigger_data": {...}}'
```

**Asynchronous execution (USE_TASK_QUEUE=true, default):**
```bash
curl -X POST "http://localhost:8025/api/execute/{spec_id}?delay=300" \
  -H "Content-Type: application/json" \
  -d '{"trigger_data": {...}}'
# Returns immediately with task_id
```

**Delayed execution (execute in 5 minutes):**
```bash
curl -X POST "http://localhost:8025/api/execute/{spec_id}?delay=300" \
  -H "Content-Type: application/json" \
  -d '{"trigger_data": {...}}'
```

**Scheduled execution (execute at specific time):**
```bash
curl -X POST "http://localhost:8025/api/execute/{spec_id}?eta=2026-01-20T14:30:00Z" \
  -H "Content-Type: application/json" \
  -d '{"trigger_data": {...}}'
```

**Check task status:**
```bash
curl http://localhost:8025/api/tasks/{task_id}
```

**Cancel task:**
```bash
curl -X POST http://localhost:8025/api/tasks/{task_id}/cancel
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
  -e USE_TASK_QUEUE=true \
  -e HUEY_DATABASE_PATH=/app/data/automation_queue.db \
  -v api_automation_edge_data:/app/data \
  api-automation-edge
```

**Note:** The data volume (`api_automation_edge_data:/app/data`) persists the SQLite task queue database across container restarts.

## References

- PRD: `implementation/HomeIQ_API_Driven_Automations_Docs/HomeIQ_PRD_API_Driven_Automations.md`
- Architecture: `implementation/HomeIQ_API_Driven_Automations_Docs/HomeIQ_Architecture_and_Interfaces.md`
- Spec Schema: `implementation/HomeIQ_API_Driven_Automations_Docs/HomeIQ_AutomationSpec_v1.schema.json`
