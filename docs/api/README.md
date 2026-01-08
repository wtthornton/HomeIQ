# API Documentation

**Status:** ✅ Consolidated (October 20, 2025)

## Single Source of Truth

**📖 [API_REFERENCE.md](./API_REFERENCE.md)** - Complete API documentation for all HA Ingestor services.

This is the **ONLY** API reference you need. It consolidates:
- Admin API (Port 8003) - System monitoring & Docker management
- Data API (Port 8006) - Events, devices, sports, analytics
- Sports Data Service (Port 8005) - ESPN integration
- AI Automation Service (Port 8018) - Automation suggestions
- Statistics API - Real-time metrics & performance

## Quick Links

### By Service
- [Admin API](./API_REFERENCE.md#admin-api) - Health checks, Docker, configuration
- [Data API](./API_REFERENCE.md#data-api) - Events, devices, analytics
- [Sports API](./API_REFERENCE.md#sports-api-service) - Team Tracker integration
- [AI Automation](./API_REFERENCE.md#ai-automation-service) - Suggestions & conversational AI
- [Statistics](./API_REFERENCE.md#statistics-api) - Metrics & performance

### By Use Case
- [Home Assistant Integration](./API_REFERENCE.md#integration-examples) - Automations & webhooks
- [Dashboard Development](./API_REFERENCE.md#real-time-metrics-dashboard-optimized) - Real-time metrics
- [External Analytics](./API_REFERENCE.md#external-analytics-dashboard) - Historical queries

## Historical Files (Superseded)

The following files have been **SUPERSEDED** by API_REFERENCE.md:

| File | Status | Notes |
|------|--------|-------|
| `../API_DOCUMENTATION.md` | ⛔ SUPERSEDED | Use [API_REFERENCE.md](./API_REFERENCE.md) |
| `../API_COMPREHENSIVE_REFERENCE.md` | ⛔ SUPERSEDED | Use [API_REFERENCE.md](./API_REFERENCE.md) |
| `../API_ENDPOINTS_REFERENCE.md` | ⛔ SUPERSEDED | Use [API_REFERENCE.md](./API_REFERENCE.md) |
| `../API_DOCUMENTATION_AI_AUTOMATION.md` | ⛔ SUPERSEDED | See [AI Automation section](./API_REFERENCE.md#ai-automation-service) |
| `../API_STATISTICS_ENDPOINTS.md` | ⛔ SUPERSEDED | See [Statistics section](./API_REFERENCE.md#statistics-api) |

These files will be moved to `docs/archive/` in the next cleanup phase.

## What Changed?

### Before (October 2025)
- 5 separate API documentation files
- Massive duplication (same endpoints documented 3-4 times)
- Inconsistent organization
- 3,033 total lines spread across files
- Agent confusion about which file to use

### After (October 20, 2025)
- 1 comprehensive API reference
- Zero duplication
- Consistent structure
- 687 lines (77% reduction)
- Clear single source of truth

### Benefits
✅ **For Agents:** One file to reference, no confusion  
✅ **For Developers:** Single place to update, easier maintenance  
✅ **For Users:** Clear navigation, complete information  
✅ **For Integrations:** Consistent examples, accurate details

## Contributing

When documenting new API endpoints:
1. Add them to [API_REFERENCE.md](./API_REFERENCE.md)
2. Follow the existing structure and format
3. Include request/response examples
4. Update the endpoint summary table
5. Never create separate API documentation files

## Questions?

- See [API_REFERENCE.md](./API_REFERENCE.md) for complete documentation
- Check [Architecture docs](../architecture/) for system design
- Review [Deployment Guide](../DEPLOYMENT_GUIDE.md) for setup

---

**Last Updated:** October 20, 2025  
**Consolidation By:** Documentation Cleanup Project (Option 3 - Hybrid Approach)

