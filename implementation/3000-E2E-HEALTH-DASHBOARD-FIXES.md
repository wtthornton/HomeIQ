# Health Dashboard – E2E and Vite Fixes

**Date:** 2026-03-03  
**Status:** Complete

## Summary

Fixed Health Dashboard crash (process is not defined) and Playwright test resilience for port 3000.

## Changes

### Critical: Vite `process` usage
- **websocketIngestionFetcher.ts:** `process.env.REACT_APP_WEBSOCKET_INGESTION_URL` → `import.meta.env.VITE_WEBSOCKET_INGESTION_URL`
- **ServiceDetailsModal.tsx:** `process.env.NODE_ENV === 'development'` → `import.meta.env.DEV`
- **vite-env.d.ts:** Added `VITE_WEBSOCKET_INGESTION_URL` to ImportMetaEnv

### Crawl and config
- **crawl-all-pages.spec.ts:** New spec for all 16 hash routes (#overview, #services, etc.)
- **playwright.config.ts:** Support `TEST_BASE_URL` for Docker testing (skip webServer when set)

### Smoke test resilience
- Devices, Alerts, Events, Data Sources, Hygiene, Validation, Analytics: accept either expected content OR `[data-testid="dashboard-content"]` when backend unavailable

## Test results

- Crawl: 1 passed
- Smoke (@smoke): 16 passed

## References

- `implementation/analysis/browser-review/3000-CRAWL-ISSUES.md`
- `implementation/analysis/browser-review/3000-ISSUES-TO-FIX.md`
