# WebSocket Ingestion Service

Tier-1 critical service. All Home Assistant events flow through here.

## Architecture

- `src/main.py` — Service class, lifecycle (start/stop)
- `src/_service_config.py` — Environment-based configuration dataclass
- `src/_event_handlers.py` — HA event callback methods (mixin)
- `src/_startup.py` — Startup phase helpers
- `src/api/app.py` — FastAPI application and health endpoints

## Key Patterns

- Events: HA WebSocket -> EntityFilter -> BatchProcessor -> AsyncEventProcessor -> InfluxDB
- Config: All tunables via environment variables (see `ServiceConfig`)
- Shutdown: Components stopped in reverse-init order; errors logged but never re-raised

## Testing

```bash
cd domains/core-platform/websocket-ingestion
pytest tests/ -v
```
