<div align="center">

# HomeIQ

**AI-Powered Home Automation Intelligence Platform**

Transform your Home Assistant into an intelligent automation powerhouse with conversational AI, pattern detection, and advanced analytics.

[![Production Ready](https://img.shields.io/badge/status-production%20ready-brightgreen?style=flat-square)](#)
[![Version](https://img.shields.io/badge/version-2.0.0-blue?style=flat-square)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-ISC-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Home Assistant](https://img.shields.io/badge/home%20assistant-compatible-41BDF5?style=flat-square&logo=home-assistant)](https://www.home-assistant.io/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-17-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

[Features](#features) · [Quick Start](#quick-start) · [Architecture](#architecture) · [Documentation](#documentation) · [Tech Stack](TECH_STACK.md) · [Changelog](CHANGELOG.md)

</div>

---

## Table of Contents

- [What is HomeIQ?](#what-is-homeiq)
- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Domain Groups](#domain-groups)
- [Documentation](#documentation)
- [Project Stats](#project-stats)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## What is HomeIQ?

HomeIQ is an **AI-powered companion for Home Assistant** that makes home automation accessible to everyone. Instead of writing complex YAML configurations, simply describe what you want in plain English.

**Traditional Home Assistant:**
```yaml
alias: "Evening Routine"
trigger:
  - platform: sun
    event: sunset
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
```

**With HomeIQ:**
```
You: "Turn on living room lights at sunset"
HomeIQ: Created automation. Want to add conditions or additional actions?
```

### Why HomeIQ?

| Feature | Description |
|---------|-------------|
| **Conversational AI** | Create automations by chatting — no YAML required |
| **Pattern Detection** | AI discovers automation opportunities from your usage data |
| **Advanced Analytics** | Deep insights into device behavior, energy usage, and trends |
| **Rich Integrations** | Weather, energy pricing, air quality, sports, calendar, and more |
| **Real-Time Dashboards** | Interactive monitoring with live data visualization |
| **Single-Home Optimized** | Designed for Intel NUC deployment, not cloud-dependent |

---

## Features

### AI-Powered Automation
- **Natural Language** — Create automations by describing what you want
- **Pattern Mining** — AI analyzes usage and suggests automations
- **Automation Linter** — Validate and auto-fix HA automations with 15+ quality rules ([docs](docs/automation-linter.md))
- **Device Templates** — Pre-built templates for common devices
- **Proactive Suggestions** — Context-aware recommendations based on weather, time, and events

### Device Intelligence
- **Health Monitoring** — Battery levels, response times, maintenance alerts
- **Smart Classification** — Automatic device type detection (fridge, car, light, sensor)
- **Setup Assistant** — Step-by-step guides for new devices
- **Power Analysis** — Compare actual vs. expected power usage

### Real-Time Analytics
- **Live Dashboard** — Monitor all devices and automations at [localhost:3000](http://localhost:3000)
- **Historical Data** — Analyze patterns over days, weeks, or months
- **Event Correlation** — Understand how devices interact
- **Performance Metrics** — Track system health and response times

### Data Enrichment
- **Weather** — Forecasts and conditions via OpenWeatherMap
- **Energy Pricing** — Real-time electricity costs
- **Air Quality** — AQI monitoring and alerts
- **Sports** — Live game tracking (NFL, NHL, and more)
- **Carbon Intensity** — Grid carbon footprint awareness
- **Calendar** — Event-triggered automations

---

## Quick Start

### Prerequisites

- [Home Assistant](https://www.home-assistant.io/) running on your local network
- Intel NUC (or similar) with 8GB+ RAM, 20GB+ disk space
- [Docker](https://www.docker.com/) and Docker Compose v2.0+

### Installation

```bash
# Clone the repository
git clone https://github.com/wtthornton/HomeIQ.git
cd HomeIQ

# Copy and configure environment
cp infrastructure/env.example infrastructure/.env

# Edit infrastructure/.env with your settings:
#   HA_HTTP_URL=http://YOUR_HA_IP:8123
#   HA_WS_URL=ws://YOUR_HA_IP:8123/api/websocket
#   HA_TOKEN=your-long-lived-access-token

# Start all services
docker compose up -d

# Verify deployment
./scripts/verify-deployment.sh
```

### First Steps

| Step | URL | Description |
|------|-----|-------------|
| 1. Health Dashboard | [localhost:3000](http://localhost:3000) | View system health, service status, dependency graph |
| 2. AI Automation | [localhost:3001](http://localhost:3001) | Chat with AI to create automations |
| 3. API Explorer | [localhost:8004/docs](http://localhost:8004/docs) | Interactive Swagger API documentation |
| 4. Observability | [localhost:8501](http://localhost:8501) | Traces, performance metrics, live logs |

### Selective Deployment

Deploy only the groups you need:

```bash
# Core only (data pipeline + dashboard)
docker compose -f domains/core-platform/compose.yml up -d

# Core + data collectors
docker compose -f domains/core-platform/compose.yml \
               -f domains/data-collectors/compose.yml up -d

# Full stack (all 50 services)
docker compose up -d
```

---

## Architecture

HomeIQ runs **50 microservices** organized into **9 domain groups** across 7 criticality tiers, designed for single-home deployment on resource-constrained hardware.

```
┌─────────────────────────────────────────────────────────┐
│                    HomeIQ Platform                       │
├─────────────────────────────────────────────────────────┤
│  Web Dashboards                                         │
│    Health Dashboard (:3000)  ·  AI Automation UI (:3001)│
│    Observability (:8501)     ·  Jaeger Tracing (:16686) │
├─────────────────────────────────────────────────────────┤
│  AI / ML Services                                       │
│    Conversational AI  ·  Pattern Detection  ·  NER      │
│    Device Intelligence  ·  Automation Mining  ·  RAG    │
├─────────────────────────────────────────────────────────┤
│  Core Platform                                          │
│    websocket-ingestion → InfluxDB (time-series)         │
│    data-api · admin-api · data-retention                │
├─────────────────────────────────────────────────────────┤
│  Data Layer                                             │
│    InfluxDB 2.7 (events, metrics)                       │
│    PostgreSQL 17 (metadata, schema-per-domain)          │
├─────────────────────────────────────────────────────────┤
│  Enrichment Services                                    │
│    Weather · Energy · Air Quality · Sports · Calendar   │
└─────────────────────────────────────────────────────────┘
                          ▲
                 ┌────────┴────────┐
                 │  Home Assistant  │
                 │   (Your Home)   │
                 └─────────────────┘
```

**Data Flow:** Home Assistant → websocket-ingestion → InfluxDB (direct writes, inline normalization) → data-api (query layer)

### Key Architecture Docs

- [Service Groups](docs/architecture/service-groups.md) — The 9-domain deployment structure
- [Service Tiers](docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md) — Complete criticality classification
- [Event Flow](docs/architecture/event-flow-architecture.md) — Event processing and data flow
- [Database Schema](docs/architecture/database-schema.md) — InfluxDB + PostgreSQL schema reference

---

## Domain Groups

| # | Domain | Services | Purpose |
|---|--------|----------|---------|
| 1 | **core-platform** | 6 | Data backbone — InfluxDB, data-api, websocket-ingestion, admin-api, dashboard, retention |
| 2 | **data-collectors** | 8 | Stateless data fetchers — weather, energy, sports, air quality, calendar, logs |
| 3 | **ml-engine** | 10 | ML inference and training — OpenVINO, NER, OpenAI, RAG, device-intelligence |
| 4 | **automation-core** | 7 | Automation engine — NL to YAML, entity resolution, validation, deployment |
| 5 | **blueprints** | 4 | Blueprint discovery, indexing, ML recommendations |
| 6 | **energy-analytics** | 3 | Energy correlator, forecasting, proactive agent |
| 7 | **device-management** | 8 | Device health, setup, classification, activity recognition |
| 8 | **pattern-analysis** | 2 | Behavioral patterns, synergy detection |
| 9 | **frontends** | 4 | AI automation UI, observability dashboard, health dashboard, Jaeger |

Each domain group has its own `compose.yml` under `domains/<group>/` and can be deployed independently. See [Service Groups Architecture](docs/architecture/service-groups.md) for dependency graph and deployment commands.

---

## Documentation

### Getting Started
| Document | Description |
|----------|-------------|
| [Deployment Runbook](docs/deployment/DEPLOYMENT_RUNBOOK.md) | Step-by-step deployment guide with service verification |
| [Deployment Pipeline](docs/deployment/DEPLOYMENT_PIPELINE.md) | CI/CD pipeline documentation |
| [API Reference](docs/api/API_REFERENCE.md) | Complete REST API reference with all endpoints and ports |

### Architecture
| Document | Description |
|----------|-------------|
| [Service Groups](docs/architecture/service-groups.md) | 9-domain group structure and deployment topology |
| [Database Schema](docs/architecture/database-schema.md) | InfluxDB + PostgreSQL schema reference |
| [Event Flow](docs/architecture/event-flow-architecture.md) | Event processing pipeline and data flow |
| [Quick Reference](docs/architecture/README_ARCHITECTURE_QUICK_REF.md) | Service patterns and architecture overview |

### Operations
| Document | Description |
|----------|-------------|
| [PostgreSQL Runbook](docs/operations/postgresql-runbook.md) | Database operations, maintenance, and troubleshooting |
| [Disaster Recovery](docs/operations/disaster-recovery.md) | Backup, restore, and recovery procedures |
| [Monitoring Setup](docs/operations/monitoring-setup.md) | Prometheus + Grafana configuration |
| [Service Health Checks](docs/operations/service-health-checks.md) | Health endpoint patterns and verification |

### Development
| Document | Description |
|----------|-------------|
| [Tech Stack](TECH_STACK.md) | Complete technology reference with versions |
| [Automation Linter](docs/automation-linter.md) | YAML linting and validation service |
| [Linter Rules](docs/automation-linter-rules.md) | Complete rules catalog |
| [Changelog](CHANGELOG.md) | Version history |

### Project Planning
| Document | Description |
|----------|-------------|
| [Open Epics Index](stories/OPEN-EPICS-INDEX.md) | All open epics and stories with priorities |
| [Rebuild Status](REBUILD_STATUS.md) | Phase completion status |
| [Phase 5 Deployment](docs/planning/phase-5-deployment-plan.md) | Production deployment plan |

---

## Project Stats

| Metric | Value |
|--------|-------|
| **Services** | 50 microservices across 9 domain groups |
| **Target Hardware** | Intel NUC (i3/i5, 8–16 GB RAM) |
| **Memory Footprint** | ~8–10 GB (optimized) |
| **Optimized For** | Single home, 50–100 devices |
| **Backend** | Python 3.12, FastAPI 0.115–0.124, Pydantic 2.x |
| **Frontend** | React 18.3, TypeScript 5.9, Vite 6.4, Tailwind CSS 3.4 |
| **AI/ML** | Sentence-Transformers 3.3, OpenAI GPT-4o-mini, scikit-learn |
| **Databases** | InfluxDB 2.7.12 (time-series), PostgreSQL 17 (metadata) |
| **Observability** | OpenTelemetry, Jaeger 1.75, Prometheus, Grafana |
| **Tests** | 704+ tests, Playwright E2E, pytest-asyncio |

---

## Roadmap

### Completed

- [x] Conversational AI automation (NL to YAML)
- [x] Pattern detection and proactive suggestions
- [x] Device health monitoring and classification
- [x] Multi-source data enrichment (7 providers)
- [x] PostgreSQL migration — sole database (Epic 0 complete)
- [x] Library upgrades — Phases 1–2 complete
- [x] Frontend redesign — teal palette, sidebar nav, accessibility
- [x] Agent evaluation framework with observability
- [x] Cross-group resilience (circuit breakers, health aggregation)
- [x] Security hardening (SQL injection, timing attacks, CORS)

### In Progress

- [ ] Frontend security hardening (Epic 1 — Sprint 1)
- [ ] Observability dashboard fixes (Epic 4)
- [ ] Health dashboard quality improvements (Epic 2)
- [ ] Phase 3 ML library upgrades (NumPy 2.x, Pandas 3.0)

### Future

- [ ] Production deployment (Phase 5)
- [ ] Frontend framework upgrades (React 19, Vite 7, Tailwind 4)
- [ ] Mobile app integration
- [ ] Voice assistant support
- [ ] Multi-language support

See [OPEN-EPICS-INDEX.md](stories/OPEN-EPICS-INDEX.md) for the full backlog and sprint plan.

---

## Contributing

Contributions are welcome! Here's how to get started:

```bash
# Fork the repo, then:
git clone https://github.com/YOUR_USERNAME/HomeIQ.git
cd HomeIQ

# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes, then commit
git commit -m "feat: add your feature description"

# Push and open a Pull Request
git push origin feature/your-feature-name
```

### Development Guidelines

- **Python**: Follow [ruff](https://docs.astral.sh/ruff/) formatting, type hints preferred
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`)
- **Tests**: Add tests for new features, run `pytest` before submitting
- **Docker**: Test your changes build with `docker compose build <service-name>`

---

## Support

- **Bug Reports** — [GitHub Issues](https://github.com/wtthornton/HomeIQ/issues)
- **Discussions** — [GitHub Discussions](https://github.com/wtthornton/HomeIQ/discussions)
- **Documentation** — [docs/](docs/)

---

## License

This project is licensed under the ISC License — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Home Assistant](https://www.home-assistant.io/) — The home automation platform
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [InfluxDB](https://www.influxdata.com/) — Time-series database
- [PostgreSQL](https://www.postgresql.org/) — Relational database
- [React](https://react.dev/) — UI library

---

<div align="center">

**Made with care for the Home Assistant community**

[Report Bug](https://github.com/wtthornton/HomeIQ/issues) · [Request Feature](https://github.com/wtthornton/HomeIQ/issues) · [Documentation](docs/)

</div>
