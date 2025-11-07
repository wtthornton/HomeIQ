# Monitoring and Observability

### Monitoring Stack

- **Frontend Monitoring:** Browser console errors, API response times
- **Backend Monitoring:** Python logging with structured JSON format
- **Error Tracking:** Comprehensive error logging with request context
- **Performance Monitoring:** Response time tracking, database query performance

### Key Metrics

**Frontend Metrics:**
- API response times
- JavaScript errors
- Component render performance
- User interactions

**Backend Metrics:**
- Request rate and response times
- Error rate by endpoint
- Database query performance
- WebSocket connection health
- Weather API response times

## Environment Health Monitoring (Epic 31 Refresh – Nov 2025)

### Backend
- `/api/health/environment` now emits structured logs (`event=environment_health`) capturing health score, HA status, integration count, and detected issue totals.
- Health normalization safeguards strip unexpected integration fields while still persisting contextual `check_details` payloads for each integration.
- Any schema mismatch falls back to a synthetic `error` entry and logs a warning instead of surfacing 500s to the dashboard.

### Frontend
- `useEnvironmentHealth` surfaces backend error details directly (e.g. `Setup service error 503: Health monitoring service not initialized`) and guards against empty/malformed payloads.
- The Setup & Health tab renders integration `check_details` (broker host, bridge state, failure recommendations, etc.) to give operators actionable diagnostics without leaving the dashboard.
- Retry behaviour (`Try Again →`) reuses the same fetch path so new health data benefits immediately from backend logging and normalization changes.