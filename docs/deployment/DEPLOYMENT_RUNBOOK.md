# HomeIQ Deployment Runbook

**Last Updated:** December 27, 2025  
**Status:** Active  
**Version:** 2.0

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
- [Test Strategy](../testing/TEST_STRATEGY.md)
- [Security Audit](../security/SECURITY_AUDIT_REPORT.md)
- [Production Readiness Components](../architecture/production-readiness-components.md)
- [Troubleshooting Guide](../TROUBLESHOOTING_GUIDE.md)

---

**Maintainer:** DevOps Team  
**Review Frequency:** Quarterly  
**Last Review:** December 27, 2025

