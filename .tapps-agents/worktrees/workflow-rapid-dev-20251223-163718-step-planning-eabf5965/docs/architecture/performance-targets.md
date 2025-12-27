# Performance Targets & SLAs

**Last Updated:** January 2025  
**Purpose:** Performance targets and service level agreements for HomeIQ  
**Target Platform:** Home Assistant single-home deployment on NUC (Next Unit of Computing)  
**Context7 Patterns:** Integrated throughout

## Response Time Targets

| Endpoint Type | Target | Acceptable | Investigation Threshold |
|---------------|--------|------------|------------------------|
| Health checks | <10ms | <50ms | >100ms |
| Device/Entity queries (SQLite) | <10ms | <50ms | >100ms |
| Event queries (InfluxDB) | <100ms | <200ms | >500ms |
| AI suggestions (OpenAI) | <5s | <10s | >15s |
| Dashboard full load | <2s | <5s | >10s |
| Webhook delivery | <1s | <3s | >5s |

## Throughput Targets (Single-Home NUC)

| Metric | Minimum | Target | Peak |
|--------|---------|--------|------|
| Event processing | 50/sec | 200/sec | 500/sec |
| API requests | 5/sec | 20/sec | 50/sec |
| WebSocket connections | 1 | 1 | 1 |
| Batch writes (InfluxDB) | 10/min | 30/min | 60/min |
| Home Assistant events | 50/sec | 150/sec | 400/sec |

**Single-Home Context:**
- Lower event volumes (1 home vs multi-tenant)
- Single WebSocket connection to Home Assistant
- Reduced API request targets (single user)
- More conservative peak targets for NUC stability

## Resource Utilization Targets (NUC-Optimized)

| Resource | Normal | Warning | Critical |
|----------|--------|---------|----------|
| CPU (per service) | <30% | 50-70% | >70% |
| Memory (per service) | <60% of limit | 60-80% | >80% |
| Total system memory | <70% | 70-85% | >85% |
| Disk usage | <70% | 70-85% | >85% |
| InfluxDB memory | <256MB | 256-320MB | >320MB |
| SQLite cache | <32MB | 32-48MB | >48MB |

**NUC-Specific Notes:**
- Lower CPU thresholds due to limited cores (2-4 typical)
- Reduced InfluxDB memory target for NUC constraints
- SQLite cache reduced to 32MB (vs 64MB for larger systems)
- Total system memory monitoring critical on NUC

## Availability Targets

| Service Tier | Target Uptime | Max Downtime/Month |
|--------------|---------------|-------------------|
| Critical (websocket-ingestion, data-api) | 99.5% | 3.6 hours |
| High (admin-api, enrichment) | 99.0% | 7.2 hours |
| Medium (external data services) | 95.0% | 36 hours |

**Notes:**
- These are targets for a single-tenant home automation system
- "Downtime" includes planned maintenance
- External API failures don't count against uptime (graceful degradation)

## Performance Monitoring Thresholds

### Alert Thresholds
- **Response Time:** P95 > target × 2
- **Error Rate:** >5% for 5 minutes
- **Memory Usage:** >80% of limit for 10 minutes
- **CPU Usage:** >80% for 15 minutes
- **Queue Size:** >1000 events for 5 minutes

### Escalation Levels
1. **Level 1:** Automated retry and circuit breaker
2. **Level 2:** Alert to development team
3. **Level 3:** Alert to on-call engineer
4. **Level 4:** Alert to management

## Service-Specific Targets

### WebSocket Ingestion Service (NUC-Optimized)
- **Event Processing:** 500 events/sec peak (single-home)
- **Batch Size:** 50-100 events per batch
- **Batch Timeout:** 3-5 seconds
- **Memory Limit:** 256MB (NUC constraint)
- **Health Check:** <10ms response
- **Context7 Telemetry:** Structured logging with correlation IDs

### Data API Service (NUC-Optimized)
- **Device Queries:** <10ms (SQLite)
- **Event Queries:** <100ms (InfluxDB)
- **Concurrent Requests:** 50+ (single-home)
- **Memory Limit:** 128MB (NUC constraint)
- **Health Check:** <10ms response
- **Context7 Patterns:** Pydantic settings, lifespan context managers

### Admin API Service (NUC-Optimized)
- **Health Checks:** <10ms
- **Statistics:** <50ms
- **Docker Management:** <200ms
- **Memory Limit:** 128MB (NUC constraint)
- **Health Check:** <10ms response
- **Context7 Patterns:** Global state with setter pattern for telemetry

### Health Dashboard
- **Initial Load:** <2s
- **Tab Switching:** <500ms
- **Real-time Updates:** <100ms
- **Bundle Size:** <500KB total
- **Health Check:** <10ms response

## Performance Testing Requirements

### Load Testing
- **API Endpoints:** 100 concurrent users
- **Dashboard:** 50 concurrent users
- **Event Processing:** 1000 events/sec sustained
- **Duration:** 30 minutes minimum

### Stress Testing
- **API Endpoints:** 200 concurrent users
- **Event Processing:** 2000 events/sec peak
- **Duration:** 10 minutes
- **Recovery Time:** <5 minutes

### Endurance Testing
- **24-hour continuous operation**
- **Memory leak detection**
- **Performance degradation monitoring**
- **Automatic recovery verification**

## Performance Regression Detection

### Automated Monitoring
- **CI/CD Pipeline:** Performance tests on every PR
- **Production Monitoring:** Real-time performance metrics
- **Alerting:** Immediate notification on threshold breaches
- **Dashboards:** Visual performance tracking

### Manual Testing
- **Weekly Performance Reviews:** Analyze trends and patterns
- **Monthly Load Tests:** Verify capacity planning
- **Quarterly Stress Tests:** Validate system limits
- **Annual Performance Audits:** Comprehensive review

## Performance Optimization Guidelines

### When to Optimize
- **Response time >2x target** for 5+ minutes
- **Error rate >5%** for 10+ minutes
- **Resource usage >80%** for 15+ minutes
- **User complaints** about performance

### Optimization Priority
1. **Critical Path:** Health checks, device queries, event writes
2. **High Impact:** Dashboard load, API responses
3. **Medium Impact:** Background processing, batch jobs
4. **Low Impact:** Admin functions, reporting

### Optimization Process
1. **Profile First:** Identify actual bottlenecks
2. **Measure Baseline:** Record current performance
3. **Implement Changes:** Apply targeted optimizations
4. **Test Results:** Verify improvements
5. **Monitor Production:** Watch for regressions
6. **Document Changes:** Update performance characteristics

## Performance Budget

### Memory Budget (NUC-Optimized)
- **WebSocket Ingestion:** 256MB (event buffering, reduced for NUC)
- **Data API:** 128MB (query processing, reduced for NUC)
- **Admin API:** 128MB (monitoring, reduced for NUC)
- **Health Dashboard:** 64MB (React app, reduced for NUC)
- **InfluxDB:** 256MB (reduced from 400MB)
- **SQLite:** 32MB cache (reduced from 64MB)
- **Total System:** 1GB maximum (NUC constraint)
- **Reserve:** 512MB for OS and Home Assistant

### CPU Budget (NUC-Optimized)
- **Normal Operation:** <30% CPU per service
- **Peak Load:** <60% CPU per service
- **Sustained Load:** <40% CPU per service
- **Background Tasks:** <15% CPU
- **Total System:** <80% CPU (reserve for Home Assistant)
- **Context7 Overhead:** <2% CPU (telemetry and structured logging)

### Network Budget (Single-Home NUC)
- **Inbound Events:** 500 events/sec (single-home)
- **Outbound Webhooks:** 50 webhooks/sec (single-home)
- **API Requests:** 50 requests/sec (single user)
- **Dashboard Traffic:** 1-3 concurrent users (single home)
- **Home Assistant WebSocket:** 1 connection (persistent)
- **Context7 Telemetry:** <1% bandwidth (structured logs)

## Performance Documentation

### Required Documentation
- **Performance Characteristics:** For each service
- **Optimization History:** Changes and their impact
- **Monitoring Setup:** Metrics and alerting configuration
- **Testing Procedures:** Load, stress, and endurance tests
- **Troubleshooting Guide:** Common issues and solutions

### Update Schedule
- **Performance Targets:** Quarterly review
- **Monitoring Thresholds:** Monthly review
- **Service Characteristics:** After each major change
- **Documentation:** Continuous updates
