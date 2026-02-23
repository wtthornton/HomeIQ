# frontends

User-facing UIs and observability tooling. Fast iteration, independent build pipelines (Node/React vs Python).

## Services

| Service | Port | Role |
|---------|------|------|
| ai-automation-ui | 3001 | AI automation web UI (React) |
| observability-dashboard | 8501 | Monitoring dashboard (Streamlit) |
| jaeger | 16686 | Distributed tracing UI (external image) |

**Note:** `health-dashboard` (port 3000) is the primary UI. It is developed as a frontend but deployed with core-platform for availability. See `domains/core-platform/`.

## Depends On

core-platform (admin-api, data-api), automation-core (automation endpoints)

## Depended On By

Nothing — leaf of the dependency tree.

## Compose

```bash
docker compose -f domains/frontends/compose.yml up -d
```
