# Epic AI-5: Incremental Pattern Processing Architecture

**Epic ID:** Epic-AI-5  
**Epic Goal:** Convert existing daily batch pattern detection from full 30-day reprocessing to incremental daily processing with multi-layer aggregation storage  
**Type:** Technical Optimization & Refactoring  
**Phase:** Performance Optimization  
**Timeline:** 3-4 weeks  
**Total Effort:** 80-100 hours

---

## Executive Summary

### Current Problem
The AI Automation Service currently processes **30 days of historical data (3M events) every single day**, reprocessing the same 29 days repeatedly. This results in:
- 30x redundant processing daily
- 2-4 minute processing time that could be 30 seconds
- High memory usage (200-400MB)
- Poor scalability as data grows

### Proposed Solution
Implement a **multi-layer incremental processing architecture** where:
- Process only **24 hours of new data daily** (100K events)
- Store **daily aggregates** in InfluxDB for historical queries
- Each detector queries its **optimal time window** from pre-aggregated data
- Reduce processing time by **30x** and storage by **80%**

### Business Value
- **Performance**: 30x faster daily processing (4 min → 30 sec)
- **Scalability**: Linear growth instead of exponential
- **Storage**: 80% reduction in storage requirements
- **Reliability**: Better system stability with lower resource usage
- **Maintainability**: Cleaner architecture with separation of concerns

---

## Architecture Overview

### Current Architecture (Inefficient)
```
Daily Batch (3 AM):
├── Fetch 30 days of raw events (3M events)
├── Process all 10 detectors on 3M events (2-4 min)
├── Store pattern summaries to SQLite
└── Discard all processed data
    └── Next day: Repeat for same 29 days + 1 new day ❌
```

### Proposed Architecture (Optimized)
```
Multi-Layer Storage:
├── Layer 1: Raw Events (InfluxDB, 7 days, 700K events)
├── Layer 2: Daily Aggregates (InfluxDB, 90 days, 900 records)
├── Layer 3: Weekly Aggregates (InfluxDB, 52 weeks, 520 records)
└── Layer 4: Pattern Summaries (SQLite, forever, ~1K records)

Daily Batch (3 AM):
├── Fetch ONLY last 24h raw events (100K events)
├── Process Group A detectors (4 min)
├── Store daily aggregates to Layer 2
├── Store pattern summaries to Layer 4
└── Historical queries use pre-aggregated layers ✅

Weekly Batch (Sunday 3 AM):
├── Query Layer 2 (last 7 days of aggregates)
├── Process Group B detectors (3 min)
└── Store weekly aggregates to Layer 3

Monthly Batch (1st of month 3 AM):
├── Query Layer 2/3 (aggregates)
├── Process Group C detectors (8 min)
└── Store monthly aggregates to Layer 3
```

---

## Detector Grouping Strategy

### Group A: Daily Incremental (Process 24h data)
- **Time-based Patterns** - Hourly activity patterns
- **Co-occurrence Patterns** - Device pair analysis
- **Sequence Patterns** - Multi-step behaviors
- **Room-based Patterns** - Spatial activity
- **Duration Patterns** - Usage duration analysis
- **Anomaly Patterns** - Unusual behavior detection

**Processing**: Daily on 100K events → Store to Layer 2

### Group B: Weekly Aggregated (Process 7d aggregates)
- **Session Patterns** - User routine analysis
- **Day-type Patterns** - Weekday vs weekend

**Processing**: Weekly on Layer 2 data → Store to Layer 3

### Group C: Monthly Contextual (Process 30d+ aggregates)
- **Contextual Patterns** - Weather/presence correlation
- **Seasonal Patterns** - Long-term seasonal trends

**Processing**: Monthly on Layer 2/3 data → Store to Layer 3

---

## Story List

| Story | Title | Effort | Priority | Dependencies |
|-------|-------|--------|----------|--------------|
| **AI5.1** | Multi-Layer Storage Design & Schema | 6-8h | Critical | None |
| **AI5.2** | InfluxDB Daily Aggregates Implementation | 10-12h | Critical | AI5.1 |
| **AI5.3** | Convert Group A Detectors to Incremental | 12-16h | Critical | AI5.2 |
| **AI5.4** | Daily Batch Job Refactoring | 8-10h | Critical | AI5.3 |
| **AI5.5** | Weekly Aggregation Layer Implementation | 8-10h | High | AI5.2 |
| **AI5.6** | Convert Group B Detectors to Weekly | 8-10h | High | AI5.5 |
| **AI5.7** | Monthly Aggregation Layer Implementation | 6-8h | Medium | AI5.5 |
| **AI5.8** | Convert Group C Detectors to Monthly | 6-8h | Medium | AI5.7 |
| **AI5.9** | Data Retention Policies & Cleanup | 4-6h | High | AI5.2 |
| **AI5.10** | Performance Testing & Validation | 8-10h | Critical | AI5.4, AI5.6, AI5.8 |
| **AI5.11** | Migration Script & Backward Compatibility | 4-6h | High | AI5.10 |

**Total Stories:** 11  
**Total Effort:** 80-104 hours

---

## Critical Path

```
Foundation Path:
AI5.1 → AI5.2 → AI5.3 → AI5.4 → AI5.10

Weekly Path:
AI5.2 → AI5.5 → AI5.6 → AI5.10

Monthly Path:
AI5.5 → AI5.7 → AI5.8 → AI5.10

Cleanup Path:
AI5.9 → AI5.11
```

**Timeline:** 3-4 weeks with sequential execution

---

## Implementation Sequence

### Week 1: Foundation & Daily Processing (26-36 hours)
- **AI5.1:** Design multi-layer storage schema (6-8h)
- **AI5.2:** Implement InfluxDB daily aggregates (10-12h)
- **AI5.3:** Convert Group A detectors (12-16h)

**Deliverable:** Daily incremental processing working for Group A

### Week 2: Daily Batch Refactoring (16-20 hours)
- **AI5.4:** Refactor daily batch job (8-10h)
- **AI5.9:** Implement data retention policies (4-6h)
- **AI5.10:** Begin performance testing (4h)

**Deliverable:** Complete daily processing pipeline operational

### Week 3: Weekly & Monthly Processing (28-36 hours)
- **AI5.5:** Weekly aggregation layer (8-10h)
- **AI5.6:** Convert Group B detectors (8-10h)
- **AI5.7:** Monthly aggregation layer (6-8h)
- **AI5.8:** Convert Group C detectors (6-8h)

**Deliverable:** All three processing tiers operational

### Week 4: Testing & Migration (12-16 hours)
- **AI5.10:** Complete performance testing (4-6h)
- **AI5.11:** Migration script & compatibility (4-6h)
- Final validation and documentation (4h)

**Deliverable:** Production-ready optimized system

---

## Success Metrics

### Performance Targets
- **Daily Processing Time**: 2-4 min → 30-60 sec (4x improvement)
- **Memory Usage**: 200-400MB → 100-150MB (50% reduction)
- **Storage Requirements**: 3M events → 700K events (77% reduction)
- **Query Performance**: 2-5 sec → 100-500ms (10x improvement)

### Validation Criteria
- ✅ All existing patterns still detected with same accuracy
- ✅ No data loss during migration
- ✅ Backward compatible with existing APIs
- ✅ Performance targets met or exceeded
- ✅ System stability maintained under load

---

## Technical Constraints

### Single-Home System Considerations
- **Resource Limits**: Runs on Raspberry Pi or similar edge device
- **Storage Constraints**: Limited disk space (32-128GB typical)
- **Memory Constraints**: 2-8GB RAM typical
- **Network**: Local network only, no cloud dependencies
- **Reliability**: Must handle power outages and restarts gracefully

### Design Principles for Single-Home
1. **Simplicity over Scalability**: Optimize for 1 home, not 1000 homes
2. **Resource Efficiency**: Minimize CPU, memory, and storage usage
3. **Local-First**: No external dependencies or cloud services
4. **Graceful Degradation**: System works even if some components fail
5. **Easy Recovery**: Simple backup and restore procedures

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Data loss during migration | High | Low | Comprehensive backup, phased rollout |
| Performance regression | Medium | Low | Extensive testing before deployment |
| InfluxDB storage growth | Medium | Medium | Retention policies, monitoring |
| Detector accuracy changes | High | Low | Validation against baseline patterns |

### Mitigation Strategies
1. **Phased Rollout**: Deploy Group A first, validate, then Groups B & C
2. **Backup Strategy**: Full backup before migration, rollback plan ready
3. **Monitoring**: Track performance metrics during and after migration
4. **Testing**: Comprehensive unit, integration, and performance tests

---

## Dependencies

### External Dependencies
- InfluxDB 2.x (already in use)
- SQLite (already in use)
- Python 3.11+ (already in use)
- Pandas, NumPy (already in use)

### Internal Dependencies
- Existing pattern detectors (AI1.4, AI1.5, AI1.6, etc.)
- Daily batch scheduler (AI1.9)
- Data API client (AI1.3)
- Database models (AI1.2)

---

## Backward Compatibility

### API Compatibility
- ✅ All existing REST API endpoints remain unchanged
- ✅ Pattern summary format in SQLite unchanged
- ✅ MQTT event publishing unchanged
- ✅ Frontend continues to work without changes

### Data Compatibility
- ✅ Existing pattern summaries preserved
- ✅ Historical data accessible via migration script
- ✅ Gradual transition with fallback to old system

---

## Documentation Requirements

### Technical Documentation
- [ ] Multi-layer storage architecture diagram
- [ ] InfluxDB schema documentation
- [ ] Detector conversion guide
- [ ] Performance benchmarking results
- [ ] Migration runbook

### User Documentation
- [ ] No user-facing changes (transparent optimization)
- [ ] System requirements update (if any)
- [ ] Troubleshooting guide updates

---

## Acceptance Criteria

### Epic-Level Acceptance
- ✅ Daily processing time reduced by at least 3x
- ✅ Storage usage reduced by at least 50%
- ✅ All 10 detector types operational with new architecture
- ✅ Pattern detection accuracy maintained (±5% variance acceptable)
- ✅ System stable for 7 days continuous operation
- ✅ Migration completed without data loss
- ✅ Backward compatible with existing integrations

---

## Future Enhancements (Out of Scope)

These are explicitly **NOT** included in this epic:
- Real-time pattern detection (remains batch-only)
- Additional detector types
- Cloud synchronization
- Multi-home support
- Advanced ML models
- Distributed processing

---

## References

- [Epic AI-1: Pattern Detection](./ai-automation/epic-ai1-summary.md)
- [Current Architecture](../../docs/architecture/architecture-device-intelligence.md)
- [InfluxDB Best Practices](https://docs.influxdata.com/influxdb/v2.7/write-data/best-practices/)
- [Time Series Optimization](https://www.timescale.com/blog/time-series-data-why-and-how-to-use-a-relational-database-instead-of-nosql/)

---

**Last Updated:** 2025-01-15  
**Status:** Draft - Ready for Review  
**Owner:** AI Automation Team

