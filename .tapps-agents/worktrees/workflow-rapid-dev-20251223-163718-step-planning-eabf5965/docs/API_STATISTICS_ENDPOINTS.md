# ⛔ SUPERSEDED - See API_REFERENCE.md

> **This document has been SUPERSEDED by [api/API_REFERENCE.md](api/API_REFERENCE.md#statistics-api)**  
> **Last Updated:** October 20, 2025  
> **Status:** Historical reference only - will be archived in next cleanup
> 
> **Please use:** [api/API_REFERENCE.md#statistics-api](api/API_REFERENCE.md#statistics-api) - Statistics section in consolidated API reference

---

# Statistics API Endpoints Reference

**Service:** Admin API  
**Base URL:** `http://localhost:8003`  
**Version:** v1  
**Last Updated:** 2025-10-18  

---

## Overview

The Admin API provides comprehensive statistics and monitoring endpoints for the HA Ingestor system. These endpoints aggregate metrics from all services, providing system-wide visibility and real-time insights.

### Key Features
- 📊 **8 Statistics Endpoints** - Complete system monitoring
- ⚡ **Real-Time Metrics** - 5-10ms response time
- 🔄 **Parallel Queries** - Fetch all service metrics simultaneously
- 🛡️ **Graceful Degradation** - Partial data on service failures
- 💾 **InfluxDB Integration** - Time-series data with fallback

---

## Endpoints

### 1. System Statistics

#### `GET /api/v1/stats`

Get comprehensive system statistics with configurable time period.

**Query Parameters:**
- `period` (optional) - Time period: `1h`, `24h`, `7d`, `30d` (default: `1h`)
- `service` (optional) - Filter by specific service name

**Response:**
```json
{
  "timestamp": "2025-10-18T18:00:00Z",
  "period": "1h",
  "metrics": {
    "websocket-ingestion": {
      "events_per_minute": 254,
      "error_rate": 0.02,
      "success_rate": 99.98
    },
    "enrichment-pipeline": {
      "events_per_minute": 240,
      "processing_time_ms": 120
    }
  },
  "trends": {
    "websocket-ingestion": [...],
    "enrichment-pipeline": [...]
  },
  "alerts": [],
  "source": "services-fallback"
}
```

**Example:**
```bash
curl "http://localhost:8003/api/v1/stats?period=24h"
curl "http://localhost:8003/api/v1/stats?service=websocket-ingestion"
```

---

### 2. Service Statistics

#### `GET /api/v1/stats/services`

Get statistics for all services with individual health metrics.

**Response:**
```json
{
  "websocket-ingestion": {
    "metrics": {
      "events_per_minute": 254,
      "error_rate": 0.02
    },
    "trends": [...],
    "alerts": []
  },
  "enrichment-pipeline": {
    "metrics": {
      "processing_rate": 240,
      "success_rate": 99.5
    },
    "trends": [...],
    "alerts": []
  }
}
```

**Example:**
```bash
curl "http://localhost:8003/api/v1/stats/services"
```

---

### 3. Metrics Query

#### `GET /api/v1/stats/metrics`

Query specific metrics with filtering and pagination.

**Query Parameters:**
- `metric_name` (optional) - Specific metric to query
- `service` (optional) - Filter by service
- `limit` (optional) - Max results (default: 100, max: 200)

**Response:**
```json
[
  {
    "name": "events_per_minute",
    "value": 254.5,
    "unit": "events/min",
    "timestamp": "2025-10-18T18:00:00Z",
    "tags": {
      "service": "websocket-ingestion"
    }
  }
]
```

**Examples:**
```bash
# Get all metrics
curl "http://localhost:8003/api/v1/stats/metrics"

# Get specific metric
curl "http://localhost:8003/api/v1/stats/metrics?metric_name=events_per_minute"

# Filter by service
curl "http://localhost:8003/api/v1/stats/metrics?service=websocket-ingestion&limit=50"
```

---

### 4. Performance Statistics

#### `GET /api/v1/stats/performance`

Get performance analytics with optimization recommendations.

**Response:**
```json
{
  "overall": {
    "total_requests": 15234,
    "total_errors": 12,
    "average_response_time": 125.5,
    "success_rate": 99.92,
    "throughput": 42.5
  },
  "services": {
    "websocket-ingestion": {
      "total_requests": 8500,
      "average_response_time": 85.2,
      "success_rate": 99.98
    }
  },
  "recommendations": [
    {
      "service": "enrichment-pipeline",
      "type": "performance",
      "level": "info",
      "message": "Response time optimal",
      "recommendation": "No action needed"
    }
  ]
}
```

**Example:**
```bash
curl "http://localhost:8003/api/v1/stats/performance"
```

---

### 5. Active Alerts

#### `GET /api/v1/stats/alerts`

Get active system alerts sorted by severity.

**Response:**
```json
[
  {
    "service": "websocket-ingestion",
    "level": "warning",
    "message": "Elevated error rate: 2.5%",
    "timestamp": "2025-10-18T18:00:00Z"
  }
]
```

**Alert Levels:**
- `critical` - Immediate action required
- `error` - Service degradation
- `warning` - Potential issues
- `info` - Informational

**Example:**
```bash
curl "http://localhost:8003/api/v1/stats/alerts"
```

---

### 6. Real-Time Metrics (Dashboard Optimized) ⚡

#### `GET /api/v1/real-time-metrics`

**NEW in Oct 2025** - Consolidated metrics endpoint specifically optimized for dashboard consumption.

**Key Benefits:**
- **Single API Call** - Replaces 6-10 individual service calls
- **5-10ms Response** - Blazing fast with parallel queries
- **Consistent Timestamps** - All metrics from same moment
- **Graceful Degradation** - Returns partial data if some services fail

**Response:**
```json
{
  "events_per_hour": 45000,
  "api_calls_active": 5,
  "data_sources_active": ["influxdb", "websocket", "home-assistant"],
  "api_metrics": [
    {
      "service": "websocket-ingestion",
      "status": "active",
      "events_per_hour": 180.0,
      "uptime_seconds": 1196.3,
      "response_time_ms": 0,
      "last_success": "2025-10-18T18:43:23.428553"
    },
    {
      "service": "enrichment-pipeline",
      "status": "active",
      "events_per_hour": 10027.4,
      "uptime_seconds": 1206.28,
      "response_time_ms": 0,
      "last_success": "2025-10-18T18:43:23.428996"
    }
  ],
  "inactive_apis": 1,
  "error_apis": 0,
  "total_apis": 15,
  "health_summary": {
    "healthy": 2,
    "unhealthy": 13,
    "total": 15,
    "health_percentage": 13.3
  },
  "timestamp": "2025-10-18T18:43:23.429317"
}
```

**Example:**
```bash
# Get all real-time metrics
curl "http://localhost:8003/api/v1/real-time-metrics"

# With jq for pretty formatting
curl -s "http://localhost:8003/api/v1/real-time-metrics" | jq .

# Check specific fields
curl -s "http://localhost:8003/api/v1/real-time-metrics" | jq '.health_summary'
```

**Use Case:**
Perfect for Health Dashboard that needs to display:
- Current event ingestion rate
- Active services count
- Per-service health status
- Overall system health percentage

**Performance:**
- Response Time: 5-10ms (p95)
- Cache: None (always fresh data)
- Timeout: 15s overall, 5s per service
- Parallel Queries: Yes (all services queried simultaneously)

---

## Data Sources

### Primary: InfluxDB
When available, endpoints use InfluxDB for time-series metrics:
- Historical trends
- Aggregated statistics
- Long-term performance data

**Indicator:** `"source": "influxdb"` in response

### Fallback: Service HTTP Calls
If InfluxDB unavailable, endpoints query services directly:
- Real-time data
- Current status
- Recent metrics

**Indicator:** `"source": "services-fallback"` in response

---

## Error Handling

### HTTP Status Codes
- `200 OK` - Request successful
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Endpoint doesn't exist
- `500 Internal Server Error` - Server error

### Partial Failures
All endpoints handle service failures gracefully:
- Missing services return fallback data
- Timeouts don't fail entire request
- Errors included in response body

**Example Response with Errors:**
```json
{
  "events_per_hour": 0,
  "api_calls_active": 0,
  "error": "Failed to get event rate: Connection timeout",
  "timestamp": "2025-10-18T18:00:00Z"
}
```

---

## Performance Characteristics

### Response Times (95th Percentile)
| Endpoint | Typical | Maximum | Notes |
|----------|---------|---------|-------|
| `/stats` | 200ms | 500ms | Depends on period |
| `/stats/services` | 300ms | 500ms | Queries all services |
| `/stats/metrics` | 100ms | 300ms | Depends on limit |
| `/stats/performance` | 200ms | 400ms | Calculated metrics |
| `/stats/alerts` | 10ms | 50ms | Lightweight |
| `/real-time-metrics` | 5-10ms | 50ms | **Optimized!** |

### Caching Strategy
- **Real-time metrics:** No cache (always fresh)
- **Statistics:** 5-minute TTL (future enhancement)
- **Performance stats:** 10-minute TTL (future enhancement)

### Concurrent Requests
All endpoints support concurrent requests:
- **Recommended:** < 100 req/sec per endpoint
- **Maximum:** < 200 req/sec per endpoint
- **Rate Limiting:** Not currently implemented

---

## Integration Examples

### Health Dashboard Integration

**Before (Multiple Calls):**
```typescript
// 6-10 API calls per refresh
const eventRate = await fetch('/api/v1/event-rate');
const websocketHealth = await fetch('http://websocket:8001/health');
const enrichmentHealth = await fetch('http://enrichment:8002/health');
const dataApiHealth = await fetch('http://data-api:8006/health');
// ... 3-6 more calls
```

**After (Single Call):**
```typescript
// 1 API call per refresh
const metrics = await fetch('http://localhost:8003/api/v1/real-time-metrics');
// Contains all dashboard data in single response
```

**Performance Improvement:**
- **API Calls:** 6-10 → 1 (80-90% reduction)
- **Latency:** 500-1500ms → 5-10ms (98% faster)
- **Network Overhead:** Significantly reduced
- **Data Consistency:** Same timestamp for all metrics

---

### Monitoring Dashboard Example

```typescript
interface DashboardMetrics {
  events_per_hour: number;
  api_calls_active: number;
  data_sources_active: string[];
  api_metrics: ServiceMetric[];
  health_summary: {
    healthy: number;
    unhealthy: number;
    total: number;
    health_percentage: number;
  };
  timestamp: string;
}

async function updateDashboard() {
  try {
    const response = await fetch('http://localhost:8003/api/v1/real-time-metrics');
    const metrics: DashboardMetrics = await response.json();
    
    // Update UI components
    updateEventRate(metrics.events_per_hour);
    updateServiceHealth(metrics.health_summary);
    updateServiceList(metrics.api_metrics);
    
  } catch (error) {
    console.error('Failed to fetch metrics:', error);
    // Handle error gracefully
  }
}

// Refresh every 5 seconds
setInterval(updateDashboard, 5000);
```

---

## Troubleshooting

### Endpoint Returns 404
**Cause:** Using wrong URL or prefix
```bash
# ❌ Wrong
curl http://localhost:8003/stats

# ✅ Correct
curl http://localhost:8003/api/v1/stats
```

### Empty Metrics Response
**Causes:**
1. InfluxDB not running → Check `"source": "services-fallback"` in response
2. No services configured → Check service URLs in admin-api config
3. All services down → Check `docker ps` for container health

**Solution:**
```bash
# Check InfluxDB
docker ps | grep influxdb

# Check admin-api logs
docker logs homeiq-admin --tail 50

# Verify service URLs
docker exec homeiq-admin env | grep URL
```

### Slow Response Times
**Causes:**
1. InfluxDB query timeout → Uses fallback automatically
2. Service not responding → Individual timeout triggers
3. Network issues → Check container networking

**Solution:**
```bash
# Check admin-api logs for timeout warnings
docker logs homeiq-admin | grep -i timeout

# Test individual service health
curl http://localhost:8001/health  # websocket
curl http://localhost:8002/health  # enrichment
curl http://localhost:8006/health  # data-api
```

---

## Related Documentation

- **Story INFRA-2:** [Implement Statistics Endpoints](../stories/story-infra-2-implement-stats-endpoints.md)
- **Story INFRA-3:** [Implement Real-Time Metrics](../stories/story-infra-3-implement-realtime-metrics.md)
- **Deployment Guide:** [Full Rebuild Deployment](../../implementation/FULL_REBUILD_DEPLOYMENT_COMPLETE.md)
- **API Architecture:** [Admin API Documentation](architecture/services/admin-api.md)

---

## Version History

### v1.0 (2025-10-18)
- Initial implementation of statistics API
- 8 endpoints covering system monitoring
- Real-time metrics optimization
- InfluxDB integration with fallback

### Planned Enhancements
- [ ] Response caching with TTL
- [ ] WebSocket streaming for real-time push
- [ ] Historical comparison (week-over-week)
- [ ] Exportable formats (CSV, JSON)
- [ ] Rate limiting
- [ ] API key authentication

---

**For issues or questions, check the troubleshooting section or review the implementation stories.**

