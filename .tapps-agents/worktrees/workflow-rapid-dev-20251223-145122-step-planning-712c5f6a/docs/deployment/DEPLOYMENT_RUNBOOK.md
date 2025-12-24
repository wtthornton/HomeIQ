# HomeIQ Deployment Runbook

**Last Updated:** December 3, 2025  
**Status:** Active

---

## Overview

This runbook provides step-by-step instructions for deploying HomeIQ to production, including pre-deployment checks, deployment procedures, and post-deployment verification.

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

## Deployment Procedure

### Step 1: Build Docker Images

```bash
# Build all services
docker-compose build

# Or build specific service
docker-compose build <service-name>
```

**Expected Time:** 5-15 minutes  
**Verification:** Check for build errors

### Step 2: Start Services

```bash
# Start all services
docker-compose up -d

# Or start specific service
docker-compose up -d <service-name>
```

**Expected Time:** <1 minute  
**Verification:** Check container status

```bash
docker-compose ps
```

### Step 3: Verify Service Health

```bash
# Run health check script
./scripts/check-service-health.sh

# Or check individual services
curl http://localhost:8001/health  # websocket-ingestion
curl http://localhost:8006/health  # data-api
curl http://localhost:8003/api/v1/health  # admin-api
```

**Expected Result:** All critical services return HTTP 200

### Step 4: Run Smoke Tests

```bash
# Run smoke tests
python tests/smoke_tests.py

# Or with pytest
pytest tests/test_smoke_critical_paths.py -v
```

**Expected Result:** All critical path tests pass

---

## Post-Deployment Verification

### 1. Service Health Check

```bash
# Automated health check
./scripts/check-service-health.sh --json > health-report.json

# Check critical services only
./scripts/check-service-health.sh --critical-only
```

**Success Criteria:**
- All critical services healthy (HTTP 200)
- Response times < 500ms
- No connection errors

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

### If Deployment Fails

1. **Stop Services:**
   ```bash
   docker-compose down
   ```

2. **Restore Previous Version:**
   ```bash
   git checkout <previous-commit>
   docker-compose build
   docker-compose up -d
   ```

3. **Verify Rollback:**
   ```bash
   ./scripts/check-service-health.sh
   ```

### If Service Degrades

1. **Identify Failing Service:**
   ```bash
   ./scripts/check-service-health.sh
   docker-compose ps
   ```

2. **Check Logs:**
   ```bash
   docker-compose logs <service-name>
   ```

3. **Restart Service:**
   ```bash
   docker-compose restart <service-name>
   ```

4. **If Persistent, Rollback:**
   - Follow rollback procedure above

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

## References

- [Test Strategy](../testing/TEST_STRATEGY.md)
- [Security Audit](../security/SECURITY_AUDIT_REPORT.md)
- [Production Readiness Components](../../docs/architecture/production-readiness-components.md)
- [Troubleshooting Guide](../troubleshooting/TROUBLESHOOTING_GUIDE.md)

---

**Maintainer:** DevOps Team  
**Review Frequency:** Quarterly

