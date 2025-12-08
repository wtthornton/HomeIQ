# ADR 003: Epic 31 Architecture Simplification

**Status:** Accepted  
**Date:** October 2025 (Epic 31)  
**Context:** Simplify event processing pipeline, reduce latency and failure points  
**Deciders:** Architecture team

---

## Context

**Previous Architecture (Pre-Epic 31):**
```
Home Assistant → websocket-ingestion → enrichment-pipeline → InfluxDB
```

**Issues:**
- Two services in critical path (higher failure probability)
- Additional network hop (latency overhead)
- Enrichment-pipeline was single point of failure
- Dual write paths (complexity)

**Challenge:** Simplify architecture while maintaining functionality.

---

## Decision

**Deprecate enrichment-pipeline service** and move normalization inline to websocket-ingestion.

**New Architecture (Epic 31):**
```
Home Assistant → websocket-ingestion (inline normalization) → InfluxDB
```

**External Services Pattern:**
- Standalone services write directly to InfluxDB
- Services query via data-api
- No service-to-service dependencies

---

## Rationale

### Why Simplify?

1. **Reduced Latency:** Eliminated network hop (10-30ms saved)
2. **Fewer Failure Points:** One less service in critical path
3. **Simpler Deployment:** One less container to manage
4. **Better Performance:** Inline processing is faster than HTTP POST

### Why Not Keep Enrichment-Pipeline?

- Added unnecessary complexity for single-home deployment
- Network latency overhead (10-30ms per batch)
- Single point of failure
- Overkill for current scale

### Why Inline Normalization?

- Normalization logic is simple (field mapping, type conversion)
- No need for separate service
- Better performance (no network overhead)
- Easier to maintain (all logic in one place)

---

## Consequences

### Positive

- **Lower Latency:** 10-30ms faster event processing
- **Higher Reliability:** One less service to fail
- **Simpler Architecture:** Easier to understand and maintain
- **Better Performance:** Inline processing is faster
- **Cleaner Code:** All normalization logic in one place

### Negative

- **Code Migration:** Normalization logic moved to websocket-ingestion
- **Service Removal:** enrichment-pipeline service deprecated
- **Documentation Updates:** Need to update all references

### Neutral

- **Functionality:** All features preserved
- **Data Format:** No changes to stored data
- **API:** No changes to external APIs

---

## Implementation

### Code Changes

**websocket-ingestion/src/main.py:**
- Added inline normalization (lines 411-420)
- Removed HTTP client for enrichment-pipeline
- Direct InfluxDB writes

**enrichment-pipeline:**
- Service deprecated
- Code removed from active deployment
- Documentation updated to mark as deprecated

### External Services Pattern

**All external services follow this pattern:**
1. Fetch from external API (ESPN, OpenWeatherMap, etc.)
2. Write directly to InfluxDB
3. Query via data-api
4. Display on dashboard

**Examples:**
- `weather-api` (Port 8009) - Standalone, writes to InfluxDB
- `sports-data` (Port 8005) - Writes scores to InfluxDB
- `carbon-intensity` (Port 8010) - Writes carbon data to InfluxDB

**DO NOT:**
- ❌ Make services HTTP POST to websocket-ingestion
- ❌ Create service-to-service dependencies
- ✅ Write directly to InfluxDB
- ✅ Query via data-api

---

## Migration

**Epic 31 Migration:**
- ✅ Normalization logic moved inline
- ✅ enrichment-pipeline service deprecated
- ✅ All references updated
- ✅ Documentation updated

**No Data Migration Required:**
- Data format unchanged
- Existing data remains valid
- No breaking changes to APIs

---

## Validation

**Epic 31 Results:**
- ✅ 10-30ms latency reduction
- ✅ Zero service failures (enrichment-pipeline removed)
- ✅ Simpler architecture
- ✅ All functionality preserved

**Current Status:** Production-proven, no issues reported

---

## Related Decisions

- [ADR 002: Hybrid Database Architecture](002-hybrid-database-architecture.md)
- Epic 31 Architecture Pattern (`.cursor/rules/epic-31-architecture.mdc`)

---

## Notes

**Critical Rule:** See `.cursor/rules/epic-31-architecture.mdc` for:
- Current architecture patterns
- Deprecated services (DO NOT reference)
- Code patterns to follow
- When to update this rule

---

**Last Updated:** December 3, 2025

