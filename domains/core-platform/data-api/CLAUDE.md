# Data API Service

Tier-1 critical service. All queries (events, devices, analytics) go through here.

## Architecture

- `src/main.py` — FastAPI app, service class, middleware, router registration
- `src/*_endpoints.py` — Route handlers grouped by domain
- `src/database.py` — PostgreSQL connection management
- `src/cache.py` — In-memory caching layer

## Key Patterns

- Auth: Bearer token via `AuthManager` (all sensitive routes use `_auth_dependency`)
- CORS: Credentials disabled when wildcard origins (security hardening)
- Metrics: Per-request timing via `metrics_buffer`, error tracking on service instance
- Observability: OpenTelemetry tracing + correlation ID middleware

## Testing

```bash
cd domains/core-platform/data-api
pytest tests/ -v
```
