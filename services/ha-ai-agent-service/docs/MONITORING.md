# Monitoring Guide

**Service:** HA AI Agent Service  
**Last Updated:** January 2025

This guide covers monitoring setup, health checks, logging, and metrics for the HA AI Agent Service.

## Health Checks

### Health Endpoint

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "ha-ai-agent-service",
  "version": "1.0.0"
}
```

**Status Codes:**
- **200 OK:** Service is healthy
- **503 Service Unavailable:** Service is unhealthy

### Docker Health Check

Configured in `docker-compose.yml`:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8030/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

**Check Health:**
```bash
# Manual check
curl http://localhost:8030/health

# Docker health status
docker inspect homeiq-ha-ai-agent-service | jq '.[0].State.Health'
```

## Logging

### Log Configuration

**Format:** Structured JSON (via Python logging)

**Levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL

**Configuration:**
- Environment variable: `LOG_LEVEL` (default: `INFO`)
- Rotated logs: 10MB max, 3 files retained

### View Logs

```bash
# Real-time logs
docker-compose logs -f ha-ai-agent-service

# Last 100 lines
docker-compose logs --tail=100 ha-ai-agent-service

# Filter by level
docker-compose logs ha-ai-agent-service | grep ERROR

# Search logs
docker-compose logs ha-ai-agent-service | grep "conversation"
```

### Log Examples

**Startup:**
```
🚀 Starting HA AI Agent Service...
✅ Settings loaded (HA URL: http://homeassistant:8123)
✅ Database initialized
✅ Context builder initialized
```

**Chat Request:**
```
INFO: Chat request completed: conversation=conv-123, tokens=150, time=1234ms
```

**Errors:**
```
ERROR: OpenAI API error: Rate limit exceeded
ERROR: Data API connection error: Could not connect to Data API
```

## Metrics

### Service Metrics

**Available via logs and health endpoint:**

1. **Request Metrics:**
   - Total requests
   - Success rate
   - Error rate
   - Response time

2. **OpenAI Metrics:**
   - Total tokens used
   - Total requests
   - Error count

3. **Resource Metrics:**
   - Memory usage
   - CPU usage
   - Database size

### Monitoring Queries

**Container Stats:**
```bash
docker stats homeiq-ha-ai-agent-service
```

**Database Size:**
```bash
docker exec homeiq-ha-ai-agent-service du -sh /app/data/ha_ai_agent.db
```

**OpenAI Usage:**
```bash
# Check logs for token usage
docker-compose logs ha-ai-agent-service | grep "tokens"
```

## Alerting

### Recommended Alerts

1. **Service Down**
   - Health check fails for 2+ minutes
   - Container not running

2. **High Error Rate**
   - >10% error rate for 5 minutes
   - 503 errors from OpenAI

3. **Resource Issues**
   - Memory usage >80%
   - Disk usage >90%

4. **Performance Degradation**
   - Response time >5 seconds
   - Health check timeout

### Alert Examples

**Service Down:**
```bash
# Check if service is running
docker ps | grep ha-ai-agent-service

# Check health
curl -f http://localhost:8030/health || echo "ALERT: Service down"
```

**Error Rate:**
```bash
# Count errors in last 5 minutes
docker-compose logs --since 5m ha-ai-agent-service | grep -c ERROR
```

## Performance Monitoring

### Response Time

**Target:** <3 seconds for chat endpoint

**Monitor:**
```bash
# Check response times in logs
docker-compose logs ha-ai-agent-service | grep "response_time_ms"
```

### Token Usage

**Monitor OpenAI token usage:**
```bash
# Extract token counts from logs
docker-compose logs ha-ai-agent-service | grep "tokens_used"
```

### Database Performance

**Check database size:**
```bash
docker exec homeiq-ha-ai-agent-service sqlite3 /app/data/ha_ai_agent.db "PRAGMA page_count * PRAGMA page_size;"
```

## Log Aggregation

### Docker Log Driver

Configured in `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### External Log Aggregation

For production, consider:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Loki** (Grafana Loki)
- **CloudWatch** (AWS)
- **Datadog**

## Metrics Collection

### Recommended Tools

1. **Prometheus** - Metrics collection
2. **Grafana** - Metrics visualization
3. **cAdvisor** - Container metrics
4. **Node Exporter** - System metrics

### Custom Metrics (Future)

Consider adding:
- Request count (by endpoint)
- Response time percentiles (p50, p95, p99)
- Error rate (by error type)
- Token usage (total, per request)
- Conversation count
- Cache hit rate

## Best Practices

1. **Monitor health checks** - Alert on failures
2. **Track error rates** - Identify patterns
3. **Monitor resource usage** - Prevent exhaustion
4. **Log aggregation** - Centralized logging
5. **Metrics collection** - Historical analysis
6. **Alert on thresholds** - Proactive monitoring

## Related Documentation

- [Error Handling](./ERROR_HANDLING.md)
- [Performance](./PERFORMANCE.md)
- [Deployment Guide](./DEPLOYMENT.md)

