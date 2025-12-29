# HomeIQ Deployment Runbook

**Last Updated:** December 29, 2025  
**Status:** Active  
**Version:** 2.1

---

## Overview

This runbook provides step-by-step instructions for deploying HomeIQ to production, including pre-deployment checks, deployment procedures, and post-deployment verification.

**Note:** This runbook covers both automated (GitHub Actions) and manual deployment procedures. For automated deployments, see [Deployment Pipeline Documentation](./DEPLOYMENT_PIPELINE.md).

---

## Pre-Deployment Checklist

### 1. Environment Preparation

- [ ] Verify Docker and Docker Compose are installed
- [ ] Check available disk space (minimum 10GB free)
- [ ] Verify network connectivity
- [ ] Confirm all required environment variables are set

### 2. Configuration Verification

- [ ] Review `docker-compose.yml` configuration
- [ ] Verify environment files (`.env`, `infrastructure/env.production`)
- [ ] Check API keys and tokens are set (not default values)
- [ ] Verify Home Assistant URL and token
- [ ] Confirm InfluxDB credentials

### 3. Security Checks

- [ ] Run security audit: `python -m pytest services/*/tests/test_*security*.py -v`
- [ ] Verify no hardcoded credentials
- [ ] Check authentication is enabled on protected endpoints
- [ ] Review recent security fixes

### 4. Code Quality

- [ ] Run unit tests: `python scripts/simple-unit-tests.py`
- [ ] Check test coverage (target: >80% for critical services)
- [ ] Review and fix any critical linter errors
- [ ] Verify no critical bugs in issue tracker

---

## Deployment Methods

### Automated Deployment (Recommended)

**Use GitHub Actions workflow for automated deployments:**

1. **Push to main branch** or **create a tag** (`v*`)
2. **Quality gates run automatically:**
   - Tests must pass
   - Security scans must pass (no CRITICAL/HIGH vulnerabilities)
   - Code quality scores meet thresholds
   - Docker Compose config validation
3. **If gates pass, deployment starts automatically**
4. **Post-deployment validation runs:**
   - Health checks for all services
   - Database connectivity verification
   - Service dependency checks
5. **Notifications sent** (Slack, email, webhook)

**Manual Trigger:**
- Go to GitHub Actions → "Deploy to Production" → "Run workflow"

**See:** [Deployment Pipeline Documentation](./DEPLOYMENT_PIPELINE.md) for complete pipeline details.

### Manual Deployment

**Use this method for local deployments or when automation is unavailable:**

#### Step 1: Pre-Deployment Validation

```bash
# Run pre-deployment validation
python scripts/deployment/validate-deployment.py --pre-deployment
```

**Checks:**
- Docker Compose configuration
- Environment variables
- Service dependencies
- Resource limits

#### Step 2: Build Docker Images

```bash
# Build all services
docker compose build --parallel

# Or build specific service
docker compose build <service-name>
```

**Expected Time:** 5-15 minutes  
**Verification:** Check for build errors

#### Step 3: Start Services

```bash
# Start all services
docker compose up -d

# Or start specific service
docker compose up -d <service-name>
```

**Expected Time:** <1 minute  
**Verification:** Check container status

```bash
docker compose ps
```

**Important for Route Order Fixes:**
If you've modified FastAPI route definitions (e.g., `synergy_router.py`), use full container restart to ensure route registration order is correct:

```bash
# Full restart (recommended for route changes)
docker compose down <service-name>
docker compose up -d <service-name>

# Or for all services
docker compose down
docker compose up -d
```

**Note:** Using `docker compose restart` may not apply route order changes correctly. Use `down/up` for route modifications.

#### Step 4: Post-Deployment Validation

```bash
# Run post-deployment validation
python scripts/deployment/validate-deployment.py --post-deployment
```

**Checks:**
- Service connectivity
- Database connectivity
- Inter-service communication

#### Step 5: Verify Service Health

```bash
# Comprehensive health check (recommended)
bash scripts/deployment/health-check.sh

# Or use existing health check script
./scripts/check-service-health.sh

# Or check individual services
curl http://localhost:8001/health  # websocket-ingestion
curl http://localhost:8006/health  # data-api
curl http://localhost:8004/health  # admin-api
```

**Expected Result:** All critical services return HTTP 200

#### Step 6: Track Deployment

```bash
# Track deployment in database
python scripts/deployment/track-deployment.py \
  --deployment-id "deploy-$(date +%Y%m%d-%H%M%S)" \
  --status success \
  --commit $(git rev-parse HEAD) \
  --branch $(git branch --show-current)
```

---

## Post-Deployment Verification

### 1. Service Health Check

```bash
# Comprehensive health check (recommended)
bash scripts/deployment/health-check.sh

# JSON output for automation
bash scripts/deployment/health-check.sh --json > health-report.json

# Check critical services only
bash scripts/deployment/health-check.sh --critical-only

# Or use existing health check script
./scripts/check-service-health.sh --json > health-report.json
```

**Success Criteria:**
- All critical services healthy (HTTP 200)
- Response times < 500ms
- No connection errors
- All containers running

### 2. Functional Verification

**Test Event Ingestion:**
```bash
# Check websocket connection
curl http://localhost:8001/health

# Verify events in InfluxDB
curl "http://localhost:8006/api/v1/events?limit=5"
```

**Test Data API:**
```bash
# Test events endpoint
curl "http://localhost:8006/api/v1/events?limit=10"

# Test stats endpoint
curl "http://localhost:8006/api/v1/events/stats?period=1h"
```

**Test Dashboard:**
```bash
# Open dashboard in browser
open http://localhost:3000

# Verify dashboard loads and shows data
```

**Test Synergies API:**
```bash
# Test direct pattern service endpoint
curl http://localhost:8034/api/v1/synergies/stats

# Test via automation service proxy
curl http://localhost:8025/api/synergies/stats

# Test via frontend proxy (through nginx)
curl http://localhost:3001/api/synergies/stats

# Verify route order (should show /stats before /{synergy_id})
docker exec ai-pattern-service python3 -c "from src.main import app; from fastapi.routing import APIRoute; routes = [(r.path, r.endpoint.__name__ if hasattr(r, 'endpoint') else 'N/A') for r in app.routes if isinstance(r, APIRoute) and 'synerg' in r.path.lower()]; [print(f'{i+1}. {p:45} {h}') for i, (p, h) in enumerate(routes)]"
```

**Expected Results:**
- All endpoints return 200 OK with JSON statistics data
- Route order shows `/stats` before `/{synergy_id}`
- Frontend Synergies page loads without errors

### 3. Monitoring Setup

**Check Logs:**
```bash
# View service logs
docker-compose logs -f <service-name>

# Check for errors
docker-compose logs | grep -i error
```

**Monitor Health:**
```bash
# Set up periodic health checks (cron job)
*/5 * * * * /path/to/scripts/check-service-health.sh --json >> /var/log/homeiq-health.log
```

---

## Rollback Procedure

### Automatic Rollback

**Triggered automatically when:**
- Health checks fail after deployment
- Post-deployment validation fails

**Process:**
1. Health check failures detected
2. Rollback script automatically executes
3. Previous deployment images restored
4. Services restarted with previous configuration
5. Rollback verified
6. Rollback tracked and team notified

**No manual intervention required** - rollback happens automatically.

### Manual Rollback

**Use when automatic rollback fails or for manual deployments:**

#### Option 1: Rollback to Previous Deployment

```bash
# Rollback to previous successful deployment
bash scripts/deployment/rollback.sh --previous
```

#### Option 2: Rollback to Specific Deployment ID

```bash
# Rollback to specific deployment
bash scripts/deployment/rollback.sh --deployment-id <deployment-id>
```

#### Option 3: Rollback to Specific Tag

```bash
# Rollback to specific tag
bash scripts/deployment/rollback.sh --tag <tag>
```

#### Option 4: Manual Git Rollback

```bash
# Stop services
docker compose down

# Restore previous version
git checkout <previous-commit>

# Rebuild and restart
docker compose build
docker compose up -d

# Verify rollback
bash scripts/deployment/health-check.sh
```

### If Service Degrades

1. **Identify Failing Service:**
   ```bash
   bash scripts/deployment/health-check.sh
   docker compose ps
   ```

2. **Check Logs:**
   ```bash
   docker compose logs <service-name>
   ```

3. **Restart Service:**
   ```bash
   docker compose restart <service-name>
   ```

4. **If Persistent, Rollback:**
   - Use automated rollback script (recommended)
   - Or follow manual rollback procedure above

---

## Troubleshooting

### Service Won't Start

**Check:**
- Docker daemon running: `docker ps`
- Port conflicts: `netstat -an | grep <port>`
- Environment variables: `docker-compose config`
- Logs: `docker-compose logs <service-name>`

### Service Unhealthy

**Check:**
- Health endpoint: `curl http://localhost:<port>/health`
- Dependencies: Verify required services are running
- Configuration: Check environment variables
- Logs: Review service logs for errors

### Synergies API 404 Errors

**Problem:** `/api/synergies/stats` returns 404 Not Found

**Root Cause:** FastAPI route matching order - parameterized route matches before specific route

**Solution:**
1. Verify route order: `/stats` must be registered before `/{synergy_id}`
2. Use full container restart: `docker-compose down ai-pattern-service && docker-compose up -d ai-pattern-service`
3. Check route registration order in container:
   ```bash
   docker exec ai-pattern-service python3 -c "from src.main import app; from fastapi.routing import APIRoute; routes = [(r.path, r.endpoint.__name__) for r in app.routes if isinstance(r, APIRoute) and 'synerg' in r.path.lower()]; [print(f'{i+1}. {p}') for i, (p, _) in enumerate(routes)]"
   ```
4. Verify `/stats` appears before `/{synergy_id}` in route list

**Prevention:**
- Always define specific routes before parameterized routes in FastAPI
- Use full container restart (`down/up`) after route changes, not just `restart`
- Test route order after deployment

**See:** `implementation/SYNERGIES_API_FIX_COMPLETE.md` for complete fix details

### Nginx Proxy Issues (Dashboard)

**Common Issues:**

1. **502 Bad Gateway or Connection Closed**
   - **Cause:** Nginx proxy_pass configuration issue or service not running
   - **Check:** `docker logs homeiq-dashboard | grep -i error`
   - **Solution:** Verify service names and ports match docker-compose.yml

2. **"host not found in upstream" Error**
   - **Cause:** Nginx tries to resolve hostname at startup, but service isn't running
   - **Solution:** Use variable-based proxy_pass with resolver for optional services:
   ```nginx
   location /service-name/ {
       set $service "http://service-name:port";
       proxy_pass $service/;
       # Resolver already configured at server level
   }
   ```

3. **Proxy Returns Wrong Endpoint (Root Instead of Target)**
   - **Cause:** Variable-based proxy_pass not forwarding path correctly
   - **Solution:** Use direct proxy_pass for always-running services, or use upstream blocks:
   ```nginx
   # For always-running services
   location /api/integrations {
       proxy_pass http://data_api/api/integrations;
   }
   
   # For optional services (with resolver)
   location /weather/ {
       set $weather_service "http://weather-api:8009";
       proxy_pass $weather_service/;
   }
   ```

**Nginx Configuration Best Practices:**
- **Always-running services:** Use direct `proxy_pass` or upstream blocks
- **Optional services:** Use variable-based `proxy_pass` with resolver (allows nginx to start even if service isn't running)
- **Service name changes:** Update both docker-compose.yml and nginx.conf (e.g., `ai-automation-service` → `ai-automation-service-new`)
- **Port changes:** Verify internal ports match (e.g., `ai-automation-service-new` uses port 8025 internally, not 8018)

**Verification:**
```bash
# Test proxy endpoints
curl http://localhost:3000/setup-service/api/health/environment
curl http://localhost:3000/api/integrations
curl http://localhost:3000/log-aggregator/health
curl http://localhost:3000/ai-automation/health

# Check nginx config syntax
docker exec homeiq-dashboard nginx -t

# View nginx logs
docker logs homeiq-dashboard --tail 50
```

### Authentication Issues (401 Unauthorized)

**Dashboard Endpoints Requiring Public Access:**
- `/api/v1/config/integrations/mqtt` (GET/PUT) - MQTT configuration for dashboard
- `/api/v1/real-time-metrics` - Real-time metrics for dashboard display

**If Dashboard Shows "Authentication Required":**
1. Check admin-api service is running: `curl http://localhost:8004/health`
2. Verify endpoints are registered as public (no `dependencies=secure_dependency`)
3. Check frontend API calls include proper headers
4. Review `services/admin-api/src/main.py` router configuration

### Health Score Showing 0/100

**Cause:** Health scoring algorithm returns 0 when data is incomplete

**Fixed (December 2025):**
- HA Core "error/unknown" now scores 25 instead of 0
- Empty integrations list scores 30 instead of 0
- 0ms response time scores 80 instead of causing issues

**Verification:**
```bash
curl http://localhost:8027/api/health/environment
# Should return health_score > 0 even with partial data
```

### High Error Rate

**Check:**
- Service logs for error patterns
- Resource usage: `docker stats`
- Network connectivity
- Database connectivity (InfluxDB)

### Performance Issues

**Check:**
- Resource usage: `docker stats`
- Response times: `./scripts/check-service-health.sh`
- Database query performance
- Network latency

---

## Maintenance

### Regular Tasks

**Daily:**
- Review health check reports
- Monitor error logs
- Check service uptime

**Weekly:**
- Review service logs for issues
- Check disk space usage
- Verify backup procedures

**Monthly:**
- Review and update dependencies
- Check security updates
- Review performance metrics

### Updates

**Procedure:**
1. Review changelog
2. Test in staging environment
3. Backup current deployment
4. Deploy updates
5. Verify health
6. Monitor for issues

---

## Emergency Contacts

- **On-Call Engineer:** [Contact Info]
- **DevOps Team:** [Contact Info]
- **Security Team:** [Contact Info]

---

## Deployment Tracking

### View Deployment History

```bash
# List recent deployments
python scripts/deployment/track-deployment.py --list

# Show deployment metrics
python scripts/deployment/track-deployment.py --metrics
```

### Metrics Available

- Total deployments
- Success/failure rates
- Average deployment duration
- Rollback frequency
- Mean time to recovery (MTTR)
- Recent deployments (7 days)

## Notifications

### Automated Notifications

Deployments automatically send notifications to:
- **Slack** (if `SLACK_WEBHOOK_URL` configured)
- **Email** (if configured, for failures only)
- **Custom Webhook** (if `DEPLOYMENT_WEBHOOK_URL` configured)
- **GitHub Actions** (workflow summary)

### Manual Notifications

For manual deployments, notifications can be sent via:

```bash
# Send notification via workflow
gh workflow run deployment-notify.yml \
  -f deployment-id="deploy-$(date +%Y%m%d-%H%M%S)" \
  -f status="success" \
  -f commit=$(git rev-parse HEAD) \
  -f branch=$(git branch --show-current)
```

## References

- [Deployment Pipeline Documentation](./DEPLOYMENT_PIPELINE.md) - Complete pipeline architecture
- [Nginx Proxy Configuration Guide](./NGINX_PROXY_CONFIGURATION.md) - Detailed nginx proxy patterns and troubleshooting
- [Synergies API Deployment Notes](./SYNERGIES_API_DEPLOYMENT_NOTES.md) - Critical deployment notes for synergies API route fixes
- [Test Strategy](../testing/TEST_STRATEGY.md)
- [Security Audit](../security/SECURITY_AUDIT_REPORT.md)
- [Production Readiness Components](../architecture/production-readiness-components.md)
- [Troubleshooting Guide](../TROUBLESHOOTING_GUIDE.md)

---

**Maintainer:** DevOps Team  
**Review Frequency:** Quarterly  
**Last Review:** December 27, 2025

