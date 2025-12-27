# Simple Migration Strategy
## HA Ingestor Service Separation

### Executive Summary

**Objective**: Transform monolithic websocket ingestion service into proper microservices architecture with minimal downtime and zero data loss.

**Approach**: Simple, straightforward migration appropriate for an alpha system processing 17 events/minute.

**Total Time**: 30 minutes  
**Risk Level**: Low  
**Rollback Time**: < 5 minutes  

---

## Migration Overview

### Current State
```
Home Assistant → WebSocket Ingestion (MONOLITHIC) → InfluxDB
                                    ↓
                            Enrichment Pipeline (UNUSED)
```

### Target State
```
Home Assistant → WebSocket Ingestion → HTTP POST → Enrichment Pipeline → InfluxDB
     (Event Capture Only)                    (Processing & Storage)
```

---

## Pre-Migration Checklist

### ✅ Code Preparation
- [ ] HTTP client implemented in websocket service
- [ ] FastAPI endpoint added to enrichment service
- [ ] Configuration files updated
- [ ] Requirements.txt updated
- [ ] Dockerfiles updated

### ✅ Environment Preparation
- [ ] Backup current system state
- [ ] Verify HA connection is stable
- [ ] Check InfluxDB is accessible
- [ ] Ensure sufficient disk space
- [ ] Have rollback plan ready

### ✅ Monitoring Preparation
- [ ] Log monitoring tools ready
- [ ] InfluxDB query tools ready
- [ ] Service health check endpoints ready
- [ ] Event rate monitoring ready

---

## Migration Steps

### Step 1: Stop Services (2 minutes)

```bash
# Stop all services
docker-compose down

# Verify services are stopped
docker-compose ps
```

**Expected Result**: All services stopped, no containers running

### Step 2: Deploy New Code (3 minutes)

```bash
# Pull latest code (if using git)
git pull origin master

# Build new images
docker-compose build

# Start services with new code
docker-compose up -d
```

**Expected Result**: All services start successfully with new architecture

### Step 3: Verify Service Health (5 minutes)

```bash
# Check all services are running
docker-compose ps

# Test health endpoints
curl http://localhost:8002/health  # Enrichment service
curl http://localhost:8003/health  # Admin API

# Check service logs
docker-compose logs websocket-ingestion
docker-compose logs enrichment-pipeline
```

**Expected Results**:
- All services show "Up" status
- Health endpoints return 200 OK
- Logs show proper initialization
- No error messages in logs

### Step 4: Validate Event Flow (10 minutes)

```bash
# Monitor websocket service logs
docker-compose logs -f websocket-ingestion

# Monitor enrichment service logs  
docker-compose logs -f enrichment-pipeline

# Check InfluxDB for new data
influx query 'from(bucket:"ha_events") |> range(start: -5m) |> count()'
```

**Expected Results**:
- WebSocket service connects to HA successfully
- Events are sent via HTTP to enrichment service
- Enrichment service processes events and writes to InfluxDB
- Event rate maintains ~17 events/minute baseline

### Step 5: Performance Validation (10 minutes)

```bash
# Monitor event processing rate
watch -n 30 'influx query "from(bucket:\"ha_events\") |> range(start: -1m) |> count()"'

# Check for any errors in logs
docker-compose logs --tail=100 | grep -i error

# Verify service communication
curl -X POST http://localhost:8002/events \
  -H "Content-Type: application/json" \
  -d '{"event_type":"test","data":{},"time_fired":"2024-01-01T00:00:00Z","origin":"test"}'
```

**Expected Results**:
- Event processing rate matches baseline
- No errors in service logs
- Test event processed successfully
- HTTP communication working properly

---

## Success Criteria

### ✅ Functional Validation
- [ ] WebSocket service connects to HA
- [ ] Events flow: HA → WebSocket → HTTP → Enrichment → InfluxDB
- [ ] Event processing rate maintains baseline (~17 events/minute)
- [ ] No data loss during migration
- [ ] All services respond to health checks

### ✅ Technical Validation
- [ ] HTTP communication between services works
- [ ] Retry logic functions properly
- [ ] Error handling works as expected
- [ ] Logging provides adequate visibility
- [ ] Services recover from restarts

### ✅ Operational Validation
- [ ] Services start automatically
- [ ] Configuration is correct
- [ ] Ports are properly exposed
- [ ] Environment variables are set
- [ ] Docker networking works

---

## Rollback Plan

### Immediate Rollback (< 5 minutes)

If critical issues are detected:

```bash
# Stop services immediately
docker-compose down

# Revert to previous code version
git checkout HEAD~1

# Restart with previous version
docker-compose up -d

# Verify rollback success
docker-compose ps
curl http://localhost:8003/health
```

### Rollback Validation

```bash
# Check services are running
docker-compose ps

# Verify event flow restored
docker-compose logs -f websocket-ingestion

# Check InfluxDB data ingestion
influx query 'from(bucket:"ha_events") |> range(start: -5m) |> count()'
```

**Rollback Success Criteria**:
- All services running with previous code
- Event flow restored to original architecture
- No data loss during rollback
- System performance back to baseline

---

## Post-Migration Tasks

### Immediate (First 30 minutes)
- [ ] Monitor event processing rate
- [ ] Check for any error messages
- [ ] Verify InfluxDB data quality
- [ ] Test service restart scenarios

### Short-term (First 24 hours)
- [ ] Monitor system performance
- [ ] Check error rates and patterns
- [ ] Validate data consistency
- [ ] Document any issues found

### Long-term (First week)
- [ ] Performance optimization
- [ ] Error handling improvements
- [ ] Monitoring enhancements
- [ ] Documentation updates

---

## Risk Mitigation

### Low Risk Factors
- **Simple code changes**: Only HTTP communication added
- **No data migration**: Same InfluxDB, same data format
- **Quick rollback**: < 5 minutes to revert
- **Low volume**: Only 17 events/minute to process
- **Alpha system**: No production users affected

### Mitigation Strategies
- **Comprehensive testing**: All changes tested locally first
- **Quick rollback**: Immediate revert capability
- **Monitoring**: Real-time validation of event flow
- **Staged approach**: Services updated one at a time
- **Documentation**: Clear steps and success criteria

---

## Communication Plan

### Pre-Migration
- Notify team of migration window
- Share rollback plan and contact information
- Set up monitoring dashboards

### During Migration
- Real-time status updates
- Immediate notification of any issues
- Progress updates every 10 minutes

### Post-Migration
- Success confirmation
- Performance metrics summary
- Any issues or improvements identified

---

## Timeline Summary

| Phase | Duration | Description |
|-------|----------|-------------|
| **Pre-Migration** | 5 minutes | Final checks and preparation |
| **Stop Services** | 2 minutes | Graceful shutdown |
| **Deploy Code** | 3 minutes | Build and start new services |
| **Health Check** | 5 minutes | Verify service startup |
| **Event Validation** | 10 minutes | Confirm event flow |
| **Performance Check** | 10 minutes | Validate baseline performance |
| **Post-Migration** | 30 minutes | Monitoring and validation |

**Total Migration Time: 30 minutes**

---

## Success Metrics

### Performance Metrics
- **Event Processing Rate**: Maintain ~17 events/minute
- **Response Time**: HTTP calls < 100ms
- **Error Rate**: < 1% of events
- **Service Uptime**: 100% during migration

### Quality Metrics
- **Data Loss**: 0 events lost
- **Data Consistency**: All events properly processed
- **Service Health**: All health checks pass
- **Log Quality**: Clear, actionable log messages

This simple migration strategy provides a safe, straightforward path to proper microservices architecture without over-engineering for a low-volume alpha system.
