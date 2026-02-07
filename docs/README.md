# HomeIQ Documentation Index

**Last Updated:** February 7, 2026  
**Purpose:** Single index of existing docs so Cursor rules and Docker references point to correct paths.

---

## Existing documentation (use these paths)

### API
| Path | Description |
|------|-------------|
| [docs/api/API_REFERENCE.md](api/API_REFERENCE.md) | **Single source of truth** for all API endpoints and ports |
| [docs/api/README.md](api/README.md) | API doc overview and quick links |
| [docs/api/service-metrics-api-design.md](api/service-metrics-api-design.md) | Service metrics API design |
| [docs/api/v2/conversation-api.md](api/v2/conversation-api.md) | Conversation API v2 |

### Architecture
| Path | Description |
|------|-------------|
| [docs/architecture/database-schema.md](architecture/database-schema.md) | Hybrid DB schema (InfluxDB + SQLite) |
| [docs/architecture/event-flow-architecture.md](architecture/event-flow-architecture.md) | Event flow and tiers |
| [docs/architecture/influxdb-schema.md](architecture/influxdb-schema.md) | InfluxDB schema |

### Deployment
| Path | Description |
|------|-------------|
| [docs/deployment/DEPLOYMENT_RUNBOOK.md](deployment/DEPLOYMENT_RUNBOOK.md) | **Primary deployment guide** – steps, services, ports |
| [docs/deployment/DEPLOYMENT_PIPELINE.md](deployment/DEPLOYMENT_PIPELINE.md) | CI/CD pipeline |
| [docs/deployment/NGINX_PROXY_CONFIGURATION.md](deployment/NGINX_PROXY_CONFIGURATION.md) | Nginx proxy patterns |

### Planning & implementation
| Path | Description |
|------|-------------|
| [docs/planning/](planning/) | Phase reports, rebuild guides, upgrade plans, deployment checklist |
| [docs/implementation/](implementation/) | Automation linter implementation notes |

### Services and ports
| Path | Description |
|------|-------------|
| [services/SERVICES_RANKED_BY_IMPORTANCE.md](../services/SERVICES_RANKED_BY_IMPORTANCE.md) | **Service tiers and Docker host ports** (8042, 8043, etc.) |
| [services/README_ARCHITECTURE_QUICK_REF.md](../services/README_ARCHITECTURE_QUICK_REF.md) | Service architecture quick reference |

### Scripts
| Path | Description |
|------|-------------|
| [scripts/README_DEPLOYMENT.md](../scripts/README_DEPLOYMENT.md) | Deployment script usage |

### Workflows
| Path | Description |
|------|-------------|
| [docs/workflows/simple-mode/](workflows/simple-mode/) | Simple Mode workflow outputs (step N artifacts) |

---

## Paths that do not exist (avoid or replace)

- `docs/DEPLOYMENT_GUIDE.md` → use **docs/deployment/DEPLOYMENT_RUNBOOK.md**
- `docs/prd/` → not present; use **docs/planning/** or **stories/** for planning/epics
- `docs/current/` → not present
- `docs/archive/` → not present
- `docs/TROUBLESHOOTING_GUIDE.md` → use **tools/cli/docs/TROUBLESHOOTING.md** if applicable
- `docs/architecture/deployment-architecture.md` → use **docs/deployment/** or **docs/architecture/event-flow-architecture.md**
- `docs/architecture/index.md`, `source-tree.md`, `BLUEPRINT_ARCHITECTURE.md`, `data-models.md` → not present
- `implementation/*.md` → **implementation/** is empty; create files there if needed

---

## Cursor and Docker reference checklist

- **Docker / deployment:** Point to `docs/deployment/DEPLOYMENT_RUNBOOK.md` and `services/SERVICES_RANKED_BY_IMPORTANCE.md`.
- **API and ports:** Point to `docs/api/API_REFERENCE.md` and `services/SERVICES_RANKED_BY_IMPORTANCE.md`.
- **Epic/planning docs:** Use `docs/planning/` or `stories/`; no `docs/prd/` in this repo.
- **Implementation notes:** Use `implementation/` (create files as needed); do not reference missing files under `implementation/`.
