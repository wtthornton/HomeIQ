# Nginx Proxy Configuration Guide

**Last Updated:** February 7, 2026  
**Status:** Active  
**Version:** 1.0

## Overview

This guide documents nginx proxy configuration patterns for the HomeIQ health dashboard, including best practices for Docker container networking and service proxying.

## Configuration Patterns

### Pattern 1: Always-Running Services (Direct proxy_pass)

**Use for:** Services that are always running when nginx starts (core services)

**Configuration:**
```nginx
# Option A: Use upstream block (recommended for connection pooling)
upstream data_api {
    server data-api:8006;
    keepalive 32;
}

location /api/integrations {
    proxy_pass http://data_api/api/integrations;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Option B: Direct hostname (simpler, no connection pooling)
location /api/integrations {
    proxy_pass http://data-api:8006/api/integrations;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Advantages:**
- Nginx resolves hostname at startup (faster)
- Simpler configuration
- Better for services that are always available

**Disadvantages:**
- Nginx will fail to start if service isn't running
- No connection pooling (unless using upstream block)

### Pattern 2: Optional Services (Variable-based proxy_pass)

**Use for:** Services that may not be running when nginx starts (optional services)

**Configuration:**
```nginx
# Resolver must be configured at server level
server {
    resolver 127.0.0.11 valid=10s;  # Docker's internal DNS
    resolver_timeout 3s;
    
    location /weather/ {
        set $weather_service "http://weather-api:8009";
        proxy_pass $weather_service/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Advantages:**
- Nginx can start even if service isn't running
- Hostname resolved dynamically when requests arrive
- Prevents "host not found in upstream" errors

**Disadvantages:**
- Requires resolver directive
- Slightly more complex configuration
- No connection pooling

### Pattern 3: Prefix Location with Path Stripping

**Use for:** Services where you want to strip the prefix path

**Configuration:**
```nginx
location /setup-service/ {
    # Automatically strips /setup-service/ and forwards the rest
    proxy_pass http://ha-setup-service:8020/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Example:**
- Request: `/setup-service/api/health/environment`
- Forwarded to: `http://ha-setup-service:8020/api/health/environment`

**Note:** The trailing slash in `proxy_pass` is critical - it tells nginx to strip the matched location prefix.

## Common Issues and Solutions

### Issue 1: "host not found in upstream" Error

**Symptoms:**
- Nginx fails to start
- Error: `nginx: [emerg] host not found in upstream "service-name"`

**Cause:**
- Using direct `proxy_pass` with a service that isn't running at nginx startup
- Nginx tries to resolve hostname at startup and fails

**Solution:**
- Use variable-based `proxy_pass` with resolver (Pattern 2)
- Or ensure the service is running before starting nginx

### Issue 2: 502 Bad Gateway

**Symptoms:**
- Requests return 502 Bad Gateway
- Service is running but proxy fails

**Causes:**
1. Wrong service name (doesn't match docker-compose.yml)
2. Wrong port (internal vs external port mismatch)
3. Service not accessible from nginx container

**Solutions:**
1. Verify service name matches docker-compose.yml container name
2. Check internal port (not external port) in proxy_pass
3. Verify services are on the same Docker network
4. Check service logs: `docker logs <service-name>`

**Example Fix:**
```nginx
# Wrong (old service name)
location /ai-automation/ {
    proxy_pass http://ai-automation-service:8018/;  # Wrong name and port
}

# Correct (updated service name and port)
location /ai-automation/ {
    proxy_pass http://ai-automation-service-new:8025/;  # Correct name and port
}
```

### Issue 3: Proxy Returns Wrong Endpoint (Root Instead of Target)

**Symptoms:**
- Requesting `/setup-service/api/health/environment` returns root endpoint `/`
- Backend logs show `GET /` instead of `GET /api/health/environment`

**Cause:**
- Variable-based `proxy_pass` not forwarding path correctly
- Regex location block not capturing path properly

**Solution:**
- Use prefix location with trailing slash (Pattern 3)
- Or use direct `proxy_pass` without variables

**Example Fix:**
```nginx
# Wrong (variable-based with regex)
location ~ ^/setup-service/(.*)$ {
    set $service "http://ha-setup-service:8020";
    proxy_pass $service/$1;  # Path forwarding issue
}

# Correct (prefix location)
location /setup-service/ {
    proxy_pass http://ha-setup-service:8020/;  # Automatic path stripping
}
```

### Issue 4: Connection Closed Unexpectedly

**Symptoms:**
- Requests fail with "connection closed unexpectedly"
- Container keeps restarting

**Causes:**
1. Nginx configuration syntax error
2. Service not ready when nginx starts
3. Network connectivity issues

**Solutions:**
1. Check nginx config: `docker exec homeiq-dashboard nginx -t`
2. Wait for services to be ready before starting nginx
3. Check Docker network: `docker network inspect homeiq-network`
4. Review nginx logs: `docker logs homeiq-dashboard`

## Service Name Reference

**Current Service Names (December 2025):**
- `data-api` - Port 8006 (use `data_api` upstream block)
- `admin-api` - Port 8004
- `ha-setup-service` - Port 8020 (internal), 8027 (external)
- `ai-automation-service-new` - Port 8025 (internal), 8036 (external)
- `log-aggregator` - Port 8015
- `weather-api` - Port 8009 (optional service)

**Deprecated Service Names:**
- ~~`ai-automation-service`~~ → Use `ai-automation-service-new`
- ~~`enrichment-pipeline`~~ → Deprecated in Epic 31

## Verification Commands

**Test Proxy Endpoints:**
```bash
# Setup service health
curl http://localhost:3000/setup-service/api/health/environment

# Integrations
curl http://localhost:3000/api/integrations

# Log aggregator
curl http://localhost:3000/log-aggregator/health

# AI automation
curl http://localhost:3000/ai-automation/health

# Weather (if running)
curl http://localhost:3000/weather/health
```

**Check Nginx Configuration:**
```bash
# Test syntax
docker exec homeiq-dashboard nginx -t

# View active config
docker exec homeiq-dashboard nginx -T | grep -A 5 "location"

# Check logs
docker logs homeiq-dashboard --tail 50
```

**Verify Service Names:**
```bash
# List running containers
docker ps --format "{{.Names}}\t{{.Ports}}"

# Check docker-compose service names
grep -E "container_name:|ports:" docker-compose.yml | grep -A 1 "service-name"
```

## Best Practices

1. **Use upstream blocks** for always-running services (connection pooling)
2. **Use variable-based proxy_pass** for optional services (prevents startup failures)
3. **Verify service names** match docker-compose.yml container names
4. **Use internal ports** in proxy_pass (not external ports)
5. **Test configuration** after changes: `docker exec homeiq-dashboard nginx -t`
6. **Rebuild container** after nginx.conf changes: `docker-compose build health-dashboard`
7. **Check logs** if proxy fails: `docker logs homeiq-dashboard`

## References

- [Nginx proxy_pass Documentation](http://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass)
- [Docker Networking](https://docs.docker.com/network/)
- [Deployment Runbook](./DEPLOYMENT_RUNBOOK.md#nginx-proxy-issues-dashboard)
- [Health Dashboard README](../services/health-dashboard/README.md#nginx-configuration)

---

**Maintainer:** DevOps Team  
**Review Frequency:** Quarterly  
**Last Review:** December 29, 2025

