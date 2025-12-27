# Database Optimization Guide

**Last Updated:** November 24, 2025  
**Status:** Current Best Practices  
**Purpose:** Comprehensive guide for SQLite and InfluxDB optimization

---

## Overview

This document covers optimization strategies for both SQLite (relational metadata) and InfluxDB (time-series data) databases used in the HomeIQ system.

---

## SQLite Optimization

### Index Strategy

#### Foreign Key Indexes

All foreign key columns should have indexes to optimize JOIN operations:

```python
# Foreign key indexes (Database Optimization - 2025)
Index('idx_suggestions_pattern_id', Suggestion.pattern_id)
Index('idx_user_feedback_suggestion_id', UserFeedback.suggestion_id)
```

**Tables with foreign keys:**
- `suggestions.pattern_id` → `patterns.id`
- `user_feedback.suggestion_id` → `suggestions.id`
- `pattern_history.pattern_id` → `patterns.id`
- `clarification_sessions.original_query_id` → `ask_ai_queries.query_id`
- And others (see `services/ai-automation-service/src/database/models.py`)

#### Composite Indexes

Composite indexes optimize queries that filter by multiple columns or use WHERE + ORDER BY:

```python
# Composite indexes for common query patterns
Index('idx_suggestions_status_created', Suggestion.status, Suggestion.created_at.desc())
Index('idx_patterns_type_confidence', Pattern.pattern_type, Pattern.confidence.desc())
Index('idx_patterns_active_confidence', Pattern.deprecated, Pattern.confidence.desc())
```

**Common patterns:**
- `WHERE status = 'X' ORDER BY created_at DESC` → `idx_suggestions_status_created`
- `WHERE pattern_type = 'X' ORDER BY confidence DESC` → `idx_patterns_type_confidence`
- `WHERE deprecated = 0 ORDER BY confidence DESC` → `idx_patterns_active_confidence`

#### Partial Indexes

Partial indexes only index rows matching a WHERE clause, reducing index size and improving performance:

```sql
-- Active suggestions only
CREATE INDEX idx_suggestions_active_status_created 
ON suggestions(status, created_at DESC) 
WHERE status IN ('draft', 'refining');

-- Active patterns only
CREATE INDEX idx_patterns_active_type_device_confidence 
ON patterns(pattern_type, device_id, confidence DESC) 
WHERE deprecated = 0;
```

**Benefits:**
- Smaller index size (only indexes relevant rows)
- Faster queries on filtered data
- Less storage overhead

### Query Optimization

#### Best Practices

1. **Use EXPLAIN QUERY PLAN**
   ```sql
   EXPLAIN QUERY PLAN
   SELECT * FROM suggestions WHERE status = 'draft' ORDER BY created_at DESC;
   ```

2. **Filter Early**
   - Apply WHERE clauses before JOINs
   - Use indexed columns in WHERE clauses
   - Limit result sets with LIMIT

3. **Avoid N+1 Queries**
   - Use JOINs instead of multiple queries
   - Use `selectinload()` for eager loading in SQLAlchemy

4. **Use Prepared Statements**
   - SQLAlchemy uses prepared statements by default
   - Avoid string concatenation for queries

#### Common Query Patterns

**Pattern 1: Status Filtering with Date Sorting**
```python
# Optimized with composite index
query = select(Suggestion).where(
    Suggestion.status == 'draft'
).order_by(Suggestion.created_at.desc()).limit(10)
```

**Pattern 2: Pattern Type with Confidence**
```python
# Optimized with composite index
query = select(Pattern).where(
    Pattern.pattern_type == 'time_of_day'
).order_by(Pattern.confidence.desc()).limit(10)
```

**Pattern 3: Active Patterns Only**
```python
# Optimized with partial index
query = select(Pattern).where(
    Pattern.deprecated == False
).order_by(Pattern.confidence.desc())
```

### Database Maintenance

#### Regular Maintenance Tasks

1. **VACUUM** - Reclaim space from deleted rows
   ```sql
   VACUUM;
   ```
   - Run when `PRAGMA freelist_count > 100`
   - Monthly or when fragmentation > 10%

2. **ANALYZE** - Update query planner statistics
   ```sql
   ANALYZE;
   ```
   - Run after creating new indexes
   - Monthly or after significant data changes

3. **PRAGMA optimize** - SQLite 3.38+ automatic optimization
   ```sql
   PRAGMA optimize;
   ```
   - Run periodically (SQLite recommends after each connection)

#### Maintenance Script

Use `scripts/sqlite_maintenance.py` to:
- Check fragmentation (freelist_count)
- Run VACUUM if needed
- Run ANALYZE
- Run PRAGMA optimize

**Schedule:** Monthly or when fragmentation > 10%

### Performance Monitoring

#### Slow Query Detection

Monitor queries taking >1 second:
- Use `EXPLAIN QUERY PLAN` to identify missing indexes
- Check for full table scans
- Verify indexes are being used

#### Tools

- `scripts/monitor_query_performance.py` - Test common queries
- SQLite query planner: `EXPLAIN QUERY PLAN`
- SQLAlchemy query logging: Set `echo=True` in engine

---

## InfluxDB Optimization

### Tag vs Field Strategy

#### Tags (Indexed, for Filtering)

Use tags for:
- Low cardinality (<10,000 unique values)
- Values used in WHERE clauses
- Values used for grouping

**Current tags:**
- `entity_id` (~100 values) ✅
- `device_id` (~50 values) ✅
- `area_id` (~15 values) ✅
- `domain` (~20 values) ✅
- `event_type` (~10 values) ✅

#### Fields (Not Indexed, for Values)

Use fields for:
- High cardinality (>10,000 unique values)
- Numeric values (measurements)
- Values not used for filtering

**Current fields:**
- `state` (string values)
- `normalized_value` (numeric)
- `duration_in_state_seconds` (numeric)
- `attributes` (JSON)

### Query Optimization

#### Best Practices

1. **Filter by Time Range First**
   ```flux
   from(bucket: "home_assistant_events")
     |> range(start: -24h)  // Time filter first
     |> filter(fn: (r) => r._measurement == "home_assistant_events")
   ```

2. **Use Tag Filters (Indexed)**
   ```flux
   |> filter(fn: (r) => r.entity_id == "light.living_room")  // Tag filter
   |> filter(fn: (r) => r.device_id == "abc123")  // Tag filter
   ```

3. **Avoid Field Filters (Not Indexed)**
   ```flux
   // ❌ SLOW - Field filter (not indexed)
   |> filter(fn: (r) => r._field == "state" && r._value == "on")
   
   // ✅ FAST - Tag filter (indexed)
   |> filter(fn: (r) => r.entity_id == "light.living_room")
   ```

4. **Use Aggregate Functions Efficiently**
   ```flux
   |> aggregateWindow(every: 1h, fn: mean)  // Efficient aggregation
   |> group(columns: ["entity_id"])  // Group by tags
   ```

#### Common Query Patterns

**Pattern 1: Recent Events by Entity**
```flux
from(bucket: "home_assistant_events")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "home_assistant_events")
  |> filter(fn: (r) => r.entity_id == "light.living_room")
  |> limit(n: 100)
```

**Pattern 2: Hourly Aggregation**
```flux
from(bucket: "home_assistant_events")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "home_assistant_events")
  |> aggregateWindow(every: 1h, fn: count)
```

**Pattern 3: Device-Level Aggregation**
```flux
from(bucket: "home_assistant_events")
  |> range(start: -24h)
  |> filter(fn: (r) => r.device_id == "abc123")
  |> group(columns: ["entity_id"])
  |> count()
```

### Retention Policies

#### Current Configuration

- `home_assistant_events`: 365 days
- `weather_data`: 365 days

#### Retention Strategy

1. **Raw Events**: 7 days (hot tier)
2. **Hourly Aggregates**: 90 days (warm tier)
3. **Daily Aggregates**: 365 days (cold tier)

**Downsampling:**
- Hot → Warm: Daily at 2:00 AM (data >7 days old)
- Warm → Cold: Daily at 2:30 AM (data >90 days old)

See `services/data-retention/src/tiered_retention.py` for implementation.

### Shard Duration

#### Recommendations

Based on retention policy:
- **1-7 days retention**: 1h shard duration
- **7-30 days retention**: 24h shard duration
- **30+ days retention**: 7d shard duration (max recommended)

**Current:** 365 days retention → Recommended: 7d shard duration

**Configuration:**
- Use InfluxDB UI: Settings > Buckets > [bucket] > Shard Group Duration
- Or use InfluxDB API: `PATCH /api/v2/buckets/{bucket_id}`

**Note:** Changes only affect new data (existing shards unchanged)

### Tag Cardinality Monitoring

#### Thresholds

- **Warning**: >5,000 unique values
- **Critical**: >10,000 unique values (InfluxDB best practice limit)

#### Monitoring

Use `scripts/check_influxdb_quality.py` to monitor tag cardinality:
- Checks `entity_id`, `device_id`, `area_id`, `domain`, `event_type`
- Reports cardinality for each tag
- Warns if threshold exceeded

**Current Status:**
- `entity_id`: ~500 values ✅
- `device_id`: ~65 values ✅
- `area_id`: ~17 values ✅
- `domain`: ~20 values ✅
- `event_type`: ~1 value ✅

All tags are well within thresholds.

### Tag Completeness

#### Monitoring

Use `scripts/verify_influxdb_tags.py` to check tag completeness:
- Reports percentage of records with `device_id` and `area_id` tags
- Threshold: ≥95% completeness

**Current Status:**
- `device_id`: ~61% complete (last 24h) ⚠️
- `area_id`: ~42% complete (last 24h) ⚠️

**Recommendation:** Investigate event processing pipeline for missing tag population.

### Downsampling

#### Implementation

Downsampling is implemented in `services/data-retention/src/tiered_retention.py`:

**Hot to Warm (Raw → Hourly):**
- Schedule: Daily at 2:00 AM
- Process: Downsample data >7 days old
- Target: `hourly_aggregates` bucket

**Warm to Cold (Hourly → Daily):**
- Schedule: Daily at 2:30 AM
- Process: Downsample hourly data >90 days old
- Target: `daily_aggregates` bucket

**Benefits:**
- Reduces storage for old data
- Faster queries on historical data
- Maintains data for long-term analysis

---

## Performance Monitoring

### SQLite Monitoring

**Tools:**
- `scripts/monitor_query_performance.py` - Test common queries
- `EXPLAIN QUERY PLAN` - Analyze query execution
- SQLAlchemy query logging

**Thresholds:**
- Slow query: ≥1 second
- Check for missing indexes
- Verify query plan uses indexes

### InfluxDB Monitoring

**Tools:**
- `scripts/monitor_query_performance.py` - Test common queries
- `scripts/check_influxdb_quality.py` - Comprehensive quality check
- InfluxDB query profiler

**Thresholds:**
- Slow query: ≥5 seconds
- Check time range filters
- Verify tag filters are used
- Check retention policy

---

## Maintenance Schedule

### Daily
- Monitor query performance (automated)
- Check tag completeness (automated)

### Weekly
- Review slow query logs
- Check tag cardinality

### Monthly
- Run SQLite VACUUM/ANALYZE (if needed)
- Review index usage
- Analyze query patterns

### Quarterly
- Review retention policies
- Optimize shard duration (if needed)
- Review and update indexes

---

## Troubleshooting

### SQLite Issues

**Slow Queries:**
1. Run `EXPLAIN QUERY PLAN` to identify missing indexes
2. Check for full table scans
3. Verify composite indexes for WHERE + ORDER BY
4. Consider partial indexes for filtered queries

**High Fragmentation:**
1. Run `PRAGMA freelist_count` to check fragmentation
2. Run `VACUUM` if freelist_count > 100
3. Run `ANALYZE` after VACUUM

### InfluxDB Issues

**Slow Queries:**
1. Check time range (narrow if possible)
2. Verify tag filters are used (not field filters)
3. Check retention policy (old data may be slow)
4. Consider downsampling for historical queries

**High Tag Cardinality:**
1. Monitor with `check_influxdb_quality.py`
2. If >10,000 values, consider moving to fields
3. Implement tag value limits if needed

**Missing Tags:**
1. Check event processing pipeline
2. Verify `influxdb_schema.py` tag population logic
3. Review websocket-ingestion service logs

---

## References

- SQLite Query Planner: https://www.sqlite.org/queryplanner.html
- InfluxDB Best Practices: https://docs.influxdata.com/influxdb/v2.7/write-data/best-practices/
- InfluxDB Schema Design: https://docs.influxdata.com/influxdb/v2.7/write-data/best-practices/schema-design/

---

**Document Status:** Complete  
**Last Updated:** November 24, 2025  
**Maintained By:** Database Optimization Team

