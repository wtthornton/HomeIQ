# Epic 45: Tiered Statistics Model - Home Assistant Alignment

**Status:** ✅ **COMPLETE**  
**Type:** Database Architecture & Performance Optimization  
**Priority:** High  
**Effort:** 5 Stories (12-16 hours estimated)  
**Created:** January 2025  
**Target Completion:** February 2025  
**Based On:** Home Assistant Database Model Analysis & Project Review

---

## Epic Goal

Implement a Home Assistant-aligned tiered statistics model that automatically aggregates raw events into short-term (5-minute) and long-term (hourly) statistics, enabling efficient long-term trend analysis while reducing storage by 80-90%. This epic aligns HomeIQ's data architecture with Home Assistant's proven three-tier statistics model while maintaining AI-specific pattern aggregates.

**Business Value:**
- **80-90% storage reduction** for long-term historical data
- **Faster historical queries** using aggregated statistics vs raw events
- **Better alignment** with Home Assistant's proven data model
- **Efficient long-term analytics** without storing all raw events indefinitely
- **Entity filtering** to reduce storage for low-value entities

---

## Existing System Context

### Current Data Architecture

**Location:** `services/websocket-ingestion/`, `services/data-api/`, InfluxDB buckets

**Current State:**
1. **Raw Events Storage**: All events stored in InfluxDB `home_assistant_events` bucket
   - Retention: 90-365 days (varies by configuration)
   - No automatic aggregation to statistics
   - Long-term queries scan raw event data (inefficient)

2. **Pattern Aggregates**: AI-specific daily/weekly/monthly aggregates exist
   - Location: `services/ai-automation-service/`
   - Purpose: Pattern detection for automation suggestions
   - Not general-purpose statistics

3. **No Entity Filtering**: All events captured regardless of value
   - Battery levels, diagnostic sensors stored indefinitely
   - No way to exclude low-value entities

4. **No Statistics Metadata**: No tracking of which entities support statistics
   - No `state_class` awareness
   - No distinction between measurement vs total_increasing entities

### Home Assistant Statistics Model (Reference)

**Three-Tier Architecture:**
- **`states` table**: Raw events (10 days default retention)
- **`statistics_short_term`**: 5-minute aggregates (configurable retention)
- **`statistics`**: Hourly aggregates (indefinite retention)
- **`statistics_meta`**: Metadata about tracked entities

**Benefits:**
- 24 entries per day per entity for long-term data
- Automatic downsampling: raw → 5-min → hourly
- Frontend uses appropriate data source based on time range

### Technology Stack
- **Database**: InfluxDB 2.7 (time-series), SQLite 3.45+ (metadata)
- **Services**: websocket-ingestion (Port 8001), data-api (Port 8006), data-retention (Port 8080)
- **Language**: Python 3.11+
- **Deployment**: Docker Compose (single-house NUC)

---

## Enhancement Details

### What's Being Added/Changed

1. **Tiered Statistics Model**
   - Short-term statistics: 5-minute aggregates (30 days retention)
   - Long-term statistics: Hourly aggregates (indefinite retention)
   - Automatic downsampling from raw events
   - New InfluxDB measurements: `statistics_short_term`, `statistics`

2. **Statistics Metadata Tracking**
   - SQLite `statistics_meta` table to track eligible entities
   - `state_class` detection from Home Assistant device registry
   - Only aggregate entities suitable for statistics (measurement, total_increasing)
   - Fast lookups for statistics eligibility

3. **Entity Filtering System**
   - Configuration for entity inclusion/exclusion
   - Filter by entity ID patterns, domain, device_class, area
   - Default: Include all, allow opt-out
   - Advanced: Include only specified entities

4. **Smart Query Routing**
   - Query optimization layer in data-api
   - Automatic data source selection based on time range:
     - Last 10 days: Raw events
     - 10-30 days: Short-term statistics
     - Beyond 30 days: Long-term statistics
   - Transparent to API consumers

5. **Retention Policy Optimization**
   - Reduce raw event retention to 7-30 days (from 90-365)
   - Short-term statistics: 30 days
   - Long-term statistics: Indefinite
   - Maintain pattern aggregates for AI use cases

### How It Integrates

- **New Service/Module**: Statistics aggregation service (or scheduled task in data-retention)
- **Extended Services**: 
  - `data-api`: Smart query routing, statistics endpoints
  - `websocket-ingestion`: Entity filtering during event capture
  - `data-retention`: Statistics aggregation scheduling
- **New Database Tables**: SQLite `statistics_meta` table
- **New InfluxDB Measurements**: `statistics_short_term`, `statistics`

### Success Criteria

- ✅ Short-term statistics (5-minute aggregates) created automatically
- ✅ Long-term statistics (hourly aggregates) created automatically
- ✅ Statistics metadata table tracks eligible entities
- ✅ Entity filtering system allows inclusion/exclusion configuration
- ✅ Raw event retention reduced to 30 days (configurable)
- ✅ Smart query routing selects appropriate data source by time range
- ✅ Storage reduction of 80-90% for long-term data
- ✅ Historical queries use statistics (faster performance)
- ✅ Pattern aggregates remain separate (AI-specific, not affected)
- ✅ Backward compatible: Existing queries continue to work

---

## Stories

### Story 45.1: Statistics Metadata Tracking & Entity Eligibility Detection

**As a** system administrator,  
**I want** the system to track which entities are eligible for statistics aggregation,  
**so that** only appropriate entities (temperature, energy, etc.) are aggregated, reducing unnecessary processing.

**Acceptance Criteria:**
1. SQLite `statistics_meta` table created in `data/metadata.db`
2. Table schema: `statistic_id` (entity_id), `source`, `unit_of_measurement`, `state_class`, `has_mean`, `has_sum`, `last_reset`
3. Service queries Home Assistant device registry for `state_class` attribute
4. Entities with `state_class: measurement` (temperature, humidity, etc.) added to metadata
5. Entities with `state_class: total_increasing` (energy meters) added to metadata
6. Metadata sync runs on device registry updates (via websocket-ingestion)
7. Fast lookup function: `is_statistics_eligible(entity_id)` returns boolean
8. Metadata table indexed for fast queries
9. Unit tests for metadata tracking logic

**Estimated Effort:** 3-4 hours

**Technical Notes:**
- Use existing device registry sync in websocket-ingestion
- Add metadata sync after device/entity discovery
- Store in SQLite for fast lookups (not InfluxDB)

---

### Story 45.2: Entity Filtering System for Event Capture

**As a** system administrator,  
**I want** to configure which entities are captured and stored,  
**so that** I can exclude low-value entities (battery levels, diagnostic sensors) and reduce storage costs.

**Acceptance Criteria:**
1. Configuration file or environment variables for entity filtering
2. Filter patterns supported:
   - Entity ID patterns (regex or glob)
   - Domain (sensor, binary_sensor, etc.)
   - Device class (battery, diagnostic, etc.)
   - Area/room
3. Default behavior: Include all entities (opt-out model)
4. Advanced mode: Include only specified entities (opt-in model)
5. Filter applied in websocket-ingestion before InfluxDB write
6. Filtered entities logged (debug level) for visibility
7. Configuration reloadable without service restart (optional)
8. Filter statistics tracked (entities filtered per hour/day)
9. Unit tests for filtering logic
10. Documentation with examples

**Estimated Effort:** 2-3 hours

**Technical Notes:**
- Add filter module to websocket-ingestion
- Check filter before `write_event()` call
- Use existing entity metadata (domain, device_class, area_id) for filtering

---

### Story 45.3: Short-Term Statistics Aggregation (5-Minute)

**As a** system administrator,  
**I want** 5-minute aggregated statistics created automatically from raw events,  
**so that** I have efficient short-term trend data without storing all raw events long-term.

**Acceptance Criteria:**
1. New InfluxDB measurement: `statistics_short_term`
2. Aggregation service/task runs every 5 minutes
3. Aggregates only entities in `statistics_meta` table
4. Aggregation metrics: `mean`, `min`, `max`, `sum` (where applicable)
5. Grouped by: `entity_id`, `domain`, `device_class`
6. Retention: 30 days (configurable)
7. Aggregation handles numeric states (temperature, humidity, energy, etc.)
8. Non-numeric states skipped (on/off, etc.)
9. Aggregation service logs progress and errors
10. Unit tests for aggregation logic
11. Performance: Aggregation completes in <30 seconds for typical home

**Estimated Effort:** 4-5 hours

**Technical Notes:**
- Can be scheduled task in data-retention service or separate microservice
- Use InfluxDB Flux queries for aggregation or Python aggregation
- Consider InfluxDB continuous queries vs scheduled Python task
- Store in same bucket or separate `statistics` bucket

---

### Story 45.4: Long-Term Statistics Aggregation (Hourly)

**As a** system administrator,  
**I want** hourly aggregated statistics created automatically from short-term statistics,  
**so that** I have efficient long-term trend data with minimal storage (24 entries/day per entity).

**Acceptance Criteria:**
1. New InfluxDB measurement: `statistics`
2. Aggregation service/task runs every hour
3. Aggregates from `statistics_short_term` (not raw events)
4. Aggregation metrics: `mean`, `min`, `max`, `sum` (where applicable)
5. Grouped by: `entity_id`, `domain`, `device_class`
6. Retention: Indefinite (no automatic deletion)
7. Aggregation handles numeric states only
8. Aggregation service logs progress and errors
9. Unit tests for aggregation logic
10. Performance: Aggregation completes in <60 seconds for typical home
11. Storage verification: ~24 entries/day per eligible entity

**Estimated Effort:** 3-4 hours

**Technical Notes:**
- Aggregate from `statistics_short_term` (12 five-minute periods = 1 hour)
- Use same aggregation service as Story 45.3 (different schedule)
- Store in same bucket or separate `statistics` bucket
- Consider InfluxDB continuous queries for automatic aggregation

---

### Story 45.5: Smart Query Routing & Retention Policy Optimization

**As a** system administrator,  
**I want** queries to automatically use the most efficient data source based on time range,  
**so that** historical queries are fast and storage is optimized without manual query selection.

**Acceptance Criteria:**
1. Query routing layer in data-api service
2. Automatic data source selection:
   - Last 10 days: Query raw events (`home_assistant_events`)
   - 10-30 days: Query short-term statistics (`statistics_short_term`)
   - Beyond 30 days: Query long-term statistics (`statistics`)
3. Transparent to API consumers (same endpoint, automatic routing)
4. Raw event retention reduced to 30 days (configurable, default 30)
5. Retention policy applied to `home_assistant_events` bucket
6. Existing query endpoints continue to work (backward compatible)
7. Query performance: Historical queries (30+ days) use statistics (10x faster)
8. Documentation updated with query routing behavior
9. Unit tests for query routing logic
10. Optional: Query endpoint parameter to force raw data (`?source=raw`)

**Estimated Effort:** 2-3 hours

**Technical Notes:**
- Extend existing query functions in `data-api/src/events_endpoints.py`
- Add time range detection logic
- Route to appropriate InfluxDB measurement
- Update retention policy via InfluxDB API or CLI

---

## Compatibility Requirements

- ✅ **Backward Compatible**: Existing queries continue to work
- ✅ **Pattern Aggregates Unchanged**: AI-specific daily/weekly/monthly aggregates remain separate
- ✅ **Historical Data Preserved**: No migration of existing data required
- ✅ **API Compatibility**: Existing API endpoints maintain same interface
- ✅ **Optional Feature**: Can be enabled/disabled via configuration
- ✅ **Gradual Rollout**: Statistics aggregation can be enabled per entity type

---

## Risk Mitigation

**Primary Risk 1:** Statistics aggregation might miss data or create incorrect aggregates  
**Mitigation:** 
- Comprehensive unit tests for aggregation logic
- Validation: Compare statistics against raw data samples
- Logging and monitoring for aggregation errors
- Gradual rollout: Enable for one entity type first

**Primary Risk 2:** Query routing might break existing functionality  
**Mitigation:**
- Backward compatible: Default to raw events if statistics unavailable
- Feature flag: Can disable smart routing
- Extensive testing of existing query endpoints
- Rollback plan: Disable statistics aggregation if issues found

**Primary Risk 3:** Storage reduction might not meet 80-90% target  
**Mitigation:**
- Calculate expected storage reduction before implementation
- Monitor actual storage usage after deployment
- Adjust retention policies if needed
- Entity filtering helps reduce raw event storage

**Rollback Plan:**
- Disable statistics aggregation service/task
- Revert retention policy to original (90-365 days)
- Disable smart query routing (use raw events only)
- All changes are additive (no data deletion)

---

## Definition of Done

- [x] All 5 stories completed with acceptance criteria met
- [x] Statistics metadata table created and populated
- [x] Entity filtering system configured and working
- [x] Short-term statistics (5-minute) aggregation running automatically
- [x] Long-term statistics (hourly) aggregation running automatically
- [x] Smart query routing selects appropriate data source
- [x] Raw event retention reduced to 30 days (configurable)
- [x] Storage reduction verified (80-90% for long-term data)
- [x] Query performance improved for historical queries
- [x] All existing queries continue to work (backward compatible)
- [x] Unit tests written and passing
- [x] Documentation updated (architecture, API, configuration)
- [x] Tested on single-house NUC deployment
- [x] No regression in existing functionality

---

## Deployment Context

**Single-House NUC Deployment:**
- Intel NUC i3/i5, 8-16GB RAM
- InfluxDB 2.7, SQLite 3.45+
- Python 3.11+, Docker Compose
- Typical home: 50-100 entities, ~10-20 eligible for statistics
- Optimized for resource constraints

**Not Designed For:**
- Multi-home deployments (statistics per home)
- Enterprise scale (different aggregation strategies)
- Real-time statistics (5-minute minimum granularity)

---

## Performance Targets

**Storage Reduction:**
- Raw events: 30 days (vs 90-365 days) = 67-92% reduction
- Long-term: 24 entries/day per entity (vs ~1000+ raw events/day) = 97%+ reduction
- **Overall: 80-90% storage reduction for long-term data**

**Query Performance:**
- Historical queries (30+ days): 10x faster using statistics
- Short-term queries (10-30 days): 5x faster using short-term statistics
- Recent queries (0-10 days): Same performance (raw events)

**Aggregation Performance:**
- Short-term aggregation: <30 seconds for typical home
- Long-term aggregation: <60 seconds for typical home
- Background processing: No impact on real-time event capture

---

## Related Epics & Dependencies

**Dependencies:**
- Epic 22: SQLite Metadata Storage (uses metadata.db)
- Epic 23: Enhanced Event Data Capture (uses entity metadata)
- Epic 31: Weather API Service Migration (architecture pattern)

**Related:**
- Epic 3: Data Enrichment & Storage (InfluxDB schema)
- Epic 4: Production Readiness & Monitoring (data-retention service)
- Epic AI-5: Incremental Pattern Processing (pattern aggregates remain separate)

**Future Enhancements:**
- Epic 46: Statistics Dashboard Visualization (if needed)
- Epic 47: Advanced Statistics Analytics (if needed)

---

## Implementation Notes

### Statistics Aggregation Options

**Option A: Scheduled Python Task (Recommended)**
- Background task in data-retention service
- Runs every 5 minutes (short-term) and every hour (long-term)
- Full control over aggregation logic
- Easy to debug and monitor

**Option B: InfluxDB Continuous Queries**
- Native InfluxDB feature
- Automatic aggregation
- Less flexible, harder to debug
- Better performance (native)

**Recommendation:** Start with Option A (Python task) for flexibility, consider Option B later if performance is critical.

### Entity Filtering Configuration

**Format (YAML or JSON):**
```yaml
entity_filtering:
  mode: "exclude"  # or "include"
  patterns:
    - entity_id: "sensor.*_battery"
    - domain: "diagnostic"
    - device_class: "battery"
  exceptions:
    - entity_id: "sensor.important_battery"  # Always include
```

### Statistics Metadata Schema

```sql
CREATE TABLE statistics_meta (
    statistic_id TEXT PRIMARY KEY,  -- entity_id
    source TEXT NOT NULL,  -- "state" or "sensor"
    unit_of_measurement TEXT,
    state_class TEXT,  -- "measurement", "total", "total_increasing"
    has_mean BOOLEAN DEFAULT 1,
    has_sum BOOLEAN DEFAULT 0,
    last_reset TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

**Epic Document Created:** January 2025  
**Based On:** Home Assistant Database Model Analysis & Project Architecture Review  
**Related Documentation:** 
- `docs/architecture/database-schema.md`
- `implementation/LESSONS_LEARNED_AND_RECOMMENDATIONS.md`
- Home Assistant Statistics Model: https://smarthomescene.com/blog/understanding-home-assistants-database-and-statistics-model/

