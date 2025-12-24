# Epic 23: Enhanced Event Data Capture

**Status:** 📋 **PLANNED**  
**Priority:** HIGH  
**Estimated Duration:** 4-6 days  
**Dependencies:** Epic 19 (Device & Entity Discovery)

---

## Overview

Enhance the event data capture pipeline to include critical missing fields identified through comprehensive analysis of Home Assistant event structures. This epic addresses gaps in automation tracing, device-level analytics, time-based analysis, and entity classification by capturing additional metadata that significantly improves analytical capabilities with minimal storage overhead (~18% increase, ~1.6 GB/year for typical home).

**Key Enhancement Areas:**
1. **Automation Causality Tracking** - Capture `context.parent_id` to trace automation chains
2. **Device-Level Analytics** - Link events to devices and areas for spatial analysis
3. **Time-Based Analysis** - Calculate state duration for dwell time and stability metrics
4. **Entity Classification** - Track entity categories for filtering diagnostic/config entities
5. **Device Metadata Enrichment** - Include manufacturer, model, and version for reliability analysis

---

## Business Value

### Current Limitations
- ❌ **Cannot trace automation chains** - No visibility into which automation triggered state changes
- ❌ **No device-level aggregation** - Cannot analyze "all sensors on Device X failing"
- ❌ **Missing time-based metrics** - Cannot calculate "how long was motion detected"
- ❌ **No entity filtering** - Cannot exclude diagnostic/config entities from analytics
- ❌ **Limited reliability analysis** - Cannot correlate issues with device manufacturers/models

### Benefits After Implementation
- ✅ **Automation debugging** - Trace event chains back to originating automation
- ✅ **Spatial analytics** - Energy usage per room, temperature zones
- ✅ **Behavioral analysis** - Motion sensor dwell time, door open duration
- ✅ **Data quality** - Filter noise from diagnostic entities
- ✅ **Device insights** - Identify unreliable manufacturers/models

---

## Technical Scope

### Data Fields to Add

| Field | Type | Storage | Priority | Impact |
|-------|------|---------|----------|--------|
| `context_parent_id` | InfluxDB Field | 32 bytes | **HIGH** | Automation causality |
| `device_id` | InfluxDB Tag | 32 bytes | **HIGH** | Device aggregation |
| `area_id` | InfluxDB Tag | 20 bytes | **HIGH** | Spatial analysis |
| `duration_in_state` | InfluxDB Field | 8 bytes | **HIGH** | Time analytics |
| `entity_category` | InfluxDB Tag | 15 bytes | **MEDIUM** | Entity filtering |
| `manufacturer` | InfluxDB Field | 30 bytes | **LOW** | Reliability analysis |
| `model` | InfluxDB Field | 40 bytes | **LOW** | Reliability analysis |
| `sw_version` | InfluxDB Field | 15 bytes | **LOW** | Version correlation |

**Total Additional Storage:** ~192 bytes/event (~9.6 MB/day, ~3.5 GB/year for 50k events/day)

### Affected Services

1. **WebSocket Ingestion Service** (`services/websocket-ingestion/`)
   - Extract additional context fields
   - Enrich events with device/area information from registry
   - Calculate duration metrics

2. **Enrichment Pipeline Service** (`services/enrichment-pipeline/`)
   - Validate new fields in data validator
   - Normalize entity category values
   - Store additional fields in InfluxDB

3. **Data API Service** (`services/data-api/`)
   - Add query endpoints for new fields
   - Enable filtering by device_id, area_id, entity_category
   - Provide automation tracing API

4. **Health Dashboard** (`services/health-dashboard/`)
   - Display device-level event grouping
   - Show automation chain visualization
   - Time-based analytics charts

---

## Stories

### Story 23.1: Context Hierarchy Tracking ⭐ HIGH
**Goal:** Capture `context.parent_id` to enable automation causality tracing

**Implementation:**
- Extract `context.parent_id` from Home Assistant events
- Store as InfluxDB field in `home_assistant_events` measurement
- Add validation for context structure
- Create API endpoint for automation chain queries

**Acceptance Criteria:**
1. `context_parent_id` field stored in InfluxDB for all events with parent context
2. Events without parent context store null/empty value
3. Data API provides `/api/v1/events/automation-trace/{context_id}` endpoint
4. Dashboard shows automation chain visualization (optional enhancement)
5. Storage overhead: ~32 bytes per event (~50% of events have parent_id)

**Estimated Effort:** 1 day

---

### Story 23.2: Device and Area Linkage ⭐ HIGH
**Goal:** Link events to devices and areas for spatial and device-level analytics

**Implementation:**
- Enhance discovery service to maintain device_id → entity_id mapping
- Extract `device_id` and `area_id` from entity registry
- Store as InfluxDB tags for efficient querying
- Add device/area filtering to event query endpoints

**Acceptance Criteria:**
1. `device_id` tag stored for all events where entity has associated device
2. `area_id` tag stored for all events where entity/device has area assignment
3. Data API supports filtering: `/api/v1/events?device_id=xxx&area_id=yyy`
4. Device registry cache refreshes on device_registry_updated events
5. Performance: Device lookup adds <5ms to event processing

**Estimated Effort:** 1.5 days

---

### Story 23.3: Time-Based Analytics ⭐ HIGH
**Goal:** Calculate and store state duration for time-based behavioral analysis

**Implementation:**
- Calculate `duration_in_state` from `old_state.last_changed` to `new_state.last_changed`
- Store as InfluxDB field (float, seconds)
- Handle edge cases: first state (no old_state), timestamp parsing errors
- Add duration-based query endpoints

**Acceptance Criteria:**
1. `duration_in_state_seconds` field calculated for all state_changed events with old_state
2. First state changes (no old_state) store null or 0
3. Duration calculation handles timezone differences correctly
4. Data API provides duration aggregation queries (avg, max, percentiles)
5. Validation: Duration values are reasonable (0 to 7 days max, log warnings for outliers)

**Estimated Effort:** 1 day

---

### Story 23.4: Entity Classification
**Goal:** Capture entity_category for filtering diagnostic/config entities

**Implementation:**
- Extract `entity_category` from entity metadata
- Store as InfluxDB tag (values: `null`, `config`, `diagnostic`)
- Add entity_category filtering to queries
- Dashboard filter for "hide diagnostic entities"

**Acceptance Criteria:**
1. `entity_category` tag stored for entities with category defined
2. Entities without category store empty/null value
3. Data API supports filtering: `/api/v1/events?exclude_category=diagnostic`
4. Dashboard checkboxes: "Show diagnostic entities", "Show config entities"
5. Default dashboard view excludes diagnostic entities

**Estimated Effort:** 0.5 days

---

### Story 23.5: Device Metadata Enrichment
**Goal:** Include device manufacturer, model, and software version for reliability analysis

**Implementation:**
- Enrich events with device metadata from device registry
- Store `manufacturer`, `model`, `sw_version` as InfluxDB fields
- Create device reliability dashboard showing failure rates by manufacturer/model
- Add device metadata to event query responses

**Acceptance Criteria:**
1. `manufacturer`, `model`, `sw_version` fields stored for events with device association
2. Metadata populated from device registry cache (no per-event HA API calls)
3. Dashboard tab shows device reliability metrics grouped by manufacturer
4. API endpoint: `/api/v1/devices/reliability` with manufacturer/model breakdown
5. Storage optimization: Fields only stored if device_id present (avoid nulls)

**Estimated Effort:** 1 day

---

## Architecture Considerations

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Home Assistant Event (WebSocket)                            │
│ {                                                           │
│   "event_type": "state_changed",                           │
│   "context": {                                             │
│     "id": "abc123",                                        │
│     "parent_id": "xyz789"  ← NEW                          │
│   },                                                       │
│   "data": {                                                │
│     "entity_id": "sensor.temp",                           │
│     "new_state": { ... }                                   │
│   }                                                        │
│ }                                                          │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ WebSocket Ingestion (Enhancement)                           │
│ - Extract context.parent_id                                 │
│ - Lookup device_id from entity registry                     │
│ - Lookup area_id from device/entity registry                │
│ - Calculate duration_in_state                               │
│ - Extract entity_category                                   │
│ - Lookup device metadata (manufacturer, model, version)     │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ Enriched Event (Processed)                                  │
│ {                                                           │
│   "event_type": "state_changed",                           │
│   "entity_id": "sensor.temp",                              │
│   "context_parent_id": "xyz789",        ← NEW              │
│   "device_id": "device_abc",            ← NEW              │
│   "area_id": "living_room",             ← NEW              │
│   "entity_category": "diagnostic",      ← NEW              │
│   "duration_in_state": 123.45,          ← NEW (calculated) │
│   "device_metadata": {                  ← NEW              │
│     "manufacturer": "Aeotec",                              │
│     "model": "ZW100 MultiSensor 6",                        │
│     "sw_version": "1.10"                                   │
│   }                                                        │
│ }                                                          │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│ InfluxDB Point Structure                                    │
│                                                             │
│ Measurement: home_assistant_events                          │
│ Tags (indexed):                                             │
│   - entity_id                                               │
│   - domain                                                  │
│   - device_class                                            │
│   - device_id              ← NEW                           │
│   - area_id                ← NEW                           │
│   - entity_category        ← NEW                           │
│                                                             │
│ Fields (data):                                              │
│   - state                                                   │
│   - old_state                                               │
│   - context_parent_id      ← NEW                           │
│   - duration_in_state      ← NEW                           │
│   - manufacturer           ← NEW                           │
│   - model                  ← NEW                           │
│   - sw_version             ← NEW                           │
│   - attr_* (attributes)                                     │
└─────────────────────────────────────────────────────────────┘
```

### Performance Considerations

1. **Registry Lookups**
   - Cache device/entity registry in memory
   - Refresh on registry_updated events
   - Lookup time: <1ms per event (hash table)

2. **Duration Calculation**
   - Simple timestamp subtraction
   - Processing time: <0.1ms per event

3. **Storage Impact**
   - Base event: ~500 bytes
   - Enhanced event: ~692 bytes (+38%)
   - Daily: 50k events × 692 bytes = ~35 MB/day
   - Annual (with retention): ~3.5 GB/year (hot tier)

4. **Query Performance**
   - New tags (device_id, area_id, entity_category) enable fast filtering
   - Tag cardinality:
     - device_id: ~100-500 (typical home)
     - area_id: ~10-30 (typical home)
     - entity_category: 3 (null, config, diagnostic)

### Backward Compatibility

- ✅ **Existing queries unaffected** - New fields are optional
- ✅ **Gradual rollout** - Events without new fields continue to work
- ✅ **No schema migration** - InfluxDB handles new fields automatically
- ⚠️ **Dashboard updates required** - New visualizations need UI changes

---

## Testing Strategy

### Unit Tests
- Context extraction with/without parent_id
- Device/area lookup from registry cache
- Duration calculation edge cases (no old_state, timezone handling)
- Entity category normalization
- Device metadata lookup performance

### Integration Tests
- End-to-end event flow with all new fields
- Registry cache update on device_registry_updated
- InfluxDB write with new fields
- Query filtering by new tags

### Performance Tests
- Event processing throughput (target: >1000 events/sec)
- Registry lookup latency (target: <1ms per lookup)
- Storage growth rate validation
- Query performance with new tags

### Validation Tests
- Data completeness: % of events with each new field
- Data accuracy: Cross-check device_id against HA API
- Duration reasonableness: Detect outliers (>7 days, <0)

---

## Rollout Plan

### Phase 1: Core Fields (Stories 23.1-23.3) - Days 1-3
1. Deploy context.parent_id capture
2. Deploy device_id and area_id linkage
3. Deploy duration_in_state calculation
4. Monitor storage growth and performance
5. Validate data accuracy with sample queries

### Phase 2: Classification & Enrichment (Stories 23.4-23.5) - Days 4-6
1. Deploy entity_category filtering
2. Deploy device metadata enrichment
3. Update dashboard with new visualizations
4. Create device reliability dashboard
5. Document new API endpoints

### Phase 3: Validation & Optimization - Day 7 (optional)
1. Run comprehensive data quality checks
2. Optimize registry cache refresh strategy
3. Add monitoring alerts for missing fields
4. Performance tuning if needed

---

## Success Metrics

### Data Completeness
- **Target:** >95% of events have device_id (where applicable)
- **Target:** >98% of events have area_id (for entities with area assignment)
- **Target:** 100% of events with parent context have context_parent_id
- **Target:** 100% of state_changed events have duration_in_state

### Performance
- **Target:** Event processing latency <50ms (95th percentile)
- **Target:** Registry lookup time <1ms average
- **Target:** Storage growth within predicted range (±10%)

### API Usage
- **Measurement:** Track usage of new query filters (device_id, area_id, entity_category)
- **Measurement:** Automation trace API call frequency
- **Measurement:** Device reliability dashboard views

### Data Quality
- **Target:** <0.1% invalid duration values (negative or >7 days)
- **Target:** 0 schema conflicts in InfluxDB writes
- **Target:** <1% events with missing expected fields

---

## Dependencies

### Required
- **Epic 19:** Device & Entity Discovery - Provides device/entity registry data
- **InfluxDB 2.7+** - Schema flexibility for new fields
- **Python 3.11+** - Datetime handling for duration calculation

### Optional
- **Epic 22:** SQLite Metadata Storage - Could optimize device registry lookups (future)

---

## Risks & Mitigations

### Risk: Storage Overhead Exceeds Predictions
**Likelihood:** Low  
**Impact:** Medium  
**Mitigation:**
- Monitor storage growth in Phase 1
- Implement field-level retention policies if needed
- Consider storing device metadata separately and referencing by device_id

### Risk: Registry Lookup Performance Degradation
**Likelihood:** Low  
**Impact:** Medium  
**Mitigation:**
- Benchmark registry cache performance before deployment
- Implement LRU cache with size limits
- Add performance monitoring alerts

### Risk: Incomplete Device/Area Assignments
**Likelihood:** Medium  
**Impact:** Low  
**Mitigation:**
- Accept that some entities don't have devices/areas (virtual entities)
- Document expected field coverage percentages
- Provide dashboard filters to identify entities without assignments

### Risk: Context Parent ID Not Always Present
**Likelihood:** High  
**Impact:** Low  
**Mitigation:**
- Design queries to handle null/empty parent_id gracefully
- Document that only automation-triggered events have parent_id
- Provide percentage metrics of events with parent context

---

## Documentation Updates

### User Documentation
- API documentation for new query parameters
- Dashboard user guide for automation tracing
- Device reliability metrics interpretation

### Developer Documentation
- Registry cache implementation details
- Duration calculation methodology
- InfluxDB schema updates

### Operations Documentation
- Storage growth projections
- Monitoring alerts configuration
- Troubleshooting guide for missing fields

---

## Future Enhancements (Post-Epic)

### Potential Follow-on Work
1. **Automation Chain Visualization** - Interactive graph showing event causality
2. **Predictive Maintenance** - Alert on device reliability degradation
3. **Spatial Heatmaps** - Energy/activity visualization by area
4. **Time Pattern Analysis** - Identify recurring duration patterns
5. **Entity Lifecycle Tracking** - Monitor entity creation/deletion/modification

---

## Epic Timeline

```
Week 1: Core Implementation
├── Day 1: Story 23.1 - Context Hierarchy (context.parent_id)
├── Day 2: Story 23.2 - Device/Area Linkage (device_id, area_id)
├── Day 3: Story 23.3 - Time Analytics (duration_in_state)
├── Day 4: Story 23.4 - Entity Classification (entity_category)
├── Day 5: Story 23.5 - Device Metadata (manufacturer, model, sw_version)
├── Day 6: Integration testing, dashboard updates
└── Day 7: Validation, optimization, documentation (optional buffer)
```

**Total Estimated Duration:** 5-7 days  
**Confidence Level:** High (leveraging existing Epic 19 infrastructure)

---

## Acceptance Criteria (Epic Level)

1. ✅ All 7 new fields captured and stored in InfluxDB
2. ✅ Storage overhead within 20% of predictions (~200 bytes/event)
3. ✅ Event processing performance maintained (<50ms p95)
4. ✅ Data completeness targets met (>95% for applicable fields)
5. ✅ API endpoints support filtering by new fields
6. ✅ Dashboard displays device-level and area-level analytics
7. ✅ Documentation complete (API, user, developer, operations)
8. ✅ All unit and integration tests passing
9. ✅ No regression in existing event processing functionality
10. ✅ Production deployment successful with monitoring alerts configured

---

**Epic Owner:** @dev  
**Created:** January 2025  
**Target Completion:** Q1 2025  
**Status:** 📋 Planning Phase

