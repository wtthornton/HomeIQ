# Port 3000 (Health Dashboard) – Issues to Fix

**Source:** Crawl + smoke test run 2026-03-03

## Fixed
1. **process is not defined** – websocketIngestionFetcher.ts used `process.env.REACT_APP_*`; changed to `import.meta.env.VITE_WEBSOCKET_INGESTION_URL`
2. **process.env.NODE_ENV** – ServiceDetailsModal.tsx; changed to `import.meta.env.DEV`

## Remaining (backend / test resilience)

### Backend 404s (expected when admin-api/data-api not running)
- /api/v1/alerts/active, /api/devices, /api/entities, /api/integrations, /api/v1/activity
- Fix: Run full stack, or make UI show graceful empty/loading states

### Smoke tests failing (7)
- Devices, Events, Alerts, Data Sources, Hygiene, Validation, Analytics – expect data-testids or content that may not render when API returns 404
- Fix: Make smoke tests resilient (accept tab loads + loading/empty state OR data)

### Medium
- VITE_API_KEY security warning – documented; use session auth in production
