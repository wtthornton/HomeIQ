# ADR 002: Hybrid Database Architecture (InfluxDB + SQLite)

**Status:** Accepted  
**Date:** January 2025 (Epic 22)  
**Context:** Single-home deployment requiring both time-series and relational data  
**Deciders:** Architecture team

---

## Context

HomeIQ needs to store:
- **Time-series data:** Home Assistant events, metrics, sensor readings (millions of events)
- **Relational metadata:** Devices, entities, webhooks, automations (thousands of records)
- **Query patterns:** Both historical time-series queries and relational lookups

**Challenge:** Choose database architecture that optimizes for both use cases.

**Scale:** Single-home deployment, ~50-100 devices, ~1M events/year

---

## Decision

Use a **hybrid database architecture**:
- **InfluxDB 2.7** for time-series data (events, metrics, sports scores)
- **SQLite 3.45+** for relational metadata (devices, entities, webhooks)

---

## Rationale

### Why Hybrid?

1. **Performance:** 5-10x faster queries for device/entity lookups vs. InfluxDB alone
2. **Optimization:** Each database optimized for its use case
3. **Simplicity:** SQLite for metadata is simpler than InfluxDB tags/fields
4. **Cost:** SQLite is zero-cost, InfluxDB handles time-series efficiently

### Why Not Pure InfluxDB?

- Device/entity queries require complex tag filtering
- Relational queries (joins, aggregations) are inefficient
- Metadata updates require rewriting entire time-series points
- Query latency 5-10x slower for metadata lookups

### Why Not Pure SQLite?

- Time-series data grows unbounded (millions of events)
- SQLite performance degrades with large tables
- No built-in time-series optimizations (retention, downsampling)
- Would require manual time-series management

### Why Not PostgreSQL?

- Overkill for single-home deployment
- Higher resource requirements
- More complex deployment
- No time-series optimizations (would need TimescaleDB extension)

---

## Consequences

### Positive

- **Fast metadata queries:** 2-5ms for device/entity lookups (SQLite)
- **Efficient time-series storage:** Optimized for event storage (InfluxDB)
- **Simple deployment:** SQLite requires no setup, InfluxDB well-supported
- **Cost effective:** SQLite is free, InfluxDB handles scale efficiently
- **Clear separation:** Time-series vs. metadata concerns separated

### Negative

- **Two databases to manage:** Requires coordination
- **Data consistency:** Must keep metadata in sync with events
- **Complexity:** Two query languages (Flux + SQL)
- **Migration:** Moving data between databases requires ETL

### Neutral

- **Deployment:** Both databases run in Docker containers
- **Backup:** Separate backup strategies for each database
- **Monitoring:** Monitor both databases independently

---

## Implementation

### Data Flow

```
Home Assistant Events
    ↓
websocket-ingestion
    ├─→ InfluxDB (time-series events)
    └─→ SQLite (device/entity metadata updates)
```

### Query Patterns

**Time-series queries (InfluxDB):**
- Historical event queries
- Metrics aggregation
- Time-range filtering

**Metadata queries (SQLite):**
- Device lookups
- Entity information
- Webhook configuration
- Automation metadata

### Data API

The `data-api` service provides unified query interface:
- Routes time-series queries to InfluxDB
- Routes metadata queries to SQLite
- Abstracts database choice from consumers

---

## Alternatives Considered

### Option 1: Pure InfluxDB
- **Rejected:** Poor performance for metadata queries (5-10x slower)

### Option 2: Pure SQLite
- **Rejected:** Poor performance for large time-series datasets

### Option 3: PostgreSQL + TimescaleDB
- **Rejected:** Overkill for single-home deployment, higher resource requirements

### Option 4: InfluxDB + PostgreSQL
- **Rejected:** PostgreSQL unnecessary when SQLite suffices for metadata

---

## Validation

**Epic 22 Results:**
- ✅ 5-10x faster device/entity queries
- ✅ Efficient time-series storage
- ✅ Simple deployment
- ✅ No performance issues

**Current Status:** Production-proven, no issues reported

---

## Related Decisions

- [ADR 001: Hybrid Orchestration Pattern](001-hybrid-orchestration-pattern.md)
- [ADR 003: Epic 31 Architecture Simplification](003-epic-31-architecture-simplification.md)

---

**Last Updated:** December 3, 2025

