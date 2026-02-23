# HomeIQ Documentation Index

**Last Updated:** February 9, 2026
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
| [stories/epic-homeiq-automation-improvements.md](../stories/epic-homeiq-automation-improvements.md) | Epic: HomeIQ automation platform improvements (schema, patterns, validation, RAG) |
| [stories/epic-reusable-pattern-framework.md](../stories/epic-reusable-pattern-framework.md) | Epic: Reusable Pattern Framework — Phase 2 (shared abstractions) |
| [stories/epic-high-value-domain-extensions.md](../stories/epic-high-value-domain-extensions.md) | Epic: High-Value Domain Extensions — Phase 3 (Energy, Blueprint, DeviceSetup) |
| [stories/epic-platform-wide-pattern-rollout.md](../stories/epic-platform-wide-pattern-rollout.md) | Epic: Platform-Wide Pattern Rollout — Phase 4 (Security, Comfort, Scenes, Device Intelligence) |
| [libs/homeiq-patterns/README.md](../libs/homeiq-patterns/README.md) | Reusable patterns documentation — 8 RAG domains, 5 validation endpoints, 5 verifiers |
| [implementation/](../implementation/) | Implementation notes; Playwright E2E plan, execution status, issues list |
| [implementation/PHASE4_AUTOMATION_API_DOCUMENTATION.md](../implementation/PHASE4_AUTOMATION_API_DOCUMENTATION.md) | Automation validation API, deploy response fields, RAG reference |
| [docs/planning/automation-architecture-reusable-patterns-prd.md](planning/automation-architecture-reusable-patterns-prd.md) | PRD: Automation architecture and reusable patterns across HomeIQ (all 4 phases complete) |

### Services and ports
| Path | Description |
|------|-------------|
| [docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md](architecture/SERVICES_RANKED_BY_IMPORTANCE.md) | **Service tiers and Docker host ports** (8042, 8043, etc.) |
| [docs/architecture/README_ARCHITECTURE_QUICK_REF.md](architecture/README_ARCHITECTURE_QUICK_REF.md) | Service architecture quick reference |

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
- `docs/implementation/` → use **implementation/** (project root) for Playwright E2E plan, execution status, issues

---

## Cursor and Docker reference checklist

- **Docker / deployment:** Point to `docs/deployment/DEPLOYMENT_RUNBOOK.md` and `docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md`.
- **API and ports:** Point to `docs/api/API_REFERENCE.md` and `docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md`.
- **Epic/planning docs:** Use `docs/planning/` or `stories/`; no `docs/prd/` in this repo.
- **Implementation notes:** Use `implementation/` (create files as needed); do not reference missing files under `implementation/`.
