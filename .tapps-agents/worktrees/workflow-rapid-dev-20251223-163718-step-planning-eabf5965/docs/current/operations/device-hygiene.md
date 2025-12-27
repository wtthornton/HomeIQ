# Device Hygiene Insight & Remediation

## Overview
- Adds inline hygiene analysis to `device-intelligence-service` (duplicate names, placeholder names, missing areas, stale discoveries, disabled entities).
- New REST endpoints exposed at `http://DEVICE_INTELLIGENCE_URL/api/hygiene/*` to list issues, update status, and run remediation tasks against Home Assistant via WebSocket APIs.
- `data-api` now proxies hygiene endpoints under `/api/v1/hygiene/*`, so dashboards and external consumers can reuse the feature without direct access to device-intelligence.
- Health Dashboard includes a "🧼 Device Hygiene" tab that surfaces findings, filters by status/severity/type, and allows one-click remediation or status changes.

## Service Configuration
- `services/device-intelligence-service/AUTH_CONFIGURATION_GUIDE.md` documents token creation, rotation, reconnect policy, and recommended Home Assistant account privileges.
- Environment variables consumed by device-intelligence:
  - `HA_URL`, `HA_TOKEN` (existing) – required for hygiene analyzer and remediation actions.
  - Optional fallbacks `NABU_CASA_URL`, `LOCAL_HA_URL`, and associated tokens still function as before.
- `data-api` expects `DEVICE_INTELLIGENCE_URL` (defaults to `http://localhost:8019`) for proxy calls.

## API Surface
### Device Intelligence (`:8019`)
- `GET /api/hygiene/issues` – returns `{ issues, count, total }` with serialized findings.
- `POST /api/hygiene/issues/{issue_key}/status` – body `{ "status": "open" | "ignored" | "resolved" }`.
- `POST /api/hygiene/issues/{issue_key}/actions/apply` – body `{ "action": <string>, "value"?: <string> }` triggers remediation (rename device, assign area, enable entity, start config flow).

### Data API (`:8006`)
- `GET /api/v1/hygiene/issues`
- `POST /api/v1/hygiene/issues/{issue_key}/status`
- `POST /api/v1/hygiene/issues/{issue_key}/actions/apply`
- These endpoints simply proxy to device-intelligence and return identical payloads; useful for UI and external integrations.

## Dashboard Usage
- Navigate to the "🧼 Device Hygiene" tab to view summarized counts (open issues, high severity concerns, pending configuration items).
- Filters support status, severity, and issue type; the Refresh button re-fetches from `/api/v1/hygiene/issues`.
- Action buttons:
  - `Apply Suggestion` – calls `/actions/apply` (rename device, set area, enable entity, or mark resolved when no automation is available).
  - `Ignore` / `Reopen` – toggles status via `/status` endpoint.
- Busy states and errors surface inline; remediation errors typically indicate Home Assistant connectivity problems.

## Testing
- Unit tests cover analyzer (`tests/test_hygiene_analyzer.py`), HA client parsing (`tests/test_ha_client.py`), remediation service (`tests/test_remediation_service.py`), and hygiene router (`tests/test_hygiene_router.py`).
- Data API includes proxy tests (`services/data-api/tests/test_hygiene_endpoints.py`).
- Health Dashboard tab is a React component (`HygieneTab.tsx`) – run `npm run dev` for manual verification and target `/api/v1/hygiene` endpoints in the backend.

## Operational Notes
- Hygiene analysis runs as part of the discovery loop. Adjusting HA connection tokens or areas will be reflected on the next discovery cycle (or when `force_refresh` is invoked).
- Remediation writes directly to Home Assistant’s registry APIs; ensure automations referencing renamed entities are reviewed, although Home Assistant will auto-update references in most cases.
- Resolved issues remain stored with `resolved_at` timestamps, enabling historical audit if needed.

