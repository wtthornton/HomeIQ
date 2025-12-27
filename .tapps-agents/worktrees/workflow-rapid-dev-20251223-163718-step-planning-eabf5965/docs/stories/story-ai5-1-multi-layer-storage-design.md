# Story AI5.1: Multi-Layer Storage Design & Schema

**Story ID:** AI5.1  
**Epic:** Epic-AI-5 (Incremental Pattern Processing Architecture)  
**Priority:** Critical  
**Effort:** 6-8 hours  
**Dependencies:** None

---

## User Story

**As a** system architect  
**I want** to design a multi-layer storage architecture for pattern aggregates  
**So that** we can process data incrementally and query efficiently across different time windows

---

## Context

Currently, the system processes 30 days of raw events daily and discards all intermediate calculations. This epic converts to an incremental architecture where:
- Raw events are processed once
- Daily aggregates are stored for historical queries
- Each detector queries its optimal time window

This story defines the storage schema and architecture for all layers.

---

## Acceptance Criteria

### Schema Design
- [ ] Layer 1 (Raw Events) schema documented
- [ ] Layer 2 (Daily Aggregates) schema designed for all 10 detector types
- [ ] Layer 3 (Weekly/Monthly Aggregates) schema designed
- [ ] Layer 4 (Pattern Summaries) schema reviewed (existing)
- [ ] Data retention policies defined for each layer

### InfluxDB Schema
- [ ] Measurement names defined for each detector type
- [ ] Tag structure optimized for query performance
- [ ] Field structure supports all detector metrics
- [ ] Bucket names and retention policies specified

### Documentation
- [ ] Architecture diagram created
- [ ] Schema documentation written
- [ ] Query patterns documented
- [ ] Storage size estimates calculated

---

## Technical Design

### Layer 1: Raw Events (Existing)
```
Bucket: home_assistant_events
Retention: 7 days (reduced from 30)
Measurement: home_assistant_events
Tags:
  - entity_id
  - device_id
  - event_type
  - domain
  - area_id
Fields:
  - state (string)
  - attr_friendly_name (string)
Size Estimate: ~700K events (7 days × 100K/day)
```

### Layer 2: Daily Aggregates (NEW)
```
Bucket: pattern_aggregates_daily
Retention: 90 days
Measurements: One per detector type

time_based_daily:
  Tags:
    - date (2025-01-15)
    - entity_id
    - domain
  Fields:
    - hourly_distribution (JSON array[24])
    - peak_hours (JSON array)
    - frequency (float)
    - confidence (float)
    - occurrences (int)

co_occurrence_daily:
  Tags:
    - date
    - device_pair (sorted, e.g., "light.a|switch.b")
  Fields:
    - co_occurrence_count (int)
    - time_window_seconds (int)
    - confidence (float)
    - typical_hours (JSON array)

sequence_daily:
  Tags:
    - date
    - sequence_id (hash of device sequence)
  Fields:
    - sequence (JSON array of entity_ids)
    - frequency (int)
    - avg_duration_seconds (float)
    - confidence (float)

room_based_daily:
  Tags:
    - date
    - area_id
  Fields:
    - activity_level (float)
    - device_usage (JSON object)
    - transition_patterns (JSON array)
    - peak_activity_hours (JSON array)

duration_daily:
  Tags:
    - date
    - entity_id
  Fields:
    - avg_duration_seconds (float)
    - min_duration_seconds (float)
    - max_duration_seconds (float)
    - duration_variance (float)
    - efficiency_score (float)

anomaly_daily:
  Tags:
    - date
    - entity_id
    - anomaly_type
  Fields:
    - anomaly_score (float)
    - baseline_deviation (float)
    - occurrences (int)
    - severity (string)

Size Estimate: ~90 days × 10 detectors × ~10 records/day = ~9K records
```

### Layer 3: Weekly/Monthly Aggregates (NEW)
```
Bucket: pattern_aggregates_weekly
Retention: 52 weeks

session_weekly:
  Tags:
    - week (2025-W03)
    - session_type
  Fields:
    - avg_session_duration (float)
    - session_count (int)
    - typical_start_times (JSON array)
    - devices_used (JSON array)

day_type_weekly:
  Tags:
    - week
    - day_type (weekday|weekend)
  Fields:
    - activity_patterns (JSON object)
    - device_usage_diff (JSON object)
    - confidence (float)

contextual_monthly:
  Tags:
    - month (2025-01)
    - weather_context
    - presence_context
  Fields:
    - device_usage_patterns (JSON object)
    - correlation_scores (JSON object)
    - confidence (float)

seasonal_monthly:
  Tags:
    - month
    - season
  Fields:
    - seasonal_activity_level (float)
    - year_over_year_comparison (JSON object)
    - trend_direction (string)

Size Estimate: ~52 weeks × 4 detectors × ~5 records/week = ~1K records
```

### Layer 4: Pattern Summaries (Existing - SQLite)
```
Table: patterns
Retention: Forever (or configurable)
Purpose: High-level pattern catalog for UI/API
Schema: (unchanged)
  - id
  - pattern_type
  - device_id
  - pattern_metadata (JSON)
  - confidence
  - occurrences
  - created_at
```

---

## Storage Size Estimates

### Current System
- Raw Events: 3M events × 30 days = 90M events (~9GB)
- Pattern Summaries: ~1K records (~1MB)
- **Total: ~9GB**

### Proposed System
- Layer 1 (Raw): 700K events × 7 days = 4.9M events (~500MB)
- Layer 2 (Daily): 9K records (~50MB)
- Layer 3 (Weekly): 1K records (~5MB)
- Layer 4 (Summaries): ~1K records (~1MB)
- **Total: ~556MB (94% reduction)**

---

## Query Patterns

### Daily Detector Queries
```flux
// Time-based pattern for last 30 days
from(bucket: "pattern_aggregates_daily")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "time_based_daily")
  |> filter(fn: (r) => r.entity_id == "light.living_room")
```

### Weekly Detector Queries
```flux
// Session patterns for last 7 days
from(bucket: "pattern_aggregates_daily")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "session_daily")
  |> aggregateWindow(every: 1w, fn: mean)
```

### Cross-Layer Queries
```flux
// Combine daily and weekly data
daily = from(bucket: "pattern_aggregates_daily")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "day_type_daily")

weekly = from(bucket: "pattern_aggregates_weekly")
  |> range(start: -4w)
  |> filter(fn: (r) => r._measurement == "day_type_weekly")

union(tables: [daily, weekly])
```

---

## Data Retention Policies

### Layer 1: Raw Events
- **Retention**: 7 days
- **Rationale**: Only needed for daily processing
- **Cleanup**: Automatic via InfluxDB retention policy

### Layer 2: Daily Aggregates
- **Retention**: 90 days
- **Rationale**: Supports 30-day pattern analysis with buffer
- **Cleanup**: Automatic via InfluxDB retention policy

### Layer 3: Weekly/Monthly Aggregates
- **Retention**: 52 weeks (1 year)
- **Rationale**: Supports seasonal analysis
- **Cleanup**: Automatic via InfluxDB retention policy

### Layer 4: Pattern Summaries
- **Retention**: Configurable (default: forever)
- **Rationale**: Historical pattern catalog
- **Cleanup**: Manual or via admin API

---

## Implementation Tasks

### Task 1: Document Layer 1 Schema (1h)
- Review existing InfluxDB schema
- Document current structure
- Define retention policy change (30d → 7d)

### Task 2: Design Layer 2 Schema (3-4h)
- Define measurements for each detector type
- Design tag structure for optimal queries
- Design field structure for all metrics
- Document JSON field schemas
- Calculate storage estimates

### Task 3: Design Layer 3 Schema (2h)
- Define measurements for weekly/monthly aggregates
- Design aggregation strategies
- Document rollup calculations

### Task 4: Create Architecture Diagram (1h)
- Draw multi-layer architecture
- Show data flow between layers
- Document query patterns

### Task 5: Document Retention Policies (1h)
- Define retention for each layer
- Document cleanup strategies
- Calculate storage requirements over time

---

## Testing Strategy

### Schema Validation
- [ ] All required fields defined
- [ ] Tag cardinality acceptable (<100K unique values)
- [ ] JSON field schemas validated
- [ ] Storage estimates realistic

### Query Performance
- [ ] Query patterns tested with sample data
- [ ] Index strategy validated
- [ ] Cross-layer queries performant

---

## Documentation Deliverables

1. **Architecture Diagram** (`docs/architecture/multi-layer-storage.md`)
   - Visual representation of all 4 layers
   - Data flow between layers
   - Retention policies

2. **Schema Documentation** (`docs/architecture/influxdb-schema.md`)
   - Complete schema for all measurements
   - Tag and field descriptions
   - Query pattern examples

3. **Storage Estimates** (`docs/architecture/storage-estimates.md`)
   - Current vs proposed storage
   - Growth projections
   - Retention policy impact

4. **Migration Plan** (`docs/architecture/migration-plan.md`)
   - Steps to migrate from current to new schema
   - Rollback procedures
   - Data preservation strategy

---

## Definition of Done

- [ ] All 4 layers documented with complete schemas
- [ ] InfluxDB measurements defined for all detector types
- [ ] Tag and field structures optimized for queries
- [ ] Retention policies defined and justified
- [ ] Storage estimates calculated and validated
- [ ] Architecture diagram created
- [ ] Schema documentation written
- [ ] Query patterns documented with examples
- [ ] Migration plan outlined
- [ ] Peer review completed
- [ ] Technical lead approval obtained

---

## Notes

### Design Considerations for Single-Home System
- **Simplicity**: Use simple tag structures, avoid over-optimization
- **Storage**: Optimize for 32-128GB disk space typical in edge devices
- **Performance**: Optimize for 100K-200K events/day, not millions
- **Reliability**: Design for graceful degradation if storage fills

### JSON Field Usage
- Use JSON fields for complex nested data (arrays, objects)
- Keep JSON fields small (<1KB typical)
- Consider flattening if query performance suffers
- Document JSON schema for each field

### Tag Cardinality
- Keep tag cardinality low (<10K unique values per tag)
- Use entity_id as tag (typically <100 entities in single home)
- Use date as tag for efficient time-based queries
- Avoid high-cardinality tags (timestamps, UUIDs)

---

**Story Points:** 5  
**Sprint:** Epic AI-5 Sprint 1  
**Status:** Ready for Development

