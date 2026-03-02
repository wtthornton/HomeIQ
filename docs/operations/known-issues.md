# Known Issues

**Project:** HomeIQ
**Last Updated:** March 2, 2026
**Phase:** 5 — Production Deployment

---

## Active Issues

| ID | Severity | Component | Description | Workaround | Status |
|---|---|---|---|---|---|
| KI-001 | Low | websocket-ingestion | 2 HA-dependent services show degraded health when Home Assistant is unavailable | Expected behavior — services operate in graceful degradation mode | Accepted |
| KI-002 | Low | data-collectors | air-quality, carbon-intensity, electricity-pricing, calendar services use `production` Docker profile — not started by default `docker compose up` | Use `--profile production` or deploy all: `docker compose --profile production up -d` | By Design |

---

## Resolved Issues (Phase 5 Deployment)

| ID | Severity | Component | Description | Resolution | Date |
|---|---|---|---|---|---|
| _To be filled during deployment_ | | | | | |

---

## Issue Template

When adding a new known issue, use this format:

```markdown
| KI-XXX | Critical/High/Medium/Low | component-name | Brief description of the issue | Workaround or mitigation steps | Open/Investigating/Resolved/Accepted |
```

### Severity Definitions

- **Critical**: Service outage, data loss, or security vulnerability. Requires immediate action.
- **High**: Significant functionality impacted. Requires resolution within 24 hours.
- **Medium**: Partial functionality affected. Can be scheduled for next maintenance window.
- **Low**: Minor issue, cosmetic, or edge case. Tracked but not blocking.

---

## Monitoring

Known issues should be cross-referenced with:
- Prometheus alert rules: `infrastructure/prometheus/alerts.yml`
- Grafana dashboards: `http://localhost:3002`
- Service logs: `docker logs <container-name>`
- Post-deployment monitor: `./scripts/post-deployment-monitor.sh`
