# Epic AI-5: Database Models Impact Analysis

**Document Type:** Design Review  
**Epic:** AI-5 (Incremental Pattern Processing)  
**Created:** 2025-01-15  
**Status:** Design Review - No Implementation

---

## Executive Summary

### Question
How does the incremental processing architecture (Epic AI-5) affect the existing SQLite database models in `ai_automation.db`?

### Answer
**Minimal impact - existing models remain largely unchanged.** The incremental architecture stores aggregates in **InfluxDB** (new), while **SQLite** continues to store high-level pattern summaries and suggestions (Layer 4). This maintains backward compatibility with existing APIs and frontend.

### Key Findings
✅ **No breaking changes** to existing models  
✅ **Backward compatible** with current system  
⚠️ **Optional enhancements** recommended for better tracking  
📊 **InfluxDB handles aggregates**, SQLite handles summaries

---

## Current SQLite Models (Layer 4)

### Models in `ai_automation.db`

```python
# Epic AI-1: Pattern Detection
- Pattern              # High-level pattern summaries
- Suggestion           # Automation suggestions
- UserFeedback         # User feedback on suggestions
- AutomationVersion    # Rollback history

# Epic AI-2: Device Intelligence
- DeviceCapability     # Device model capabilities
- DeviceFeatureUsage   # Feature usage tracking

# Epic AI-3: Synergy Detection
- SynergyOpportunity   # Cross-device synergies

# Ask AI Feature
- AskAIQuery           # Natural language queries
```

---

## Impact Analysis by Model

### ✅ Pattern Model - **NO CHANGES REQUIRED**

**Current Schema:**
```python
class Pattern(Base):
    id = Column(Integer, primary_key=True)
    pattern_type = Column(String, nullable=False)  # 'time_of_day', 'co_occurrence', etc.
    device_id = Column(String, nullable=False)
    pattern_metadata = Column(JSON)
    confidence = Column(Float, nullable=False)
    occurrences = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Impact:**
- ✅ **No changes needed** - continues to store high-level pattern summaries
- ✅ **Same data flow** - detectors still write pattern summaries here
- ✅ **Backward compatible** - existing queries work unchanged

**Why No Changes:**
- Pattern summaries are **Layer 4** (UI/API layer)
- Daily aggregates go to **InfluxDB Layer 2** (new)
- These serve different purposes:
  - **SQLite Pattern**: "This device has a time-of-day pattern" (summary)
  - **InfluxDB Aggregate**: "On 2025-01-15, device had 12 events at hour 19" (detail)

**Optional Enhancement:**
```python
# OPTIONAL: Add field to track aggregate source
class Pattern(Base):
    # ... existing fields ...
    aggregate_date_range = Column(String, nullable=True)  # "2024-12-15 to 2025-01-15"
    aggregate_source = Column(String, default='daily')     # 'daily', 'weekly', 'monthly'
```

**Recommendation:** ✅ **Keep as-is** - no changes needed

---

### ✅ Suggestion Model - **NO CHANGES REQUIRED**

**Current Schema:**
```python
class Suggestion(Base):
    id = Column(Integer, primary_key=True)
    pattern_id = Column(Integer, ForeignKey('patterns.id'), nullable=True)
    description_only = Column(Text, nullable=False)
    automation_yaml = Column(Text, nullable=True)
    status = Column(String, default='draft')
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    # ... more fields ...
```

**Impact:**
- ✅ **No changes needed** - suggestions still generated from patterns
- ✅ **Same workflow** - pattern → suggestion → deployment
- ✅ **Backward compatible** - frontend unchanged

**Why No Changes:**
- Suggestions are **Layer 4** (UI/API layer)
- Generated from pattern summaries (not aggregates)
- User-facing data structure remains stable

**Recommendation:** ✅ **Keep as-is** - no changes needed

---

### ✅ UserFeedback Model - **NO CHANGES REQUIRED**

**Current Schema:**
```python
class UserFeedback(Base):
    id = Column(Integer, primary_key=True)
    suggestion_id = Column(Integer, ForeignKey('suggestions.id'))
    action = Column(String, nullable=False)
    feedback_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Impact:**
- ✅ **No changes needed** - feedback tied to suggestions, not aggregates
- ✅ **Backward compatible**

**Recommendation:** ✅ **Keep as-is** - no changes needed

---

### ✅ AutomationVersion Model - **NO CHANGES REQUIRED**

**Current Schema:**
```python
class AutomationVersion(Base):
    id = Column(Integer, primary_key=True)
    automation_id = Column(String(100), nullable=False, index=True)
    yaml_content = Column(Text, nullable=False)
    deployed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    safety_score = Column(Integer, nullable=False)
```

**Impact:**
- ✅ **No changes needed** - rollback history independent of processing architecture
- ✅ **Backward compatible**

**Recommendation:** ✅ **Keep as-is** - no changes needed

---

### ✅ DeviceCapability Model - **NO CHANGES REQUIRED**

**Current Schema:**
```python
class DeviceCapability(Base):
    device_model = Column(String, primary_key=True)
    manufacturer = Column(String, nullable=False)
    capabilities = Column(JSON, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Impact:**
- ✅ **No changes needed** - device capabilities independent of pattern processing
- ✅ **Backward compatible**

**Recommendation:** ✅ **Keep as-is** - no changes needed

---

### ✅ DeviceFeatureUsage Model - **NO CHANGES REQUIRED**

**Current Schema:**
```python
class DeviceFeatureUsage(Base):
    device_id = Column(String, primary_key=True)
    feature_name = Column(String, primary_key=True)
    configured = Column(Boolean, default=False, nullable=False)
    discovered_date = Column(DateTime, default=datetime.utcnow)
```

**Impact:**
- ✅ **No changes needed** - feature usage tracking independent of pattern processing
- ✅ **Backward compatible**

**Recommendation:** ✅ **Keep as-is** - no changes needed

---

### ✅ SynergyOpportunity Model - **NO CHANGES REQUIRED**

**Current Schema:**
```python
class SynergyOpportunity(Base):
    id = Column(Integer, primary_key=True)
    synergy_id = Column(String(36), unique=True, nullable=False)
    synergy_type = Column(String(50), nullable=False)
    device_ids = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

**Impact:**
- ✅ **No changes needed** - synergy detection independent of processing architecture
- ✅ **Backward compatible**

**Recommendation:** ✅ **Keep as-is** - no changes needed

---

### ✅ AskAIQuery Model - **NO CHANGES REQUIRED**

**Current Schema:**
```python
class AskAIQuery(Base):
    query_id = Column(String, primary_key=True)
    original_query = Column(Text, nullable=False)
    extracted_entities = Column(JSON, nullable=True)
    suggestions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Impact:**
- ✅ **No changes needed** - Ask AI queries independent of pattern processing
- ✅ **Backward compatible**

**Recommendation:** ✅ **Keep as-is** - no changes needed

---

## New Models (InfluxDB - Not SQLite)

### ⚠️ Important: Aggregates NOT in SQLite

The incremental architecture adds **InfluxDB measurements** (not SQLite tables):

```
InfluxDB Bucket: pattern_aggregates_daily
Measurements:
  - time_based_daily
  - co_occurrence_daily
  - sequence_daily
  - room_based_daily
  - duration_daily
  - anomaly_daily

InfluxDB Bucket: pattern_aggregates_weekly
Measurements:
  - session_weekly
  - day_type_weekly
  - contextual_monthly
  - seasonal_monthly
```

**These are NOT SQLite models** - they're handled by `PatternAggregateClient` (new) using InfluxDB Python client.

---

## Optional Enhancements (Not Required)

### Enhancement 1: Add Processing Metadata to Pattern

**Purpose:** Track which aggregates contributed to pattern detection

```python
class Pattern(Base):
    # ... existing fields ...
    
    # NEW: Optional tracking fields
    aggregate_date_range = Column(String, nullable=True)
    # Example: "2024-12-15 to 2025-01-15"
    
    aggregate_source = Column(String, default='daily')
    # Values: 'daily', 'weekly', 'monthly'
    
    aggregate_count = Column(Integer, nullable=True)
    # Number of daily aggregates used in detection
```

**Benefits:**
- Better debugging ("which aggregates created this pattern?")
- Audit trail for pattern detection
- Helps validate accuracy

**Drawbacks:**
- Adds complexity
- Not needed for single-home system
- Can query InfluxDB directly if needed

**Recommendation:** ⚠️ **Skip for now** - add only if debugging issues

---

### Enhancement 2: Add Aggregate Cache Table (SQLite)

**Purpose:** Cache frequently-queried aggregates in SQLite

```python
class AggregateCache(Base):
    """
    Optional: Cache frequently-accessed aggregates in SQLite
    for faster queries without hitting InfluxDB.
    """
    __tablename__ = 'aggregate_cache'
    
    id = Column(Integer, primary_key=True)
    detector_type = Column(String, nullable=False)  # 'time_based', 'co_occurrence', etc.
    entity_id = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    aggregate_data = Column(JSON, nullable=False)
    cached_at = Column(DateTime, default=datetime.utcnow)
    
    # Composite index for fast lookups
    __table_args__ = (
        Index('idx_cache_lookup', 'detector_type', 'entity_id', 'date'),
    )
```

**Benefits:**
- Faster queries (SQLite vs InfluxDB)
- Reduces InfluxDB load
- Useful for frequently-accessed data

**Drawbacks:**
- Data duplication (InfluxDB + SQLite)
- Cache invalidation complexity
- More storage required
- Probably overkill for single-home

**Recommendation:** ❌ **Don't add** - unnecessary for single-home system

---

### Enhancement 3: Add Processing Job Tracking

**Purpose:** Track daily/weekly/monthly batch job execution

```python
class ProcessingJob(Base):
    """
    Track batch job execution for monitoring and debugging.
    """
    __tablename__ = 'processing_jobs'
    
    id = Column(Integer, primary_key=True)
    job_type = Column(String, nullable=False)  # 'daily', 'weekly', 'monthly'
    processing_date = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False)  # 'running', 'completed', 'failed'
    events_processed = Column(Integer, nullable=True)
    patterns_detected = Column(Integer, nullable=True)
    aggregates_stored = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_job_date', 'processing_date', 'job_type'),
    )
```

**Benefits:**
- Better monitoring
- Debugging failed jobs
- Performance tracking over time
- Useful for production systems

**Drawbacks:**
- Adds complexity
- More storage
- Need cleanup policy

**Recommendation:** ⚠️ **Consider for Phase 2** - useful but not critical for initial implementation

---

## Data Flow Comparison

### Current System (Before Epic AI-5)
```
InfluxDB (Raw Events)
    ↓
Daily Batch Job (processes 30 days)
    ↓
SQLite Pattern Table (summaries)
    ↓
SQLite Suggestion Table
    ↓
Frontend
```

### New System (After Epic AI-5)
```
InfluxDB Layer 1 (Raw Events, 7 days)
    ↓
Daily Batch Job (processes 24h)
    ↓
InfluxDB Layer 2 (Daily Aggregates, 90 days) ← NEW
    ↓
SQLite Pattern Table (summaries) ← UNCHANGED
    ↓
SQLite Suggestion Table ← UNCHANGED
    ↓
Frontend ← UNCHANGED
```

**Key Point:** SQLite models unchanged - new InfluxDB layer inserted **before** pattern detection, not after.

---

## Migration Impact

### Database Migration Required?
**NO** - No SQLite schema changes needed

### Alembic Migration Needed?
**NO** - Existing schema works as-is

### Data Migration Required?
**NO** - Existing patterns/suggestions remain valid

### Backward Compatibility?
**YES** - 100% backward compatible

---

## Recommendations Summary

### Required Changes
**NONE** - All existing SQLite models work unchanged

### Optional Enhancements
1. ❌ **Skip**: Aggregate cache table (unnecessary for single-home)
2. ⚠️ **Maybe**: Processing job tracking (useful for monitoring)
3. ⚠️ **Maybe**: Pattern aggregate metadata (useful for debugging)

### Implementation Priority
1. **Phase 1 (Epic AI-5)**: No SQLite model changes
2. **Phase 2 (Future)**: Consider job tracking if monitoring needed
3. **Phase 3 (Future)**: Consider pattern metadata if debugging issues

---

## Testing Implications

### Model Testing
- ✅ **No new tests needed** for existing models
- ✅ **Existing tests remain valid**
- ✅ **No migration tests needed**

### Integration Testing
- ✅ Test pattern detection with new aggregates
- ✅ Verify patterns still stored correctly
- ✅ Verify suggestions still generated correctly
- ✅ Verify frontend still works

---

## API Compatibility

### REST API Endpoints
**All existing endpoints remain unchanged:**
- `GET /api/patterns/list` ✅
- `GET /api/suggestions/list` ✅
- `POST /api/suggestions/generate` ✅
- `POST /api/deploy/{id}` ✅

### Response Formats
**All response formats unchanged:**
- Pattern JSON structure ✅
- Suggestion JSON structure ✅
- Backward compatible ✅

---

## Frontend Compatibility

### UI Components
**All frontend components work unchanged:**
- Patterns Tab ✅
- Suggestions Tab ✅
- Automations Tab ✅
- No UI changes needed ✅

---

## Conclusion

### Summary
The incremental processing architecture (Epic AI-5) has **minimal impact on SQLite database models**. All existing models remain unchanged and fully backward compatible.

### Key Decisions
1. ✅ **Keep all SQLite models as-is**
2. ✅ **Store aggregates in InfluxDB** (new layer)
3. ✅ **Maintain backward compatibility**
4. ⚠️ **Consider optional enhancements in Phase 2**

### Action Items
- [ ] **No immediate action required** for SQLite models
- [ ] Review optional enhancements after Phase 1 complete
- [ ] Monitor system performance to determine if enhancements needed

### Risk Assessment
**Risk Level:** ✅ **LOW**
- No breaking changes
- Backward compatible
- Existing functionality preserved
- Optional enhancements can be added later if needed

---

## Appendix: Model Comparison Table

| Model | Current Use | Impact | Changes Needed | Priority |
|-------|-------------|--------|----------------|----------|
| Pattern | Pattern summaries | None | None | N/A |
| Suggestion | Automation suggestions | None | None | N/A |
| UserFeedback | User feedback | None | None | N/A |
| AutomationVersion | Rollback history | None | None | N/A |
| DeviceCapability | Device capabilities | None | None | N/A |
| DeviceFeatureUsage | Feature tracking | None | None | N/A |
| SynergyOpportunity | Synergy detection | None | None | N/A |
| AskAIQuery | NL queries | None | None | N/A |

**Summary:** 8 models, 0 changes required, 100% backward compatible

---

**Document Status:** Complete  
**Reviewed By:** [Pending]  
**Approved By:** [Pending]  
**Last Updated:** 2025-01-15

