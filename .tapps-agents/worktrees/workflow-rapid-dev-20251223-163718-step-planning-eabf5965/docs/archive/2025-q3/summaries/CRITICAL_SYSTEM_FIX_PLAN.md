# Critical System Fix Plan

## 🚨 **CRITICAL SYSTEM STATUS**

**Current State**: SYSTEM DEGRADED - Multiple critical failures detected
**Impact**: 0% event processing, 100% data loss, broken WebSocket connection
**Priority**: IMMEDIATE ACTION REQUIRED

---

## 📊 **Issue Analysis Summary**

### Dashboard State
- ❌ **Overall Status**: DEGRADED
- ❌ **WebSocket Connection**: DISCONNECTED (0 connection attempts)  
- ⚠️ **Event Processing**: DEGRADED (0 events/min)
- ✅ **Database Storage**: HEALTHY (but schema conflicts)
- ✅ **Weather Service**: ENABLED (but no data flow)

### Critical Errors Identified
1. **WebSocket Transport Error**: `ConnectionResetError: Cannot write to closing transport`
2. **InfluxDB Schema Conflict**: `field type conflict: input field "attr_dynamics" is type boolean, already exists as type string`
3. **Service Communication Failure**: `Failed to send event to enrichment service` (HTTP 500)

---

## 🎯 **DETAILED TASK PLAN**

### **PHASE 1: IMMEDIATE CRITICAL FIXES** ⚡

#### Task 1.1: Fix InfluxDB Schema Conflicts
**Priority**: CRITICAL - Blocks all data persistence
**Estimated Time**: 5 minutes
**Actions**:
1. Clear conflicting InfluxDB measurements
2. Reset schema to clean state
3. Verify data bucket is accessible

#### Task 1.2: Fix WebSocket Connection
**Priority**: CRITICAL - Blocks event ingestion
**Estimated Time**: 3 minutes
**Actions**:
1. Restart WebSocket ingestion service
2. Verify Home Assistant connectivity
3. Check authentication tokens

#### Task 1.3: Fix Service Communication
**Priority**: CRITICAL - Blocks event processing pipeline
**Estimated Time**: 5 minutes
**Actions**:
1. Restart all services in correct order
2. Verify service-to-service connectivity
3. Check network and port configurations

### **PHASE 2: SYSTEM VERIFICATION** ✅

#### Task 2.1: Health Check Verification
**Priority**: HIGH - Confirm fixes worked
**Estimated Time**: 5 minutes
**Actions**:
1. Check dashboard metrics
2. Verify event processing rates
3. Confirm data persistence

#### Task 2.2: End-to-End Testing
**Priority**: HIGH - Validate complete pipeline
**Estimated Time**: 10 minutes
**Actions**:
1. Generate test events
2. Verify weather enrichment
3. Check InfluxDB data writes

### **PHASE 3: MONITORING & OPTIMIZATION** 📈

#### Task 3.1: Performance Monitoring
**Priority**: MEDIUM - Ensure stability
**Estimated Time**: 5 minutes
**Actions**:
1. Monitor system metrics
2. Check error rates
3. Verify service health

#### Task 3.2: Documentation Update
**Priority**: MEDIUM - Record fixes
**Estimated Time**: 5 minutes
**Actions**:
1. Document resolution steps
2. Update troubleshooting guide
3. Record lessons learned

---

## ⚡ **IMMEDIATE EXECUTION PLAN**

### **Step 1: InfluxDB Schema Fix**
```bash
# Clear conflicting measurements
docker-compose exec influxdb influx delete \
  --bucket home_assistant_events \
  --start 1970-01-01T00:00:00Z \
  --stop $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

### **Step 2: Service Restart Sequence**
```bash
# Stop all services
docker-compose down

# Start core services first
docker-compose up -d influxdb enrichment-pipeline

# Wait for health checks
sleep 30

# Start WebSocket service
docker-compose up -d websocket-ingestion

# Start remaining services
docker-compose up -d
```

### **Step 3: Health Verification**
```bash
# Check service status
docker-compose ps

# Verify WebSocket connection
docker-compose logs websocket-ingestion --tail=20

# Check InfluxDB connectivity
docker-compose exec influxdb influx ping
```

---

## 🎯 **SUCCESS CRITERIA**

### **Critical Success Metrics**
- ✅ **WebSocket Connection**: Status = "connected"
- ✅ **Event Processing**: Rate > 0 events/min
- ✅ **Database Writes**: No schema conflicts
- ✅ **Service Health**: All services "healthy"
- ✅ **Dashboard Status**: Overall status = "healthy"

### **Performance Targets**
- **Event Processing Rate**: > 10 events/min
- **Error Rate**: < 1%
- **Service Uptime**: > 99%
- **Data Persistence**: 100% success rate

---

## 🚨 **RISK MITIGATION**

### **Potential Risks**
1. **Data Loss**: Clearing InfluxDB will remove existing data
2. **Service Downtime**: Restart sequence causes temporary outage
3. **Configuration Issues**: Environment variables may need adjustment

### **Mitigation Strategies**
1. **Backup Strategy**: Document current state before changes
2. **Rollback Plan**: Keep previous configuration available
3. **Monitoring**: Continuous health checks during fixes

---

## 📋 **EXECUTION CHECKLIST**

### **Pre-Execution**
- [ ] Document current system state
- [ ] Backup critical configurations
- [ ] Notify stakeholders of maintenance window

### **Execution**
- [ ] Execute InfluxDB schema fix
- [ ] Restart services in correct sequence
- [ ] Verify each service health
- [ ] Test end-to-end functionality

### **Post-Execution**
- [ ] Monitor system for 30 minutes
- [ ] Verify all success criteria met
- [ ] Update documentation
- [ ] Report status to stakeholders

---

## 🎉 **EXPECTED OUTCOME**

After executing this plan:
- **System Status**: HEALTHY
- **Event Processing**: Fully operational
- **Data Pipeline**: Complete end-to-end functionality
- **Weather Enrichment**: Active with API calls
- **Dashboard Metrics**: All green indicators

**Total Estimated Time**: 30-45 minutes
**System Downtime**: 5-10 minutes during restarts
