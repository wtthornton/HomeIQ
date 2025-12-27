# Migration Plan - Alpha Environment

**Epic:** AI-5 (Incremental Pattern Processing)  
**Created:** 2025-01-15  
**Status:** Ready for Implementation  
**Purpose:** Simplified migration plan for alpha environment with data recreation

---

## Alpha Environment Approach

Since we're in **alpha environment**, we can take a simplified approach:
- **No data preservation** required
- **No rollback procedures** needed
- **Direct schema changes** allowed
- **Fresh start** with new architecture

---

## Migration Strategy

### Phase 1: Environment Preparation (30 minutes)

#### 1.1 Stop All Services
```bash
# Stop AI automation service
docker-compose stop ai-automation-service

# Stop websocket-ingestion (if needed)
docker-compose stop websocket-ingestion

# Stop data-api (if needed)
docker-compose stop data-api
```

#### 1.2 Backup Configuration Only
```bash
# Backup only configuration files (not data)
cp services/ai-automation-service/src/config.py services/ai-automation-service/src/config.py.backup
cp docker-compose.yml docker-compose.yml.backup
cp .env .env.backup
```

#### 1.3 Clean InfluxDB
```bash
# Connect to InfluxDB
docker exec -it influxdb influx

# Delete existing buckets
DROP BUCKET "home_assistant_events"
DROP BUCKET "pattern_aggregates_daily"  # if exists
DROP BUCKET "pattern_aggregates_weekly" # if exists

# Create new buckets with retention policies
CREATE BUCKET "home_assistant_events" WITH RETENTION 7d
CREATE BUCKET "pattern_aggregates_daily" WITH RETENTION 90d
CREATE BUCKET "pattern_aggregates_weekly" WITH RETENTION 52w
```

#### 1.4 Clean SQLite Database
```bash
# Remove existing pattern database
rm data/patterns.db
rm data/patterns.db-shm
rm data/patterns.db-wal

# Create fresh database (will be created on first run)
touch data/patterns.db
```

### Phase 2: Code Deployment (2 hours)

#### 2.1 Deploy New Code
```bash
# Pull latest code with Epic AI-5 changes
git checkout feature/epic-ai5-incremental-processing

# Install new dependencies
cd services/ai-automation-service
pip install -r requirements.txt
```

#### 2.2 Update Configuration
```yaml
# Update .env file
INFLUXDB_BUCKET_RAW=home_assistant_events
INFLUXDB_BUCKET_DAILY=pattern_aggregates_daily
INFLUXDB_BUCKET_WEEKLY=pattern_aggregates_weekly
INFLUXDB_RETENTION_RAW=7d
INFLUXDB_RETENTION_DAILY=90d
INFLUXDB_RETENTION_WEEKLY=52w

# Update processing schedule
ANALYSIS_SCHEDULE=0 3 * * *  # Daily at 3 AM
WEEKLY_ANALYSIS_SCHEDULE=0 3 * * 0  # Weekly on Sunday at 3 AM
MONTHLY_ANALYSIS_SCHEDULE=0 3 1 * *  # Monthly on 1st at 3 AM
```

#### 2.3 Deploy Services
```bash
# Start services with new configuration
docker-compose up -d

# Verify services are running
docker-compose ps
```

### Phase 3: Validation (1 hour)

#### 3.1 Verify InfluxDB Setup
```bash
# Check buckets exist
docker exec -it influxdb influx
SHOW BUCKETS

# Expected output:
# name                    retention
# ----                    --------
# home_assistant_events   7d
# pattern_aggregates_daily 90d
# pattern_aggregates_weekly 52w
```

#### 3.2 Test Data Flow
```bash
# Check websocket-ingestion is writing to Layer 1
docker logs websocket-ingestion | grep "Events written"

# Check AI automation service is processing
docker logs ai-automation-service | grep "Processing"
```

#### 3.3 Run Test Analysis
```bash
# Trigger manual daily analysis
docker exec -it ai-automation-service python -c "
from src.scheduler.daily_analysis import DailyAnalysisScheduler
scheduler = DailyAnalysisScheduler()
await scheduler.run_daily_analysis()
"
```

### Phase 4: Monitoring (24 hours)

#### 4.1 Monitor First Daily Run
```bash
# Watch logs during first daily run (3 AM)
docker logs -f ai-automation-service

# Expected logs:
# - "Processing 100K events for 2025-01-15"
# - "Stored daily aggregates for 6 detectors"
# - "Processing completed in 45 seconds"
```

#### 4.2 Verify Data Storage
```bash
# Check Layer 1 data
docker exec -it influxdb influx
USE home_assistant_events
SELECT COUNT(*) FROM home_assistant_events WHERE _time > now() - 1d

# Check Layer 2 data
USE pattern_aggregates_daily
SELECT COUNT(*) FROM time_based_daily WHERE _time > now() - 1d
```

#### 4.3 Performance Validation
```bash
# Check processing time
docker logs ai-automation-service | grep "Processing completed"

# Expected: < 60 seconds (vs previous 4 minutes)
```

---

## Implementation Checklist

### Pre-Migration
- [ ] Stop all services
- [ ] Backup configuration files
- [ ] Clean InfluxDB buckets
- [ ] Clean SQLite database
- [ ] Verify clean state

### Code Deployment
- [ ] Deploy Epic AI-5 code
- [ ] Install new dependencies
- [ ] Update configuration
- [ ] Start services
- [ ] Verify services running

### Validation
- [ ] Verify InfluxDB buckets created
- [ ] Test data flow
- [ ] Run test analysis
- [ ] Check logs for errors

### Monitoring
- [ ] Monitor first daily run
- [ ] Verify data storage
- [ ] Check performance metrics
- [ ] Validate pattern detection

---

## Expected Results

### Immediate Results
```yaml
Processing Time:
  Before: 2-4 minutes
  After: 30-60 seconds
  Improvement: 4x faster

Memory Usage:
  Before: 200-400MB
  After: 100-150MB
  Improvement: 50% reduction

Storage Usage:
  Before: 9GB system impact
  After: 556MB system impact
  Improvement: 94% reduction
```

### Data Flow Validation
```yaml
Layer 1 (Raw Events):
  - 100K events/day
  - 7-day retention
  - ~700K total events

Layer 2 (Daily Aggregates):
  - ~100 records/day
  - 90-day retention
  - ~9K total records

Layer 3 (Weekly/Monthly):
  - ~20 records/week
  - 52-week retention
  - ~1K total records

Layer 4 (Pattern Summaries):
  - ~10 patterns/day
  - Forever retention
  - ~1K total patterns
```

---

## Troubleshooting

### Common Issues

#### Issue: Services won't start
```bash
# Check logs
docker logs ai-automation-service

# Common fixes:
# - Check InfluxDB connection
# - Verify bucket names
# - Check configuration syntax
```

#### Issue: No data in Layer 2
```bash
# Check if daily analysis ran
docker logs ai-automation-service | grep "daily analysis"

# Check InfluxDB connection
docker exec -it influxdb influx
USE pattern_aggregates_daily
SHOW MEASUREMENTS
```

#### Issue: Processing time still slow
```bash
# Check if using 24h data (not 30 days)
docker logs ai-automation-service | grep "Processing.*events"

# Should show ~100K events, not 3M
```

### Recovery Procedures

#### If Migration Fails
```bash
# Stop services
docker-compose down

# Restore configuration
cp services/ai-automation-service/src/config.py.backup services/ai-automation-service/src/config.py
cp docker-compose.yml.backup docker-compose.yml
cp .env.backup .env

# Restart with old configuration
docker-compose up -d
```

#### If Data Corruption
```bash
# Clean everything and start fresh
docker-compose down
docker volume rm ha-ingestor_influxdb_data
docker-compose up -d
```

---

## Success Criteria

### Technical Success
- [ ] All services running without errors
- [ ] Daily processing < 1 minute
- [ ] Memory usage < 150MB
- [ ] Storage usage < 1GB
- [ ] All 4 layers storing data correctly

### Functional Success
- [ ] Pattern detection working
- [ ] Historical queries working
- [ ] UI displaying patterns
- [ ] No data loss (fresh start)
- [ ] Performance targets met

### Operational Success
- [ ] System stable for 24 hours
- [ ] No manual intervention needed
- [ ] Monitoring working
- [ ] Logs clean and informative
- [ ] Documentation updated

---

## Post-Migration Tasks

### Immediate (Day 1)
- [ ] Monitor first daily run
- [ ] Verify all data layers
- [ ] Check performance metrics
- [ ] Update team on status

### Short-term (Week 1)
- [ ] Monitor weekly run
- [ ] Check storage growth
- [ ] Optimize any slow queries
- [ ] Document lessons learned

### Long-term (Month 1)
- [ ] Monitor monthly run
- [ ] Review storage projections
- [ ] Plan capacity upgrades
- [ ] Update documentation

---

## Alpha-Specific Considerations

### No Data Preservation
- Fresh start with new architecture
- No historical data migration
- Patterns will rebuild over time
- Faster implementation

### No Rollback Needed
- Can recreate environment quickly
- No complex migration procedures
- Focus on functionality over safety
- Rapid iteration possible

### Simplified Testing
- Test with fresh data
- No compatibility concerns
- Focus on new features
- Clean validation environment

---

## Next Steps After Migration

### Week 1: Foundation
- [ ] Complete Story AI5.1 (Storage Design) ✅
- [ ] Implement Story AI5.2 (InfluxDB Client)
- [ ] Convert Story AI5.3 (Group A Detectors)

### Week 2: Daily Processing
- [ ] Complete Story AI5.4 (Daily Batch)
- [ ] Implement Story AI5.9 (Retention Policies)
- [ ] Begin Story AI5.10 (Performance Testing)

### Week 3: Weekly/Monthly
- [ ] Complete Stories AI5.5-AI5.8 (All Layers)
- [ ] Finish Story AI5.10 (Performance Testing)
- [ ] Prepare Story AI5.11 (Migration Script)

### Week 4: Production Ready
- [ ] Complete all stories
- [ ] Full system validation
- [ ] Documentation updates
- [ ] Ready for production

---

**Document Status:** Complete  
**Last Updated:** 2025-01-15  
**Ready for:** Alpha Implementation  
**Environment:** Alpha (No Data Preservation)

---

## Summary

This simplified migration plan is designed for alpha environment where:
- **No data preservation** is required
- **No rollback procedures** are needed
- **Direct schema changes** are allowed
- **Fresh start** approach is taken

The migration can be completed in **3.5 hours** with immediate validation and **24-hour monitoring** to ensure success.

**Key Benefits:**
- Simple and fast implementation
- No complex migration procedures
- Focus on functionality over safety
- Rapid iteration and testing

**Ready to proceed with alpha migration!** 🚀
