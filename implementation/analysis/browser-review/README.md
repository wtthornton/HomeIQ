# Browser Review – localhost:3001 & localhost:3000

Playwright MCP review of every page and link on both apps. Each page has a dedicated `.md` with **Issues** and **Enhancements** for later fixes.

**Reviewed:** 2026-02-28

---

## Port 3001 – AI Automation UI (Ideas app)

| Page | File | Routes / Notes |
|------|------|----------------|
| Ideas | [3001-ideas.md](./3001-ideas.md) | `/` – Automation suggestions, source tabs |
| Chat | [3001-chat.md](./3001-chat.md) | `/chat` – HA Agent chat |
| Explore | [3001-explore.md](./3001-explore.md) | `/explore` – Discovery, device explorer |
| Insights | [3001-insights.md](./3001-insights.md) | `/insights` – Patterns, Device Connections, Room View |
| Automations | [3001-automations.md](./3001-automations.md) | `/automations` – Deployed automations |
| Settings | [3001-settings.md](./3001-settings.md) | `/settings` – Analysis schedule, confidence |

Additional route (no sidebar link): `/name-enhancement` – see 3001-settings or codebase.

---

## Port 3000 – Health Dashboard

| Tab / Page | File | Hash / Notes |
|------------|------|--------------|
| Overview | [3000-overview.md](./3000-overview.md) | `#overview` |
| Services | [3000-services.md](./3000-services.md) | `#services` |
| Groups | [3000-groups.md](./3000-groups.md) | `#groups` |
| Dependencies | [3000-dependencies.md](./3000-dependencies.md) | `#dependencies` |
| Configuration | [3000-configuration.md](./3000-configuration.md) | `#configuration` |
| Devices | [3000-devices.md](./3000-devices.md) | `#devices` |
| Events | [3000-events.md](./3000-events.md) | `#events` |
| Data Feeds | [3000-data-sources.md](./3000-data-sources.md) | `#data-sources` |
| Energy | [3000-energy.md](./3000-energy.md) | `#energy` |
| Sports | [3000-sports.md](./3000-sports.md) | `#sports` |
| Alerts | [3000-alerts.md](./3000-alerts.md) | `#alerts` |
| Device Health | [3000-hygiene.md](./3000-hygiene.md) | `#hygiene` |
| Automation Checks | [3000-validation.md](./3000-validation.md) | `#validation` |
| AI Performance | [3000-evaluation.md](./3000-evaluation.md) | `#evaluation` |
| Logs | [3000-logs.md](./3000-logs.md) | `#logs` |
| Analytics | [3000-analytics.md](./3000-analytics.md) | `#analytics` |

---

## Cross-cutting

- **Navigation:** Sidebar (3001) and hamburger + tab strip (3000) were exercised; all main links lead to the correct pages.
- **Theme:** Dark mode is supported on both apps.
- **Errors observed:** 3001 Ideas “Failed to load suggestions”; 3001 Explore “Failed to load devices” (demo mode); 3000 Overview KPIs “Loading…” in some runs; 3000 Services “DEGRADED PERFORMANCE” when applicable.

Use the per-page files for concrete issues and enhancement ideas.

## Epics & Stories

Epics created from this review:

- **AI Automation UI (3001):** [epic-browser-review-ai-automation-ui](../../stories/epic-browser-review-ai-automation-ui.md) – 4 stories
- **Health Dashboard (3000):** [epic-browser-review-health-dashboard](../../stories/epic-browser-review-health-dashboard.md) – 5 stories
- **TAPPS Quality Gate:** [epic-tapps-quality-gate-compliance](../../stories/epic-tapps-quality-gate-compliance.md) – 3 stories (converter/yaml_transformer scoring + Bandit findings)
