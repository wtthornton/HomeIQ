# Domain Structure Reference

**Last Updated:** February 2026  
**Status:** Canonical reference for the 9-domain layout (Epic 5 Story 8)  
**See also:** [Service Groups Architecture](./service-groups.md), [Service Decomposition Plan](../planning/service-decomposition-plan.md)

---

## Purpose

This document is the single reference for the HomeIQ 9-domain structure after Domain Architecture Restructuring (Epics 1–4). Use it to find any service, its port, and how domains relate.

---

## Directory Tree (Top-Level)

```
homeiq/
├── domains/
│   ├── core-platform/       # 6 services — data backbone
│   ├── data-collectors/     # 8 services — external API fetchers
│   ├── ml-engine/           # 10 services — ML inference & training
│   ├── automation-core/     # 7 services — automation engine
│   ├── blueprints/          # 4 services — blueprint discovery
│   ├── energy-analytics/    # 3 services — energy intelligence
│   ├── device-management/   # 8 services — device lifecycle
│   ├── pattern-analysis/    # 2 services — pattern/synergy analysis
│   └── frontends/           # 4 services — UIs
├── libs/                    # 5 installable packages (ex-shared/)
├── docs/
├── implementation/
└── stories/
```

---

## The 9 Domains

| # | Domain | Services | Purpose |
|---|--------|----------|---------|
| 1 | **core-platform** | 6 | Data backbone — InfluxDB, data-api, websocket-ingestion, admin-api, health-dashboard, data-retention |
| 2 | **data-collectors** | 8 | Stateless fetchers — weather, sports, carbon, electricity, air-quality, calendar, smart-meter, log-aggregator |
| 3 | **ml-engine** | 10 | ML inference, embeddings, training — ai-core, openvino, ml-service, RAG, device-intelligence, etc. |
| 4 | **automation-core** | 7 | Core automation — ha-ai-agent, ai-automation-service-new, ai-query, automation-linter, yaml-validation, etc. |
| 5 | **blueprints** | 4 | Blueprint index, suggestion, rule-recommendation-ml, automation-miner |
| 6 | **energy-analytics** | 3 | energy-correlator, energy-forecasting, proactive-agent-service |
| 7 | **device-management** | 8 | Device health, classifier, setup, database client, recommender, activity-recognition, activity-writer, ha-setup |
| 8 | **pattern-analysis** | 2 | ai-pattern-service, api-automation-edge |
| 9 | **frontends** | 4 | ai-automation-ui, observability-dashboard, health-dashboard, jaeger |

**Total:** 50 deployed services (plus `ha-simulator` under dev profile and `nlp-fine-tuning`/`model-prep` as offline training tools).

---

## Service List by Domain (Port and Brief Description)

See [Service Groups Architecture](./service-groups.md) for the full table. Summary:

- **core-platform:** influxdb (8086), data-api (8006), websocket-ingestion (8001), admin-api (8004), health-dashboard (3000), data-retention (8080).
- **data-collectors:** weather-api (8009), sports-api (8005), carbon-intensity (8010), electricity-pricing (8011), air-quality (8012), calendar-service (8013), smart-meter-service (8014), log-aggregator (8015).
- **ml-engine, automation-core, blueprints, energy-analytics, device-management, pattern-analysis, frontends:** See service-groups.md for ports and descriptions.

---

## Compose File Locations

| Domain | Compose File |
|--------|--------------|
| core-platform | `domains/core-platform/compose.yml` |
| data-collectors | `domains/data-collectors/compose.yml` |
| ml-engine | `domains/ml-engine/compose.yml` |
| automation-core | `domains/automation-core/compose.yml` |
| blueprints | `domains/blueprints/compose.yml` |
| energy-analytics | `domains/energy-analytics/compose.yml` |
| device-management | `domains/device-management/compose.yml` |
| pattern-analysis | `domains/pattern-analysis/compose.yml` |
| frontends | `domains/frontends/compose.yml` |

Root full stack: project root `docker-compose.yml` (if present) or `docker buildx bake` with `docker-bake.hcl`.

---

## Inter-Domain Communication

- **Core-platform** is the root; no other group is required for it to run.
- **Data-collectors, ml-engine, device-management, pattern-analysis** depend only on core-platform (InfluxDB/data-api).
- **Automation-core, blueprints, energy-analytics** may also call ml-engine for inference.
- **Frontends** call admin-api and data-api (core-platform) and automation UIs as needed.

---

## CI Pipeline Mapping

- Build and test typically run per-domain or per-service under `domains/<group>/<service>/`.
- Root `docker buildx bake full` (or equivalent) builds all images; see `docker-bake.hcl`.
- GitHub Actions or other CI should trigger on changes under `domains/<group>/` for that group.

---

## References

- [Service Groups Architecture](./service-groups.md) — Full service table, ports, env vars, deploy commands
- [Service Decomposition Plan](../planning/service-decomposition-plan.md) — PRD and migration history
- [Migration Verification Checklist](./migration-verification-checklist.md) — Post-migration validation steps
