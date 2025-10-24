# Performance Targets & SLAs

**Last Updated:** October 24, 2025  
**Purpose:** Performance targets and service level agreements for HomeIQ

## Response Time Targets

| Endpoint Type | Target | Acceptable | Investigation Threshold |
|---------------|--------|------------|------------------------|
| Health checks | <10ms | <50ms | >100ms |
| Device/Entity queries (SQLite) | <10ms | <50ms | >100ms |
| Event queries (InfluxDB) | <100ms | <200ms | >500ms |
| AI suggestions (OpenAI) | <5s | <10s | >15s |
| Dashboard full load | <2s | <5s | >10s |
| Webhook delivery | <1s | <3s | >5s |

## Throughput Targets

| Metric | Minimum | Target | Peak |
|--------|---------|--------|------|
| Event processing | 100/sec | 500/sec | 1000+/sec |
| API requests | 10/sec | 50/sec | 100/sec |
| WebSocket connections | 1 | 1-3 | 5 |
| Batch writes (InfluxDB) | 10/min | 60/min | 120/min |

## Resource Utilization Targets

| Resource | Normal | Warning | Critical |
|----------|--------|---------|----------|
| CPU (per service) | <20% | 50-80% | >80% |
| Memory (per service) | <60% of limit | 60-80% | >80% |
| Disk usage | <70% | 70-85% | >85% |
| InfluxDB memory | <400MB | 400-480MB | >480MB |

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

### WebSocket Ingestion Service
- **Event Processing:** 1000+ events/sec peak
- **Batch Size:** 100 events per batch
- **Batch Timeout:** 5 seconds
- **Memory Limit:** 512MB
- **Health Check:** <10ms response

### Data API Service
- **Device Queries:** <10ms (SQLite)
- **Event Queries:** <100ms (InfluxDB)
- **Concurrent Requests:** 100+
- **Memory Limit:** 256MB
- **Health Check:** <10ms response

### Admin API Service
- **Health Checks:** <10ms
- **Statistics:** <50ms
- **Docker Management:** <200ms
- **Memory Limit:** 256MB
- **Health Check:** <10ms response

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

### Memory Budget (per service)
- **WebSocket Ingestion:** 512MB (event buffering)
- **Data API:** 256MB (query processing)
- **Admin API:** 256MB (monitoring)
- **Health Dashboard:** 128MB (React app)
- **Total System:** 2GB maximum

### CPU Budget (per service)
- **Normal Operation:** <20% CPU
- **Peak Load:** <50% CPU
- **Sustained Load:** <30% CPU
- **Background Tasks:** <10% CPU

### Network Budget
- **Inbound Events:** 1000 events/sec
- **Outbound Webhooks:** 100 webhooks/sec
- **API Requests:** 100 requests/sec
- **Dashboard Traffic:** 50 concurrent users

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
