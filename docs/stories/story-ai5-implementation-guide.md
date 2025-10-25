# Epic AI-5: Implementation Guide

**Quick Reference for Developers**

---

## Overview

This epic converts the AI Automation Service from processing 30 days of data daily to incremental processing with multi-layer aggregation storage.

**Key Change:** Process each day's data once, store aggregates, query aggregates for historical analysis.

---

## Before You Start

### Prerequisites
- [ ] Read Epic AI-5 document (`epic-ai5-incremental-pattern-processing.md`)
- [ ] Review current architecture (`docs/architecture/architecture-device-intelligence.md`)
- [ ] Understand InfluxDB basics
- [ ] Familiar with pattern detectors in `src/pattern_detection/`

### Development Environment
```bash
# Ensure InfluxDB 2.x running
docker-compose up -d influxdb

# Install dependencies
cd services/ai-automation-service
pip install -r requirements.txt

# Run tests
pytest tests/
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

#### Step 1: Design Storage Schema (AI5.1)
**Files to create:**
- `docs/architecture/multi-layer-storage.md`
- `docs/architecture/influxdb-schema.md`

**Key Decisions:**
- InfluxDB bucket names
- Tag structure for each detector
- Field structure for metrics
- Retention policies

**Deliverable:** Complete schema documentation

---

#### Step 2: Implement InfluxDB Client (AI5.2)
**Files to create:**
- `src/clients/pattern_aggregate_client.py`
- `src/models/pattern_aggregates.py`
- `tests/test_pattern_aggregate_client.py`

**Key Code:**
```python
# src/clients/pattern_aggregate_client.py
class PatternAggregateClient:
    def __init__(self, url, token, org, bucket="pattern_aggregates_daily"):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
    
    def write_time_based_daily(self, date, entity_id, ...):
        point = Point("time_based_daily") \
            .tag("date", date.strftime("%Y-%m-%d")) \
            .tag("entity_id", entity_id) \
            .field("frequency", frequency) \
            .time(date, WritePrecision.S)
        self.write_api.write(bucket=self.bucket, record=point)
    
    def query_time_based_daily(self, start_date, end_date, entity_id=None):
        flux_query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start_date.isoformat()})
              |> filter(fn: (r) => r._measurement == "time_based_daily")
        '''
        return self._execute_query(flux_query)
```

**Testing:**
```bash
pytest tests/test_pattern_aggregate_client.py -v
```

**Deliverable:** Working InfluxDB client with tests

---

#### Step 3: Convert Group A Detectors (AI5.3)
**Files to modify:**
- `src/pattern_detection/time_of_day.py`
- `src/pattern_detection/co_occurrence.py`
- `src/pattern_detection/sequence_detector.py`
- `src/pattern_detection/room_based_detector.py`
- `src/pattern_detection/duration_detector.py`
- `src/pattern_detection/ml_pattern_detector.py` (base class)

**Key Changes:**

**Before (current):**
```python
class TimeOfDayPatternDetector:
    def detect_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        # Process all 30 days of events
        patterns = []
        for device in events_df['entity_id'].unique():
            device_events = events_df[events_df['entity_id'] == device]
            # Analyze 30 days of data
            pattern = self._analyze_device(device_events)
            patterns.append(pattern)
        return patterns
```

**After (incremental):**
```python
class TimeOfDayPatternDetector:
    def __init__(self, aggregate_client: PatternAggregateClient = None):
        self.aggregate_client = aggregate_client
    
    def detect_patterns(
        self, 
        events_df: pd.DataFrame,
        processing_date: datetime
    ) -> List[Dict]:
        """Process ONLY 24h of events, store daily aggregates."""
        patterns = []
        daily_aggregates = []
        
        for device in events_df['entity_id'].unique():
            device_events = events_df[events_df['entity_id'] == device]
            
            # Analyze 24h of data
            hourly_dist = self._compute_hourly_distribution(device_events)
            peak_hours = self._find_peak_hours(hourly_dist)
            frequency = self._compute_frequency(device_events)
            
            # Store daily aggregate
            if self.aggregate_client:
                self.aggregate_client.write_time_based_daily(
                    date=processing_date,
                    entity_id=device,
                    domain=device.split('.')[0],
                    hourly_distribution=hourly_dist,
                    peak_hours=peak_hours,
                    frequency=frequency,
                    confidence=0.85,
                    occurrences=len(device_events)
                )
            
            # Query historical aggregates for pattern detection
            if self.aggregate_client:
                historical = self.aggregate_client.query_time_based_daily(
                    start_date=processing_date - timedelta(days=30),
                    end_date=processing_date,
                    entity_id=device
                )
                
                # Detect pattern from 30 days of aggregates
                if self._is_consistent_pattern(historical):
                    pattern = self._create_pattern(device, historical)
                    patterns.append(pattern)
        
        return patterns
```

**Key Points:**
1. Accept `processing_date` parameter (the date being processed)
2. Process only 24h of events
3. Compute daily metrics
4. Store daily aggregate via `aggregate_client`
5. Query historical aggregates for pattern detection
6. Return patterns based on aggregate analysis

**Testing:**
```bash
# Test with 24h data
pytest tests/test_time_of_day_detector.py::test_incremental_processing -v

# Test aggregate storage
pytest tests/test_time_of_day_detector.py::test_stores_daily_aggregate -v

# Test historical query
pytest tests/test_time_of_day_detector.py::test_queries_historical_data -v
```

**Deliverable:** All 6 Group A detectors converted and tested

---

### Phase 2: Daily Batch Refactoring (Week 2)

#### Step 4: Refactor Daily Batch Job (AI5.4)
**Files to modify:**
- `src/scheduler/daily_analysis.py`

**Key Changes:**

**Before (current):**
```python
async def run_daily_analysis(self):
    # Fetch 30 days
    start_date = datetime.now(timezone.utc) - timedelta(days=30)
    events_df = await data_client.fetch_events(
        start_time=start_date,
        limit=100000
    )
    
    # Run detectors on 30 days
    tod_patterns = tod_detector.detect_patterns(events_df)
    co_patterns = co_detector.detect_patterns(events_df)
    # ... more detectors
```

**After (incremental):**
```python
async def run_daily_analysis(self):
    # Initialize aggregate client
    aggregate_client = PatternAggregateClient(
        url=settings.influxdb_url,
        token=settings.influxdb_token,
        org=settings.influxdb_org
    )
    
    # Fetch ONLY last 24h
    processing_date = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=1)  # Yesterday
    
    events_df = await data_client.fetch_events(
        start_time=processing_date,
        end_time=processing_date + timedelta(days=1),
        limit=100000
    )
    
    logger.info(f"Processing {len(events_df)} events for {processing_date.date()}")
    
    # Run detectors with aggregate client
    tod_detector = TimeOfDayPatternDetector(aggregate_client=aggregate_client)
    tod_patterns = tod_detector.detect_patterns(events_df, processing_date)
    
    co_detector = CoOccurrencePatternDetector(aggregate_client=aggregate_client)
    co_patterns = co_detector.detect_patterns(events_df, processing_date)
    
    # ... more detectors
    
    # Store pattern summaries to SQLite (unchanged)
    if all_patterns:
        async with get_db_session() as db:
            await store_patterns(db, all_patterns)
```

**Testing:**
```bash
# Test daily job with 24h data
pytest tests/test_daily_analysis_scheduler.py::test_processes_24h_only -v

# Test aggregate storage
pytest tests/test_daily_analysis_scheduler.py::test_stores_aggregates -v

# Measure performance
pytest tests/test_daily_analysis_scheduler.py::test_performance_improvement -v
```

**Deliverable:** Daily batch job using incremental processing

---

#### Step 5: Implement Retention Policies (AI5.9)
**Files to modify:**
- `src/clients/influxdb_client.py`
- `src/scheduler/daily_analysis.py`

**Key Code:**
```python
# Create buckets with retention
def create_bucket_with_retention(self, bucket_name, retention_days):
    """Create InfluxDB bucket with retention policy."""
    retention_seconds = retention_days * 24 * 60 * 60
    
    buckets_api = self.client.buckets_api()
    bucket = buckets_api.create_bucket(
        bucket_name=bucket_name,
        org=self.org,
        retention_rules=[{
            "type": "expire",
            "everySeconds": retention_seconds
        }]
    )
    logger.info(f"Created bucket {bucket_name} with {retention_days}d retention")
```

**Setup Script:**
```python
# scripts/setup_influxdb_buckets.py
from src.clients.influxdb_client import InfluxDBEventClient

client = InfluxDBEventClient(...)

# Create buckets with retention
client.create_bucket_with_retention("pattern_aggregates_daily", 90)
client.create_bucket_with_retention("pattern_aggregates_weekly", 365)

# Update existing bucket retention
client.update_bucket_retention("home_assistant_events", 7)
```

**Deliverable:** Automatic data retention working

---

### Phase 3: Weekly/Monthly Processing (Week 3)

#### Step 6-8: Implement Weekly/Monthly Layers (AI5.5, AI5.6, AI5.7, AI5.8)

**Files to modify:**
- `src/clients/pattern_aggregate_client.py` (add weekly/monthly methods)
- `src/pattern_detection/session_detector.py`
- `src/pattern_detection/day_type_detector.py`
- `src/pattern_detection/contextual_detector.py`
- `src/pattern_detection/seasonal_detector.py`
- `src/scheduler/daily_analysis.py` (add weekly/monthly jobs)

**Key Code:**
```python
# Add to daily_analysis.py
class DailyAnalysisScheduler:
    def start(self):
        # Daily job (existing)
        self.scheduler.add_job(
            self.run_daily_analysis,
            CronTrigger.from_crontab(settings.analysis_schedule)
        )
        
        # Weekly job (NEW)
        self.scheduler.add_job(
            self.run_weekly_analysis,
            CronTrigger(day_of_week='sun', hour=3, minute=0)
        )
        
        # Monthly job (NEW)
        self.scheduler.add_job(
            self.run_monthly_analysis,
            CronTrigger(day=1, hour=3, minute=0)
        )
    
    async def run_weekly_analysis(self):
        """Process weekly aggregates for Group B detectors."""
        aggregate_client = PatternAggregateClient(...)
        
        # Query last 7 days of daily aggregates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Run Group B detectors
        session_detector = SessionDetector(aggregate_client=aggregate_client)
        session_patterns = session_detector.detect_patterns_from_aggregates(
            start_date, end_date
        )
        
        # Store weekly aggregates
        # ...
```

**Deliverable:** Weekly and monthly processing operational

---

### Phase 4: Testing & Migration (Week 4)

#### Step 9-10: Performance Testing & Migration (AI5.10, AI5.11)

**Performance Tests:**
```python
# tests/performance/test_incremental_performance.py
def test_daily_processing_time():
    """Verify daily processing < 1 minute."""
    start = time.time()
    await scheduler.run_daily_analysis()
    duration = time.time() - start
    
    assert duration < 60, f"Processing took {duration}s, expected <60s"

def test_memory_usage():
    """Verify memory usage < 150MB."""
    import psutil
    process = psutil.Process()
    
    await scheduler.run_daily_analysis()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    assert memory_mb < 150, f"Memory usage {memory_mb}MB, expected <150MB"
```

**Migration Script:**
```python
# scripts/migrate_to_incremental.py
async def migrate():
    """Migrate from old to new architecture."""
    
    # 1. Backup existing data
    logger.info("Backing up existing patterns...")
    await backup_sqlite_patterns()
    
    # 2. Create new InfluxDB buckets
    logger.info("Creating InfluxDB buckets...")
    await create_influxdb_buckets()
    
    # 3. Optional: Backfill historical aggregates
    if args.backfill:
        logger.info("Backfilling historical aggregates...")
        await backfill_aggregates(days=30)
    
    # 4. Update configuration
    logger.info("Updating configuration...")
    await update_config()
    
    # 5. Restart services
    logger.info("Migration complete! Restart services.")
```

**Deliverable:** Production-ready system with migration path

---

## Testing Checklist

### Unit Tests
- [ ] PatternAggregateClient write methods
- [ ] PatternAggregateClient read methods
- [ ] Each detector's incremental processing
- [ ] Each detector's aggregate storage
- [ ] Daily batch job with 24h data
- [ ] Weekly batch job
- [ ] Monthly batch job

### Integration Tests
- [ ] End-to-end daily processing
- [ ] End-to-end weekly processing
- [ ] End-to-end monthly processing
- [ ] InfluxDB connectivity
- [ ] SQLite compatibility

### Performance Tests
- [ ] Daily processing time < 1 min
- [ ] Memory usage < 150MB
- [ ] Storage usage < 1GB
- [ ] Query performance < 500ms

### Accuracy Tests
- [ ] Pattern detection accuracy ±5%
- [ ] No false positives increase
- [ ] No false negatives increase

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Backup existing data
- [ ] Review migration plan
- [ ] Prepare rollback procedure

### Deployment Steps
1. [ ] Stop AI automation service
2. [ ] Backup SQLite database
3. [ ] Create InfluxDB buckets
4. [ ] Run migration script
5. [ ] Update configuration
6. [ ] Start AI automation service
7. [ ] Monitor first daily run
8. [ ] Validate patterns generated
9. [ ] Check storage usage
10. [ ] Monitor for 7 days

### Post-Deployment
- [ ] Verify pattern accuracy
- [ ] Monitor performance metrics
- [ ] Check storage growth
- [ ] Validate retention policies
- [ ] Update documentation

---

## Troubleshooting

### Issue: Daily job takes > 1 minute
**Solution:** Check InfluxDB query performance, optimize tag structure

### Issue: Pattern accuracy decreased
**Solution:** Validate aggregate calculations, check for data loss

### Issue: Storage growing too fast
**Solution:** Verify retention policies active, check for duplicate writes

### Issue: InfluxDB connection errors
**Solution:** Check network connectivity, verify credentials, check bucket exists

---

## Rollback Procedure

If issues occur, rollback to previous system:

1. Stop AI automation service
2. Restore SQLite backup
3. Revert code to previous version
4. Update configuration to use 30-day processing
5. Restart service
6. Monitor for stability

---

## Success Criteria

✅ **Performance:**
- Daily processing < 1 minute
- Memory usage < 150MB
- Storage < 1GB

✅ **Quality:**
- Pattern accuracy ±5%
- No data loss
- System stable 7 days

✅ **Compatibility:**
- APIs unchanged
- Frontend works
- No breaking changes

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-15  
**Status:** Ready for Implementation

