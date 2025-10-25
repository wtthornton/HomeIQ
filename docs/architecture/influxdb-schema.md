# InfluxDB Schema Documentation

**Epic:** AI-5 (Incremental Pattern Processing)  
**Created:** 2025-01-15  
**Status:** Design Complete  
**Purpose:** Complete InfluxDB schema specifications for multi-layer storage architecture

---

## Schema Overview

The multi-layer storage architecture uses InfluxDB 2.x for time-series data storage across three layers:

- **Layer 1**: Raw events (7 days retention)
- **Layer 2**: Daily aggregates (90 days retention)  
- **Layer 3**: Weekly/Monthly aggregates (52 weeks retention)

Each layer is optimized for specific query patterns and retention requirements.

---

## Layer 1: Raw Events Schema

### Bucket Configuration
```yaml
Bucket Name: home_assistant_events
Retention Policy: 7 days (reduced from 30)
Organization: home_assistant
Purpose: Source of truth for recent data
Size Estimate: ~700K events (7 days × 100K/day)
```

### Measurement: home_assistant_events
```yaml
Measurement: home_assistant_events
Description: Raw Home Assistant events from websocket-ingestion
Source: websocket-ingestion service (Port 8001)
```

#### Tags (Indexed for Query Performance)
```yaml
entity_id:
  type: string
  description: Home Assistant entity identifier
  examples: ["light.living_room", "switch.kitchen", "sensor.temperature"]
  cardinality: ~100 (typical single home)
  query_usage: Primary filter for device-specific queries

device_id:
  type: string
  description: Device identifier from device registry
  examples: ["a1b2c3d4e5f6", "device_123"]
  cardinality: ~50 (typical single home)
  query_usage: Device-level aggregation

event_type:
  type: string
  description: Type of Home Assistant event
  values: ["state_changed", "device_registry_updated", "entity_registry_updated"]
  cardinality: ~10
  query_usage: Filter by event type

domain:
  type: string
  description: Home Assistant domain (extracted from entity_id)
  examples: ["light", "switch", "sensor", "binary_sensor"]
  cardinality: ~20
  query_usage: Domain-level aggregation

area_id:
  type: string
  description: Area identifier from Home Assistant
  examples: ["living_room", "kitchen", "bedroom", "outdoor"]
  cardinality: ~15 (typical single home)
  query_usage: Room-based pattern analysis
```

#### Fields (Values)
```yaml
state:
  type: string
  description: Current state of the entity
  examples: ["on", "off", "unavailable", "25.5"]
  nullable: false
  query_usage: State analysis and pattern detection

attr_friendly_name:
  type: string
  description: Human-readable name of the entity
  examples: ["Living Room Light", "Kitchen Switch", "Temperature Sensor"]
  nullable: true
  query_usage: UI display and debugging

attributes:
  type: JSON object
  description: Additional entity attributes
  schema:
    type: object
    properties:
      unit_of_measurement: string
      device_class: string
      icon: string
      # ... other Home Assistant attributes
  nullable: true
  query_usage: Advanced filtering and analysis
```

#### Example Data Point
```json
{
  "measurement": "home_assistant_events",
  "tags": {
    "entity_id": "light.living_room",
    "device_id": "a1b2c3d4e5f6",
    "event_type": "state_changed",
    "domain": "light",
    "area_id": "living_room"
  },
  "fields": {
    "state": "on",
    "attr_friendly_name": "Living Room Light",
    "attributes": {
      "unit_of_measurement": null,
      "device_class": null,
      "icon": "mdi:lightbulb"
    }
  },
  "timestamp": "2025-01-15T14:30:00Z"
}
```

---

## Layer 2: Daily Aggregates Schema

### Bucket Configuration
```yaml
Bucket Name: pattern_aggregates_daily
Retention Policy: 90 days
Organization: home_assistant
Purpose: Pre-computed daily patterns for historical queries
Size Estimate: ~9K records (90 days × 10 detectors × ~10/day)
```

### Measurement: time_based_daily
```yaml
Measurement: time_based_daily
Description: Daily time-based activity patterns
Detector: TimeOfDayPatternDetector
Processing: Daily @ 3 AM
```

#### Tags
```yaml
date:
  type: string
  format: YYYY-MM-DD
  description: Date of the aggregate
  examples: ["2025-01-15", "2025-01-16"]
  cardinality: 90 (retention period)
  query_usage: Time-based filtering

entity_id:
  type: string
  description: Entity identifier
  examples: ["light.living_room", "switch.kitchen"]
  cardinality: ~100
  query_usage: Device-specific queries

domain:
  type: string
  description: Home Assistant domain
  examples: ["light", "switch", "sensor"]
  cardinality: ~20
  query_usage: Domain-level aggregation
```

#### Fields
```yaml
hourly_distribution:
  type: JSON array[24]
  description: Activity count for each hour (0-23)
  schema:
    type: array
    items:
      type: number
      minimum: 0
    minItems: 24
    maxItems: 24
  example: [0, 0, 0, 0, 0, 2, 5, 8, 12, 15, 18, 20, 22, 25, 28, 30, 25, 20, 15, 10, 5, 2, 1, 0]
  query_usage: Hourly pattern analysis

peak_hours:
  type: JSON array
  description: Hours with highest activity
  schema:
    type: array
    items:
      type: integer
      minimum: 0
      maximum: 23
  example: [8, 9, 10, 14, 15, 16, 19, 20]
  query_usage: Peak activity identification

frequency:
  type: float
  description: Average events per hour
  range: [0.0, 100.0]
  example: 12.5
  query_usage: Activity level comparison

confidence:
  type: float
  description: Pattern confidence score
  range: [0.0, 1.0]
  example: 0.85
  query_usage: Pattern reliability assessment

occurrences:
  type: integer
  description: Total events in the day
  range: [0, 10000]
  example: 300
  query_usage: Activity volume analysis
```

### Measurement: co_occurrence_daily
```yaml
Measurement: co_occurrence_daily
Description: Daily co-occurrence patterns between device pairs
Detector: CoOccurrencePatternDetector
Processing: Daily @ 3 AM
```

#### Tags
```yaml
date:
  type: string
  format: YYYY-MM-DD
  description: Date of the aggregate

device_pair:
  type: string
  description: Sorted pair of device entity_ids
  format: "entity1|entity2"
  examples: ["light.living_room|switch.kitchen", "sensor.motion|light.hallway"]
  cardinality: ~500 (typical device pairs)
  query_usage: Device pair analysis
```

#### Fields
```yaml
co_occurrence_count:
  type: integer
  description: Number of co-occurrences in the day
  range: [0, 1000]
  example: 45
  query_usage: Co-occurrence frequency analysis

time_window_seconds:
  type: integer
  description: Time window for co-occurrence detection
  range: [1, 3600]
  example: 300
  query_usage: Temporal relationship analysis

confidence:
  type: float
  description: Co-occurrence confidence score
  range: [0.0, 1.0]
  example: 0.78
  query_usage: Relationship strength assessment

typical_hours:
  type: JSON array
  description: Hours when co-occurrence typically happens
  schema:
    type: array
    items:
      type: integer
      minimum: 0
      maximum: 23
  example: [7, 8, 9, 18, 19, 20]
  query_usage: Temporal pattern analysis
```

### Measurement: sequence_daily
```yaml
Measurement: sequence_daily
Description: Daily sequence patterns (multi-step behaviors)
Detector: SequencePatternDetector
Processing: Daily @ 3 AM
```

#### Tags
```yaml
date:
  type: string
  format: YYYY-MM-DD
  description: Date of the aggregate

sequence_id:
  type: string
  description: Hash of the device sequence
  format: "sha256_hash"
  examples: ["a1b2c3d4e5f6...", "f6e5d4c3b2a1..."]
  cardinality: ~200 (typical sequences)
  query_usage: Sequence identification
```

#### Fields
```yaml
sequence:
  type: JSON array
  description: Ordered list of entity_ids in the sequence
  schema:
    type: array
    items:
      type: string
  example: ["sensor.motion", "light.hallway", "light.living_room"]
  query_usage: Sequence pattern analysis

frequency:
  type: integer
  description: Number of times sequence occurred
  range: [0, 1000]
  example: 12
  query_usage: Sequence frequency analysis

avg_duration_seconds:
  type: float
  description: Average duration of the sequence
  range: [0.0, 3600.0]
  example: 45.5
  query_usage: Sequence timing analysis

confidence:
  type: float
  description: Sequence pattern confidence
  range: [0.0, 1.0]
  example: 0.92
  query_usage: Pattern reliability assessment
```

### Measurement: room_based_daily
```yaml
Measurement: room_based_daily
Description: Daily room-based activity patterns
Detector: RoomBasedPatternDetector
Processing: Daily @ 3 AM
```

#### Tags
```yaml
date:
  type: string
  format: YYYY-MM-DD
  description: Date of the aggregate

area_id:
  type: string
  description: Room/area identifier
  examples: ["living_room", "kitchen", "bedroom", "outdoor"]
  cardinality: ~15
  query_usage: Room-based analysis
```

#### Fields
```yaml
activity_level:
  type: float
  description: Overall activity level in the room
  range: [0.0, 100.0]
  example: 75.5
  query_usage: Room activity comparison

device_usage:
  type: JSON object
  description: Usage statistics per device in the room
  schema:
    type: object
    additionalProperties:
      type: object
      properties:
        count: integer
        duration_seconds: float
        peak_hour: integer
  example: {
    "light.living_room": {"count": 25, "duration_seconds": 1200.0, "peak_hour": 20},
    "switch.tv": {"count": 3, "duration_seconds": 300.0, "peak_hour": 19}
  }
  query_usage: Device usage analysis

transition_patterns:
  type: JSON array
  description: Common room-to-room transitions
  schema:
    type: array
    items:
      type: object
      properties:
        from_room: string
        to_room: string
        count: integer
        avg_duration: float
  example: [
    {"from_room": "kitchen", "to_room": "living_room", "count": 8, "avg_duration": 15.5},
    {"from_room": "living_room", "to_room": "bedroom", "count": 3, "avg_duration": 30.0}
  ]
  query_usage: Movement pattern analysis

peak_activity_hours:
  type: JSON array
  description: Hours with highest activity in the room
  schema:
    type: array
    items:
      type: integer
      minimum: 0
      maximum: 23
  example: [7, 8, 9, 18, 19, 20, 21]
  query_usage: Temporal activity analysis
```

### Measurement: duration_daily
```yaml
Measurement: duration_daily
Description: Daily duration patterns for device usage
Detector: DurationPatternDetector
Processing: Daily @ 3 AM
```

#### Tags
```yaml
date:
  type: string
  format: YYYY-MM-DD
  description: Date of the aggregate

entity_id:
  type: string
  description: Entity identifier
  examples: ["light.living_room", "switch.kitchen"]
  cardinality: ~100
  query_usage: Device-specific analysis
```

#### Fields
```yaml
avg_duration_seconds:
  type: float
  description: Average duration of device usage
  range: [0.0, 86400.0]
  example: 45.5
  query_usage: Duration trend analysis

min_duration_seconds:
  type: float
  description: Minimum duration observed
  range: [0.0, 86400.0]
  example: 2.0
  query_usage: Duration range analysis

max_duration_seconds:
  type: float
  description: Maximum duration observed
  range: [0.0, 86400.0]
  example: 180.0
  query_usage: Duration range analysis

duration_variance:
  type: float
  description: Variance in duration (consistency measure)
  range: [0.0, 10000.0]
  example: 125.5
  query_usage: Usage consistency analysis

efficiency_score:
  type: float
  description: Efficiency score based on usage patterns
  range: [0.0, 1.0]
  example: 0.78
  query_usage: Usage efficiency assessment
```

### Measurement: anomaly_daily
```yaml
Measurement: anomaly_daily
Description: Daily anomaly detection results
Detector: AnomalyPatternDetector
Processing: Daily @ 3 AM
```

#### Tags
```yaml
date:
  type: string
  format: YYYY-MM-DD
  description: Date of the aggregate

entity_id:
  type: string
  description: Entity identifier
  examples: ["light.living_room", "sensor.temperature"]
  cardinality: ~100
  query_usage: Device-specific anomaly analysis

anomaly_type:
  type: string
  description: Type of anomaly detected
  values: ["frequency", "timing", "duration", "sequence", "value"]
  cardinality: 5
  query_usage: Anomaly type filtering
```

#### Fields
```yaml
anomaly_score:
  type: float
  description: Anomaly severity score
  range: [0.0, 1.0]
  example: 0.85
  query_usage: Anomaly severity ranking

baseline_deviation:
  type: float
  description: Deviation from baseline pattern
  range: [0.0, 10.0]
  example: 2.5
  query_usage: Deviation magnitude analysis

occurrences:
  type: integer
  description: Number of anomalous events
  range: [0, 1000]
  example: 3
  query_usage: Anomaly frequency analysis

severity:
  type: string
  description: Human-readable severity level
  values: ["low", "medium", "high", "critical"]
  example: "high"
  query_usage: Severity-based filtering
```

---

## Layer 3: Weekly/Monthly Aggregates Schema

### Bucket Configuration
```yaml
Bucket Name: pattern_aggregates_weekly
Retention Policy: 52 weeks (1 year)
Organization: home_assistant
Purpose: Long-term trends and seasonal analysis
Size Estimate: ~1K records (52 weeks × 4 detectors × ~5/week)
```

### Measurement: session_weekly
```yaml
Measurement: session_weekly
Description: Weekly session patterns (user routines)
Detector: SessionPatternDetector
Processing: Weekly @ Sunday 3 AM
Source: Layer 2 daily aggregates
```

#### Tags
```yaml
week:
  type: string
  format: YYYY-W## (ISO week)
  description: Week identifier
  examples: ["2025-W03", "2025-W04"]
  cardinality: 52 (retention period)
  query_usage: Week-based filtering

session_type:
  type: string
  description: Type of user session
  values: ["morning_routine", "evening_routine", "work_session", "leisure", "sleep"]
  cardinality: 5
  query_usage: Session type analysis
```

#### Fields
```yaml
avg_session_duration:
  type: float
  description: Average session duration in minutes
  range: [0.0, 1440.0]
  example: 45.5
  query_usage: Session duration trends

session_count:
  type: integer
  description: Number of sessions in the week
  range: [0, 1000]
  example: 21
  query_usage: Session frequency analysis

typical_start_times:
  type: JSON array
  description: Common session start times
  schema:
    type: array
    items:
      type: string
      format: HH:MM
  example: ["07:30", "08:00", "18:30", "19:00"]
  query_usage: Routine timing analysis

devices_used:
  type: JSON array
  description: Devices commonly used in sessions
  schema:
    type: array
    items:
      type: string
  example: ["light.living_room", "switch.kitchen", "sensor.motion"]
  query_usage: Device usage in routines
```

### Measurement: day_type_weekly
```yaml
Measurement: day_type_weekly
Description: Weekly day-type patterns (weekday vs weekend)
Detector: DayTypePatternDetector
Processing: Weekly @ Sunday 3 AM
Source: Layer 2 daily aggregates
```

#### Tags
```yaml
week:
  type: string
  format: YYYY-W##
  description: Week identifier

day_type:
  type: string
  description: Type of day
  values: ["weekday", "weekend"]
  cardinality: 2
  query_usage: Day type comparison
```

#### Fields
```yaml
activity_patterns:
  type: JSON object
  description: Activity patterns by hour
  schema:
    type: object
    properties:
      hourly_activity:
        type: array
        items:
          type: number
          minimum: 0
        minItems: 24
        maxItems: 24
      peak_hours:
        type: array
        items:
          type: integer
          minimum: 0
          maximum: 23
  example: {
    "hourly_activity": [0, 0, 0, 0, 0, 2, 5, 8, 12, 15, 18, 20, 22, 25, 28, 30, 25, 20, 15, 10, 5, 2, 1, 0],
    "peak_hours": [8, 9, 10, 14, 15, 16, 19, 20]
  }
  query_usage: Day type pattern analysis

device_usage_diff:
  type: JSON object
  description: Difference in device usage between day types
  schema:
    type: object
    additionalProperties:
      type: object
      properties:
        usage_increase: float
        confidence: float
  example: {
    "light.living_room": {"usage_increase": 0.25, "confidence": 0.85},
    "switch.tv": {"usage_increase": -0.15, "confidence": 0.78}
  }
  query_usage: Day type device usage analysis

confidence:
  type: float
  description: Pattern confidence score
  range: [0.0, 1.0]
  example: 0.88
  query_usage: Pattern reliability assessment
```

### Measurement: contextual_monthly
```yaml
Measurement: contextual_monthly
Description: Monthly contextual patterns (weather/presence correlation)
Detector: ContextualPatternDetector
Processing: Monthly @ 1st 3 AM
Source: Layer 2/3 aggregates + external data
```

#### Tags
```yaml
month:
  type: string
  format: YYYY-MM
  description: Month identifier
  examples: ["2025-01", "2025-02"]
  cardinality: 12 (retention period)
  query_usage: Monthly trend analysis

weather_context:
  type: string
  description: Weather condition category
  values: ["sunny", "cloudy", "rainy", "snowy", "stormy"]
  cardinality: 5
  query_usage: Weather-based analysis

presence_context:
  type: string
  description: Presence pattern category
  values: ["home", "away", "partial", "overnight_away"]
  cardinality: 4
  query_usage: Presence-based analysis
```

#### Fields
```yaml
device_usage_patterns:
  type: JSON object
  description: Device usage patterns under this context
  schema:
    type: object
    additionalProperties:
      type: object
      properties:
        usage_level: float
        peak_hours: array
        correlation_strength: float
  example: {
    "light.living_room": {
      "usage_level": 0.75,
      "peak_hours": [18, 19, 20, 21],
      "correlation_strength": 0.82
    }
  }
  query_usage: Contextual device usage analysis

correlation_scores:
  type: JSON object
  description: Correlation scores between context and device usage
  schema:
    type: object
    additionalProperties:
      type: number
      minimum: -1.0
      maximum: 1.0
  example: {
    "weather_temperature": 0.65,
    "presence_duration": 0.78,
    "time_of_day": 0.92
  }
  query_usage: Context correlation analysis

confidence:
  type: float
  description: Contextual pattern confidence
  range: [0.0, 1.0]
  example: 0.85
  query_usage: Pattern reliability assessment
```

### Measurement: seasonal_monthly
```yaml
Measurement: seasonal_monthly
Description: Monthly seasonal patterns (long-term trends)
Detector: SeasonalPatternDetector
Processing: Monthly @ 1st 3 AM
Source: Layer 2/3 aggregates + historical data
```

#### Tags
```yaml
month:
  type: string
  format: YYYY-MM
  description: Month identifier

season:
  type: string
  description: Season identifier
  values: ["spring", "summer", "autumn", "winter"]
  cardinality: 4
  query_usage: Seasonal analysis
```

#### Fields
```yaml
seasonal_activity_level:
  type: float
  description: Overall activity level for the season
  range: [0.0, 100.0]
  example: 68.5
  query_usage: Seasonal activity comparison

year_over_year_comparison:
  type: JSON object
  description: Comparison with same month previous year
  schema:
    type: object
    properties:
      activity_change: float
      device_usage_changes: object
      trend_direction: string
  example: {
    "activity_change": 0.12,
    "device_usage_changes": {
      "light.living_room": 0.08,
      "switch.kitchen": -0.03
    },
    "trend_direction": "increasing"
  }
  query_usage: Year-over-year trend analysis

trend_direction:
  type: string
  description: Overall trend direction
  values: ["increasing", "decreasing", "stable", "variable"]
  example: "increasing"
  query_usage: Trend analysis
```

---

## Query Patterns and Examples

### Daily Pattern Queries

#### Time-based Pattern Analysis
```flux
// Get time-based patterns for a specific device over last 30 days
from(bucket: "pattern_aggregates_daily")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "time_based_daily")
  |> filter(fn: (r) => r.entity_id == "light.living_room")
  |> aggregateWindow(every: 1d, fn: mean)
  |> yield(name: "time_based_patterns")
```

#### Co-occurrence Analysis
```flux
// Find most frequent device co-occurrences
from(bucket: "pattern_aggregates_daily")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "co_occurrence_daily")
  |> group(columns: ["device_pair"])
  |> sum(column: "co_occurrence_count")
  |> sort(columns: ["_value"], desc: true)
  |> limit(n: 10)
  |> yield(name: "top_co_occurrences")
```

#### Room Activity Analysis
```flux
// Compare activity levels across rooms
from(bucket: "pattern_aggregates_daily")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "room_based_daily")
  |> group(columns: ["area_id"])
  |> mean(column: "activity_level")
  |> sort(columns: ["_value"], desc: true)
  |> yield(name: "room_activity_ranking")
```

### Cross-Layer Queries

#### Weekly Session Analysis
```flux
// Combine daily and weekly session data
daily_sessions = from(bucket: "pattern_aggregates_daily")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "session_daily")

weekly_sessions = from(bucket: "pattern_aggregates_weekly")
  |> range(start: -4w)
  |> filter(fn: (r) => r._measurement == "session_weekly")

union(tables: [daily_sessions, weekly_sessions])
  |> aggregateWindow(every: 1w, fn: mean)
  |> yield(name: "comprehensive_session_analysis")
```

#### Seasonal Trend Analysis
```flux
// Analyze seasonal patterns with monthly aggregates
from(bucket: "pattern_aggregates_weekly")
  |> range(start: -12M)
  |> filter(fn: (r) => r._measurement == "seasonal_monthly")
  |> group(columns: ["season"])
  |> mean(column: "seasonal_activity_level")
  |> yield(name: "seasonal_activity_trends")
```

### Performance Optimization Queries

#### Efficient Time Range Queries
```flux
// Optimized query with proper time filtering
from(bucket: "pattern_aggregates_daily")
  |> range(start: 2025-01-01T00:00:00Z, stop: 2025-01-31T23:59:59Z)
  |> filter(fn: (r) => r._measurement == "time_based_daily")
  |> filter(fn: (r) => r.entity_id =~ /^light\./)
  |> aggregateWindow(every: 1d, fn: mean)
  |> yield(name: "light_patterns_january")
```

#### Tag-based Filtering
```flux
// Efficient filtering using tags
from(bucket: "pattern_aggregates_daily")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "room_based_daily")
  |> filter(fn: (r) => r.area_id == "living_room")
  |> filter(fn: (r) => r.date >= "2025-01-01")
  |> group(columns: ["date"])
  |> mean(column: "activity_level")
  |> yield(name: "living_room_activity_trend")
```

---

## Indexing Strategy

### Primary Indexes
```yaml
Time Index:
  description: Primary time-based index
  fields: _time
  usage: Range queries, time-based filtering

Tag Indexes:
  entity_id: Device-specific queries
  date: Daily aggregate queries
  area_id: Room-based queries
  domain: Domain-level aggregation
  device_pair: Co-occurrence analysis
  sequence_id: Sequence pattern queries
  week: Weekly aggregate queries
  month: Monthly aggregate queries
  season: Seasonal analysis
```

### Query Optimization
```yaml
Best Practices:
  - Always use time range filters first
  - Filter by tags before fields
  - Use specific measurement names
  - Limit result sets with appropriate functions
  - Use aggregateWindow for time-based grouping
  - Prefer mean() over sum() for averages
  - Use group() for multi-dimensional analysis
```

---

## Data Validation

### Schema Validation Rules
```yaml
Required Fields:
  - All measurements must have _time field
  - All measurements must have appropriate tags
  - JSON fields must match defined schemas
  - Numeric fields must be within defined ranges

Data Quality Checks:
  - Tag cardinality within limits
  - Field values within valid ranges
  - JSON schema compliance
  - Timestamp validity
  - No duplicate data points
```

### Validation Queries
```flux
// Check for data quality issues
from(bucket: "pattern_aggregates_daily")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "time_based_daily")
  |> filter(fn: (r) => r.confidence < 0.0 or r.confidence > 1.0)
  |> yield(name: "invalid_confidence_scores")
```

---

## Migration Considerations

### Schema Evolution
```yaml
Backward Compatibility:
  - New fields can be added as optional
  - Existing fields cannot be removed
  - Tag changes require data migration
  - Measurement renames require application updates

Versioning Strategy:
  - Use measurement names for versioning
  - Maintain old measurements during transition
  - Gradual migration of queries
  - Deprecation timeline for old schemas
```

### Data Migration
```yaml
Migration Steps:
  1. Create new buckets with retention policies
  2. Update application to write to new schema
  3. Migrate historical data if needed
  4. Update queries to use new measurements
  5. Remove old measurements after validation
```

---

## Monitoring and Maintenance

### Storage Monitoring
```yaml
Key Metrics:
  - Bucket size growth rate
  - Retention policy effectiveness
  - Query performance trends
  - Tag cardinality growth
  - Data quality scores

Alerts:
  - Storage usage > 80% of limit
  - Query time > 5 seconds
  - Data quality score < 0.9
  - Retention policy failures
```

### Maintenance Tasks
```yaml
Daily:
  - Monitor storage usage
  - Check query performance
  - Validate data quality

Weekly:
  - Review retention policy effectiveness
  - Analyze query patterns
  - Check for schema drift

Monthly:
  - Review storage growth projections
  - Optimize slow queries
  - Update documentation
```

---

**Document Status:** Complete  
**Last Updated:** 2025-01-15  
**Ready for:** Implementation  
**Next:** Storage Estimates Documentation
