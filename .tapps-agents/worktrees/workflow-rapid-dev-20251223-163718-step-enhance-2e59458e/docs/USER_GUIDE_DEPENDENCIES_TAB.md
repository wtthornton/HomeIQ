# Dependencies Tab User Guide

## Overview

The Dependencies tab in the Health Dashboard provides real-time visibility into all 15 microservices that power the Home Assistant Ingestor system. This guide explains how to use and interpret the metrics displayed.

## Accessing the Dependencies Tab

1. Open the Health Dashboard at `http://localhost:3000`
2. Click on the "Dependencies" tab
3. Metrics will automatically refresh every 5 seconds

## Understanding the Metrics

### Top-Level Metrics Cards

The Dependencies tab displays five key metrics at the top:

#### 1. **Events/sec** (Green)
- **What it shows**: Current rate of events being processed across all services
- **Interpretation**:
  - `> 1.0`: High activity - system is actively processing events
  - `0.1-1.0`: Normal activity - steady event processing
  - `< 0.1` or `0.0`: Low/no activity - check if data sources are active

#### 2. **Active APIs** (Blue)
- **What it shows**: Number of services currently processing events
- **Interpretation**:
  - High number (8-15): Most services are operational
  - Medium number (4-7): Some services may be idle or down
  - Low number (0-3): System health issue - investigate inactive services

#### 3. **Inactive APIs** (Red)
- **What it shows**: Number of services responding but not processing events
- **Interpretation**:
  - `0-2`: Normal - some services may be intentionally idle
  - `3-5`: Check if external data sources are configured
  - `> 5`: Potential configuration issue

#### 4. **Error APIs** (Orange)
- **What it shows**: Number of services experiencing errors or timeouts
- **Interpretation**:
  - `0`: All services healthy
  - `1-2`: Minor issues - check error messages
  - `> 2`: System health concern - investigate urgently

#### 5. **Health Score %** (Purple)
- **What it shows**: Overall system health percentage
- **Interpretation**:
  - `90-100%`: Excellent health
  - `75-89%`: Good health - minor issues
  - `50-74%`: Degraded health - attention needed
  - `< 50%`: Poor health - immediate action required

## Per-API Metrics Table

The table below the metrics cards shows detailed information for each service:

### Column Descriptions

#### Service
- **Format**: Service name in monospace font
- **Example**: `websocket-ingestion`, `data-api`

#### Events/sec
- **Format**: Decimal number (2 decimal places)
- **Example**: `2.50`, `0.75`, `0.00`
- **What it means**: Current event processing rate for this service

#### Events/hour
- **Format**: Whole number
- **Example**: `9000`, `2700`, `0`
- **What it means**: Projected hourly event count based on current rate
- **Calculation**: Events/sec × 3600

#### Uptime
- **Format**: Human-readable time
- **Examples**:
  - `45m 30s` - Service running for 45 minutes
  - `2h 15m` - Service running for 2 hours and 15 minutes
  - `5h 30m` - Service running for 5+ hours

#### Status
- **Format**: Color-coded badge with optional error message
- **Possible Values**:
  - 🟢 **active** (Green) - Service is healthy and processing events
  - 🟡 **inactive** (Yellow) - Service is running but not processing events
  - 🟠 **timeout** (Orange) - Service didn't respond within timeout period
  - ⚫ **not_configured** (Gray) - Service URL not configured in admin-api
  - 🔴 **error** (Red) - Service returned an error

### Status Interpretation Guide

#### 🟢 Active Status
- **Meaning**: Service is operating normally
- **Action**: None required
- **Expected for**: websocket-ingestion, data-api, enrichment-pipeline (when HA is connected)

#### 🟡 Inactive Status
- **Meaning**: Service is responding to health checks but not processing events
- **Possible Reasons**:
  - No incoming data from upstream services
  - Service is configured but data source is disabled
  - Legitimate idle state (e.g., calendar service with no upcoming events)
- **Action**: 
  - Check if this is expected (some services may be idle by design)
  - Verify upstream data sources are configured
  - Check service-specific configuration

#### 🟠 Timeout Status
- **Meaning**: Service didn't respond within the allocated timeout (3-10 seconds)
- **Possible Reasons**:
  - Service is overloaded or experiencing high latency
  - Network connectivity issue
  - Service is starting up or restarting
- **Action**:
  - Check service logs for errors
  - Verify service is running: `docker ps | grep service-name`
  - Check network connectivity between services
  - Consider increasing timeout if service legitimately needs more time

#### ⚫ Not Configured Status
- **Meaning**: Service URL is not configured in the admin-api
- **Possible Reasons**:
  - Service is not deployed in this environment
  - Service URL mapping is missing
  - Service is optional and intentionally not configured
- **Action**:
  - If service should be available, add URL to admin-api service_urls
  - If service is optional, this status is acceptable

#### 🔴 Error Status
- **Meaning**: Service returned an HTTP error or exception
- **Error Messages**: Displayed below the status badge
- **Possible Reasons**:
  - Service is experiencing internal errors
  - Service dependencies (database, external API) are unavailable
  - Code bug or unhandled exception
- **Action**:
  - Read the error message for specific details
  - Check service logs for stack traces
  - Verify service dependencies are healthy
  - Restart service if needed: `docker restart service-name`

## Common Scenarios

### Scenario 1: All Services Inactive
**Symptoms**:
- Active APIs: 0
- Inactive APIs: 15
- All services show "inactive" status

**Likely Cause**: Home Assistant is not connected or not sending events

**Solution**:
1. Check Home Assistant connection in websocket-ingestion logs
2. Verify HA_WS_URL and HA_TOKEN are correctly configured
3. Check Home Assistant is running and accessible

### Scenario 2: High Error Count
**Symptoms**:
- Error APIs: 5+
- Multiple services show "error" or "timeout" status

**Likely Cause**: System-wide issue (database down, network problem)

**Solution**:
1. Check InfluxDB is running and accessible
2. Verify Docker network connectivity
3. Check system resources (CPU, memory, disk)
4. Review service logs for common error patterns

### Scenario 3: Specific Service Always Timing Out
**Symptoms**:
- One service consistently shows "timeout" status
- Other services are "active"

**Likely Cause**: Service is slow, overloaded, or misconfigured

**Solution**:
1. Check service-specific logs
2. Verify service is not resource-constrained
3. Check if service is performing expensive operations
4. Consider increasing timeout for this service (requires code change)

### Scenario 4: Low Health Score Despite Active Services
**Symptoms**:
- Health Score: 60%
- Active APIs: 5
- Inactive APIs: 8
- Error APIs: 2

**Interpretation**: System is partially functional but degraded

**Solution**:
1. Identify which services are inactive/error
2. Determine if inactive services are expected to be active
3. Fix error services first (highest priority)
4. Investigate inactive services if they should be active

## Troubleshooting Tips

### Tip 1: Use Error Messages
- Error messages appear below status badges in red text
- They provide specific details about what went wrong
- Common errors:
  - `HTTP 500` - Internal server error
  - `Timeout after 5s` - Service didn't respond in time
  - `Connection refused` - Service is not running
  - `Not found` - Endpoint doesn't exist

### Tip 2: Check Service Logs
```bash
# View recent logs for a specific service
docker logs --tail 100 service-name

# Follow logs in real-time
docker logs -f service-name

# Check if service is running
docker ps | grep service-name
```

### Tip 3: Restart Troubled Services
```bash
# Restart a specific service
docker restart service-name

# Restart all services
docker-compose restart

# Check service health after restart
curl http://localhost:PORT/health
```

### Tip 4: Verify Network Connectivity
```bash
# Test connection to admin-api
curl http://localhost:8001/api/v1/real-time-metrics

# Test connection to a specific service
curl http://localhost:8000/api/v1/event-rate
```

## Advanced Features

### Polling Interval
- **Default**: 5 seconds
- **Modification**: Edit `DependenciesTab.tsx` and change `useRealTimeMetrics(5000)` parameter
- **Recommendation**: Don't go below 2 seconds to avoid overloading services

### Priority-Based Timeouts
Services have different timeout values based on their importance:
- **High Priority** (3-5s): websocket-ingestion, admin-api, data-api
- **Medium Priority** (5-10s): ai-automation-service, energy-correlator
- **Low Priority** (5s): External APIs, sports, weather

### Interpreting Events/Hour
- **Purpose**: Helps predict system load over time
- **Use Cases**:
  - Capacity planning: Will current rate cause issues over hours?
  - Trend analysis: Is event rate increasing or decreasing?
  - Alerting: Set thresholds for high event rates

## Best Practices

1. **Regular Monitoring**: Check the Dependencies tab at least once per day
2. **Health Score Alerts**: Investigate when health score drops below 80%
3. **Error Investigation**: Address error services immediately
4. **Baseline Establishment**: Learn your system's normal event rates
5. **Documentation**: Document expected inactive services (e.g., calendar may be inactive if no events scheduled)

## Related Documentation

- [API Guidelines](../architecture/api-guidelines.md) - Technical details of the metrics APIs
- [Epic 23 Implementation](../../implementation/EPIC_23_ENHANCED_DEPENDENCIES_METRICS_COMPLETE.md) - Complete implementation details
- [Health Dashboard Overview](../../implementation/REVIEW_GUIDE_START_HERE.md) - General dashboard usage

## Support

For issues or questions:
1. Check service logs for detailed error information
2. Review this guide's troubleshooting section
3. Check the Health Dashboard's other tabs for additional insights
4. Consult the technical documentation for API details

