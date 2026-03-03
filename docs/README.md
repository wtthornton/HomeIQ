# HomeIQ Documentation

**Last Updated:** March 2, 2026

This is the **single index** for project documentation. Use it for correct paths; avoid creating duplicate guides at root.

---

## Quick Links

| Document | Description |
|----------|-------------|
| [README](../README.md) | Project overview, quick start, architecture |
| [Tech Stack](../TECH_STACK.md) | Complete technology reference with versions |
| [Rebuild Status](../REBUILD_STATUS.md) | Phase completion tracker |
| [Changelog](../CHANGELOG.md) | Version history and release notes |
| [Open Epics](../stories/OPEN-EPICS-INDEX.md) | All open work items with priorities |

---

## API

| Document | Description |
|----------|-------------|
| [API Reference](api/API_REFERENCE.md) | All endpoints, ports, and request/response schemas |
| [API Overview](api/README.md) | Quick links and API patterns |
| [Conversation API v2](api/v2/conversation-api.md) | Conversational AI endpoint specification |

---

## Architecture

| Document | Description |
|----------|-------------|
| [Service Groups](architecture/service-groups.md) | 9-domain group structure, dependency graph, deployment topology |
| [Service Tiers](architecture/SERVICES_RANKED_BY_IMPORTANCE.md) | Criticality classification and Docker host ports |
| [Event Flow](architecture/event-flow-architecture.md) | Event processing pipeline and data flow |
| [Database Schema](architecture/database-schema.md) | InfluxDB + PostgreSQL schema reference |
| [InfluxDB Schema](architecture/influxdb-schema.md) | InfluxDB measurements, tags, and fields |
| [Domain Structure](architecture/domain-structure.md) | Domain group folder layout |
| [Quick Reference](architecture/README_ARCHITECTURE_QUICK_REF.md) | Architecture patterns overview |

---

## Deployment

| Document | Description |
|----------|-------------|
| [Deployment Runbook](deployment/DEPLOYMENT_RUNBOOK.md) | Step-by-step deployment guide |
| [Deployment Pipeline](deployment/DEPLOYMENT_PIPELINE.md) | CI/CD pipeline documentation |
| [Nginx Proxy](deployment/NGINX_PROXY_CONFIGURATION.md) | Nginx reverse proxy patterns |

---

## Operations

| Document | Description |
|----------|-------------|
| [PostgreSQL Runbook](operations/postgresql-runbook.md) | Database operations, maintenance, troubleshooting |
| [Disaster Recovery](operations/disaster-recovery.md) | Backup, restore, and recovery procedures |
| [Monitoring Setup](operations/monitoring-setup.md) | Prometheus + Grafana configuration |
| [Service Health Checks](operations/service-health-checks.md) | Health endpoint patterns and verification |
| [Agent Evaluation](operations/agent-evaluation-runbook.md) | AI agent evaluation framework operations |

---

## Planning

| Document | Description |
|----------|-------------|
| [Phase 5 Deployment Plan](planning/phase-5-deployment-plan.md) | Production deployment strategy |
| [Phase 3 Readiness](planning/phase-3-readiness-report.md) | ML library upgrade readiness assessment |
| [Library Upgrade Plan](planning/library-upgrade-plan.md) | Dependency upgrade strategy and progress |
| [Frontend Redesign](planning/frontend-redesign-plan.md) | Frontend architecture and design system |
| [Quality Audit](planning/quality-audit-report.md) | Codebase quality assessment |
| [Deployment Checklist](planning/deployment-checklist.md) | Pre-deployment verification checklist |

---

## Features

| Document | Description |
|----------|-------------|
| [Automation Linter](automation-linter.md) | YAML linting and validation service |
| [Linter Rules](automation-linter-rules.md) | Complete linter rules catalog |
| [Frontend Terminology](frontend-terminology.md) | UI naming conventions and design system |

---

## Shared Libraries

| Package | README | Purpose |
|---------|--------|---------|
| homeiq-patterns | [libs/homeiq-patterns/README.md](../libs/homeiq-patterns/README.md) | RAG, validation routers, post-action verifiers |
| homeiq-resilience | [libs/homeiq-resilience/](../libs/homeiq-resilience/) | Circuit breakers, cross-group clients |
| homeiq-observability | [libs/homeiq-observability/](../libs/homeiq-observability/) | Structured logging, tracing, metrics |
| homeiq-data | [libs/homeiq-data/](../libs/homeiq-data/) | InfluxDB client, database pool, caching |
| homeiq-ha | [libs/homeiq-ha/](../libs/homeiq-ha/) | HA connection manager, lint engine |

---

## Path Corrections

| Invalid Path | Use Instead |
|-------------|-------------|
| `docs/DEPLOYMENT_GUIDE.md` | [docs/deployment/DEPLOYMENT_RUNBOOK.md](deployment/DEPLOYMENT_RUNBOOK.md) |
| `docs/DEVELOPMENT.md` | [docs/architecture/](architecture/) |
| `docs/QUICK_START.md` | [docs/deployment/DEPLOYMENT_RUNBOOK.md](deployment/DEPLOYMENT_RUNBOOK.md) |
| `docs/USER_MANUAL.md` | [README.md](../README.md) |
| `docs/TROUBLESHOOTING_GUIDE.md` | [tools/cli/docs/TROUBLESHOOTING.md](../tools/cli/docs/TROUBLESHOOTING.md) |
| `docs/prd/` | [docs/planning/](planning/) or root [stories/](../stories/) |
| `docs/DOCUMENTATION_INDEX.md` | This file: [docs/README.md](README.md) |
| `CONTRIBUTING.md` | [Contributing](../README.md#contributing) in README |
