# Archived Services

This directory contains archived/deprecated services that have been replaced by newer implementations.

## Archive Structure

Services are archived by quarter:
- `2025-q4/` - Services archived in Q4 2025 (October-December)

## Archived Services

### Q4 2025

#### `ai-automation-service` (December 22, 2025)
- **Status:** Deprecated
- **Replaced By:** `services/ai-automation-service-new/`
- **Reason:** Microservice migration (Story 39.10)
- **Migration Date:** December 22, 2025
- **Location:** `2025-q4/ai-automation-service/`

**Why Archived:**
- Monolithic service split into focused microservices
- New service follows 2025 FastAPI patterns (async/await, dependency injection)
- Improved testability and maintainability
- Better separation of concerns

**Migration Notes:**
- All core functionality migrated to `ai-automation-service-new`
- Suggestion generation, YAML generation, and deployment logic preserved
- Database schema compatible (shared SQLite database)
- All integration tests passing in new service

## Archive Policy

1. **Services are archived when:**
   - Replaced by newer implementation
   - Deprecated for 30+ days
   - No longer in active use

2. **Archive retention:**
   - Services kept for 1 year for reference
   - After 1 year, moved to long-term archive or removed

3. **Access:**
   - Archived services are read-only
   - No active development or bug fixes
   - Documentation preserved for historical reference

## Restoring Archived Services

If you need to restore an archived service:

1. Copy from archive to `services/` directory
2. Update `docker-compose.yml` if needed
3. Review and update dependencies
4. Test thoroughly before production use
5. Consider migrating to newer implementation instead

---

**Last Updated:** December 22, 2025

