# WebSocket Troubleshooting Guide

## 🎯 **Overview**

This guide helps diagnose and resolve WebSocket connection issues with the Home Assistant WebSocket Ingestion service. The service connects to Home Assistant's WebSocket API to receive real-time state changes.

---

## 🔍 **Quick Diagnostics**

### 1. Check Service Status
```bash
# Check if WebSocket service is running
docker-compose ps websocket-ingestion

# Check service health
curl http://localhost:8001/health
```

### 2. Check Logs
```bash
# View recent logs
docker-compose logs --tail=50 websocket-ingestion

# Follow logs in real-time
docker-compose logs -f websocket-ingestion
```

### 3. Test Home Assistant Connectivity
```bash
# Test Home Assistant accessibility
curl -H "Authorization: Bearer YOUR_TOKEN" http://YOUR_HA_URL/api/
```

---

## 🚨 **Common Issues & Solutions**

### Issue 1: Authentication Failures

**Symptoms:**
- Logs show "Authentication failed" errors
- Service shows "unhealthy" status
- No events being received

**Diagnosis:**
```bash
# Check authentication in logs
docker-compose logs websocket-ingestion | grep -i auth
```

**Solutions:**
1. **Verify Token:**
   ```bash
   # Check token in environment
   docker-compose exec websocket-ingestion env | grep HOME_ASSISTANT_TOKEN
   ```

2. **Test Token Manually:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://YOUR_HA_URL/api/config
   ```

3. **Regenerate Token:**
   - Go to Home Assistant → Profile → Long-lived access tokens
   - Create new token with full permissions
   - Update `.env` file

### Issue 2: Connection Timeouts

**Symptoms:**
- "Connection timeout" errors in logs
- Service keeps reconnecting
- Intermittent connectivity

**Diagnosis:**
```bash
# Check connection attempts
docker-compose logs websocket-ingestion | grep -i "connection"
```

**Solutions:**
1. **Check Network Connectivity:**
   ```bash
   # Test from container
   docker-compose exec websocket-ingestion ping YOUR_HA_HOST
   ```

2. **Verify Home Assistant URL:**
   - Ensure URL is accessible from Docker network
   - Check if using internal vs external IP
   - Verify SSL/TLS configuration

3. **Check Firewall/Proxy:**
   - Ensure ports are open
   - Check for proxy interference
   - Verify WebSocket support

### Issue 3: Subscription Failures

**Symptoms:**
- Connected but no events received
- "Subscription failed" in logs
- Events counter stays at 0

**Diagnosis:**
```bash
# Check subscription status
curl http://localhost:8001/health | jq '.subscription'
```

**Solutions:**
1. **Check Authentication Timing:**
   - Service now includes 1-second delay after authentication
   - This ensures authentication completes before subscription

2. **Verify Event Types:**
   ```bash
   # Check what events are being subscribed to
   docker-compose logs websocket-ingestion | grep "subscribe"
   ```

3. **Test Manual Subscription:**
   ```bash
   # Check if Home Assistant accepts subscriptions
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"type": "subscribe_events", "event_type": "state_changed"}' \
        http://YOUR_HA_URL/api/websocket
   ```

### Issue 4: High Memory Usage

**Symptoms:**
- Container using excessive memory
- Service becomes unresponsive
- Out of memory errors

**Diagnosis:**
```bash
# Check memory usage
docker stats websocket-ingestion
```

**Solutions:**
1. **Check Event Volume:**
   ```bash
   # Monitor event rate
   curl http://localhost:8001/health | jq '.subscription.event_rate_per_minute'
   ```

2. **Review Logging Level:**
   - Reduce verbose logging in production
   - Check for memory leaks in event processing

3. **Restart Service:**
   ```bash
   docker-compose restart websocket-ingestion
   ```

---

## 🔧 **Advanced Troubleshooting**

### Debug Mode

Enable verbose logging for detailed diagnostics:

```bash
# Set debug environment variable
docker-compose exec websocket-ingestion env | grep LOG_LEVEL

# Update environment for debug
echo "LOG_LEVEL=DEBUG" >> .env
docker-compose restart websocket-ingestion
```

### Network Diagnostics

```bash
# Check Docker network
docker network ls
docker network inspect homeiq_default

# Test connectivity from service container
docker-compose exec websocket-ingestion nslookup YOUR_HA_HOST
docker-compose exec websocket-ingestion telnet YOUR_HA_HOST 8123
```

### Home Assistant Configuration

Verify Home Assistant WebSocket configuration:

1. **Check Configuration:**
   ```yaml
   # In configuration.yaml
   http:
     use_x_forwarded_for: true
     trusted_proxies:
       - 172.16.0.0/12  # Docker network
   ```

2. **Check API Access:**
   - Ensure API is enabled
   - Verify WebSocket API is accessible
   - Check for IP restrictions

---

## 📊 **Health Check Reference**

### Service Health Endpoint

**URL:** `http://localhost:8001/health`

**Response Fields:**
```json
{
  "status": "healthy|unhealthy|degraded",
  "service": "websocket-ingestion",
  "uptime": "0:05:23.123456",
  "connection": {
    "is_running": true,
    "connection_attempts": 1,
    "successful_connections": 1,
    "failed_connections": 0
  },
  "subscription": {
    "is_subscribed": true,
    "active_subscriptions": 1,
    "total_events_received": 42,
    "events_by_type": {
      "state_changed": 42
    },
    "last_event_time": "2025-10-10T21:12:39.436996",
    "event_rate_per_minute": 16.28
  }
}
```

### Health Status Meanings

- **healthy**: Service connected and receiving events
- **degraded**: Connected but not receiving events, or high error rate
- **unhealthy**: Cannot connect to Home Assistant

---

## 🛠️ **Recovery Procedures**

### Complete Service Reset

```bash
# Stop service
docker-compose stop websocket-ingestion

# Remove container
docker-compose rm -f websocket-ingestion

# Rebuild if needed
docker-compose build websocket-ingestion

# Start fresh
docker-compose up -d websocket-ingestion
```

### Configuration Reset

```bash
# Backup current config
cp .env .env.backup

# Reset to defaults
cp infrastructure/env.example .env

# Reconfigure
./scripts/setup-secure-env.sh
```

### Database Reset (If Needed)

```bash
# Clear InfluxDB data (CAUTION: This deletes all data!)
docker-compose down
docker volume rm homeiq_influxdb_data
docker-compose up -d
```

---

## 📋 **Monitoring Commands**

### Real-time Monitoring

```bash
# Monitor all services
watch -n 5 'docker-compose ps'

# Monitor WebSocket service specifically
watch -n 5 'curl -s http://localhost:8001/health | jq'

# Monitor logs
docker-compose logs -f websocket-ingestion
```

### Performance Monitoring

```bash
# Check resource usage
docker stats websocket-ingestion

# Check event rate
curl -s http://localhost:8001/health | jq '.subscription.event_rate_per_minute'

# Check connection status
curl -s http://localhost:8001/health | jq '.connection'
```

---

## 🚀 **Prevention Best Practices**

1. **Regular Health Checks:**
   - Monitor service health endpoints
   - Set up alerts for connection failures
   - Track event processing rates

2. **Token Management:**
   - Use long-lived tokens with appropriate permissions
   - Rotate tokens regularly
   - Store tokens securely

3. **Network Configuration:**
   - Use stable IP addresses for Home Assistant
   - Configure proper DNS resolution
   - Ensure WebSocket support in network infrastructure

4. **Monitoring Setup:**
   - Log aggregation for centralized monitoring
   - Metrics collection for performance tracking
   - Alerting for critical failures

---

## 📞 **Getting Help**

If issues persist after following this guide:

1. **Collect Information:**
   ```bash
   # Collect logs
   docker-compose logs websocket-ingestion > websocket-logs.txt
   
   # Collect health status
   curl http://localhost:8001/health > websocket-health.json
   
   # Collect system info
   docker-compose ps > service-status.txt
   ```

2. **Check Documentation:**
   - [Main README](README.md)
   - [Docker Structure Guide](DOCKER_STRUCTURE_GUIDE.md)
   - [API Documentation](API_ENDPOINTS_REFERENCE.md)

3. **Create Issue:**
   - Include collected logs and health status
   - Describe steps to reproduce
   - Include environment details (OS, Docker version, etc.)

---

## 📚 **Related Documentation**

- [WebSocket Fixes Summary](archive/summaries/WEBSOCKET_FIXES_SUMMARY.md)
- [WebSocket Fixes Test Results](archive/summaries/WEBSOCKET_FIXES_TEST_RESULTS.md)
- [WebSocket Fixes Deployment Log](archive/summaries/WEBSOCKET_FIXES_DEPLOYMENT_LOG.md)
- [WebSocket Fixes Final Summary](archive/summaries/WEBSOCKET_FIXES_FINAL_SUMMARY.md)
- [Dashboard 502 Fix Summary](archive/summaries/DASHBOARD_502_FIX_SUMMARY.md)
