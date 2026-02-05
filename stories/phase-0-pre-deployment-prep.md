---
epic: homeiq-rebuild-deployment
phase: 0
priority: critical
status: in-progress
estimated_duration: 1 day
---

# Phase 0: Pre-Deployment Preparation

**Epic:** HomeIQ Rebuild and Deployment
**Phase:** 0 (Pre-Deployment Preparation)
**Priority:** CRITICAL
**Estimated Duration:** 1 day (8 hours)
**Status:** In Progress

## Overview

Prepare the HomeIQ platform (48 microservices) for a comprehensive rebuild and deployment. This phase focuses on:
1. Creating complete backups of current state
2. Diagnosing and fixing the unhealthy websocket-ingestion service
3. Verifying Python/Node.js versions across all services
4. Validating infrastructure requirements
5. Setting up build monitoring and logging

**Current State:**
- 43/44 services healthy
- 1 UNHEALTHY service: websocket-ingestion (CRITICAL)
- Services running for 47 hours
- Docker Compose v2.0+ with BuildKit enabled

---

## Story 1: Create Comprehensive System Backup

**As a** DevOps engineer
**I want** complete backups of all Docker volumes and configuration files
**So that** I can safely rollback if the rebuild fails

### Acceptance Criteria

✅ **AC1:** Docker volumes backed up
- [ ] InfluxDB data volume backed up to `backups/influxdb_data_[timestamp].tar.gz`
- [ ] SQLite data volume backed up to `backups/sqlite_data_[timestamp].tar.gz`
- [ ] Backups verified (can be extracted successfully)
- [ ] Backup size and integrity logged

✅ **AC2:** Configuration files backed up
- [ ] `.env` file backed up to `.env.backup_[timestamp]`
- [ ] `docker-compose.yml` backed up to `docker-compose.yml.backup_[timestamp]`
- [ ] All `infrastructure/.env.*` files backed up
- [ ] Git status captured (tracked/untracked files)

✅ **AC3:** Docker images cataloged
- [ ] Current images list exported to `current_images.txt`
- [ ] Image sizes and tags documented
- [ ] Image creation dates recorded

✅ **AC4:** Backup verification
- [ ] All backup files exist and are non-zero size
- [ ] Backup manifest created with checksums
- [ ] Restoration procedure documented

### Tasks

**Task 1.1: Backup Docker Volumes** (30 min)
```bash
# Create backups directory
mkdir -p backups

# Backup InfluxDB data
docker run --rm -v homeiq_influxdb_data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/influxdb_data_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Backup SQLite data
docker run --rm -v homeiq_sqlite-data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/sqlite_data_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Verify backups
ls -lh backups/
```

**Task 1.2: Backup Configuration Files** (15 min)
```bash
# Backup environment files
cp .env .env.backup_$(date +%Y%m%d_%H%M%S)
cp docker-compose.yml docker-compose.yml.backup_$(date +%Y%m%d_%H%M%S)
cp -r infrastructure infrastructure.backup_$(date +%Y%m%d_%H%M%S)

# Capture git status
git status > git_status_$(date +%Y%m%d_%H%M%S).txt
```

**Task 1.3: Export Docker Images List** (10 min)
```bash
# Export images list
docker images --format "{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep homeiq > current_images.txt

# Tag current images for safety
for img in $(docker images --format "{{.Repository}}" | grep homeiq | sort -u); do
  docker tag $img:latest $img:pre-rebuild
done
```

**Task 1.4: Create Backup Manifest** (15 min)
```bash
# Create manifest with checksums
cd backups
sha256sum *.tar.gz > backup_manifest_$(date +%Y%m%d_%H%M%S).txt
cd ..
```

### Story Points: 3
### Estimated Effort: 1.5 hours
### Dependencies: None
### Risk: LOW

---

## Story 2: Diagnose and Fix Unhealthy WebSocket Ingestion Service

**As a** DevOps engineer
**I want** the websocket-ingestion service to be healthy
**So that** Home Assistant events are properly ingested during rebuild

### Acceptance Criteria

✅ **AC1:** Diagnostic data captured
- [ ] Service logs captured (last 500 lines)
- [ ] Container inspection data saved
- [ ] Resource usage statistics recorded
- [ ] Health check endpoint tested manually

✅ **AC2:** Connectivity verified
- [ ] InfluxDB connectivity tested from container
- [ ] Home Assistant HTTP endpoint tested
- [ ] Environment variables verified
- [ ] Network connectivity confirmed

✅ **AC3:** Service restored to healthy state
- [ ] Health check endpoint returns 200 OK
- [ ] Service logs show no errors
- [ ] Events being ingested successfully
- [ ] Service stable for 30+ minutes

✅ **AC4:** Root cause documented
- [ ] Issue identified and documented
- [ ] Fix applied and tested
- [ ] Prevention measures noted
- [ ] Incident report created

### Tasks

**Task 2.1: Capture Diagnostic Information** (20 min)
```bash
# Create diagnostics directory
mkdir -p diagnostics/websocket-ingestion

# Capture logs
docker logs homeiq-websocket --tail 500 > diagnostics/websocket-ingestion/logs_$(date +%Y%m%d_%H%M%S).txt

# Capture inspection data
docker inspect homeiq-websocket > diagnostics/websocket-ingestion/inspect_$(date +%Y%m%d_%H%M%S).json

# Capture resource stats
docker stats homeiq-websocket --no-stream > diagnostics/websocket-ingestion/stats_$(date +%Y%m%d_%H%M%S).txt

# Test health endpoint
curl -v http://localhost:8001/health 2>&1 | tee diagnostics/websocket-ingestion/health_check_$(date +%Y%m%d_%H%M%S).txt
```

**Task 2.2: Test Connectivity** (15 min)
```bash
# Test InfluxDB connectivity
docker exec homeiq-websocket curl -f http://influxdb:8086/health || echo "InfluxDB unreachable"

# Test Home Assistant connectivity (if available)
docker exec homeiq-websocket curl -f $HA_HTTP_URL/api/ || echo "HA unreachable"

# Verify environment variables
docker exec homeiq-websocket env | grep -E "HA_|INFLUX" > diagnostics/websocket-ingestion/env_vars.txt

# Check DNS resolution
docker exec homeiq-websocket nslookup influxdb || echo "DNS issue detected"
```

**Task 2.3: Attempt Service Recovery** (30 min)
```bash
# Option 1: Restart service
docker restart homeiq-websocket

# Wait and check status
sleep 30
docker ps --filter name=websocket --format "{{.Status}}"

# If still unhealthy, check logs again
docker logs homeiq-websocket --tail 100

# Option 2: Rebuild if restart fails
if [ "$(docker inspect homeiq-websocket --format='{{.State.Health.Status}}')" != "healthy" ]; then
  echo "Restart failed, attempting rebuild..."
  docker-compose build --no-cache websocket-ingestion
  docker-compose up -d websocket-ingestion
fi

# Monitor for 30 minutes
watch -n 60 'docker ps --filter name=websocket --format "{{.Status}}"'
```

**Task 2.4: Document Root Cause and Fix** (25 min)
- Analyze diagnostic data to identify root cause
- Document issue in incident report
- Note fix applied and validation steps
- Add prevention measures to deployment checklist

### Story Points: 5
### Estimated Effort: 1.5 hours
### Dependencies: Story 1 (backups completed first)
### Risk: MEDIUM-HIGH (critical service, unknown root cause)

---

## Story 3: Verify Python Versions Across All Services

**As a** Platform engineer
**I want** to know the Python version in each service
**So that** I can plan upgrades for services below Python 3.10

### Acceptance Criteria

✅ **AC1:** Python versions documented for all Python services
- [ ] Python version checked in all 45+ Python containers
- [ ] Results saved to `python_versions_audit.csv`
- [ ] Services below Python 3.10 identified
- [ ] Upgrade priority assigned to each service

✅ **AC2:** Version matrix created
- [ ] Service name, current version, target version documented
- [ ] Dockerfile Python base image identified
- [ ] Upgrade complexity estimated (low/medium/high)
- [ ] Dependencies on Python version noted

✅ **AC3:** Upgrade plan outlined
- [ ] Services grouped by upgrade priority
- [ ] Dockerfile update strategy defined
- [ ] Testing requirements identified
- [ ] Rollout sequence planned

### Tasks

**Task 3.1: Check Python Versions in All Containers** (45 min)
```bash
# Create audit file
echo "Service,Python Version,Status,Base Image" > python_versions_audit.csv

# Check all Python services
for service in \
  data-api websocket-ingestion admin-api data-retention \
  weather-api sports-api carbon-intensity electricity-pricing \
  air-quality calendar-service smart-meter-service log-aggregator \
  ai-core-service ai-pattern-service ai-automation-service-new \
  ai-query-service ai-training-service ai-code-executor \
  ha-ai-agent-service proactive-agent-service ml-service \
  openvino-service rag-service openai-service ner-service \
  device-intelligence-service device-health-monitor \
  device-context-classifier device-database-client \
  device-recommender device-setup-assistant ha-setup-service \
  automation-linter automation-miner blueprint-index \
  blueprint-suggestion-service yaml-validation-service \
  api-automation-edge energy-correlator rule-recommendation-ml; do

  echo "Checking $service..."
  version=$(docker exec homeiq-$service python --version 2>&1 || echo "N/A")
  base_image=$(docker inspect homeiq-$service --format='{{.Config.Image}}' 2>/dev/null || echo "N/A")

  echo "$service,$version,$([ \"$version\" \< \"Python 3.10\" ] && echo \"NEEDS_UPGRADE\" || echo \"OK\"),$base_image" >> python_versions_audit.csv
done

# Display results
cat python_versions_audit.csv | column -t -s,
```

**Task 3.2: Identify Dockerfiles and Base Images** (30 min)
```bash
# Find all Dockerfiles
find services/ -name "Dockerfile" -o -name "Dockerfile.dev" > dockerfiles_list.txt

# Extract Python base images
for dockerfile in $(cat dockerfiles_list.txt); do
  echo "=== $dockerfile ==="
  grep -E "^FROM python:" $dockerfile || echo "No Python base image found"
done > dockerfile_python_versions.txt
```

**Task 3.3: Create Upgrade Matrix** (30 min)
- Analyze audit results
- Group services by current Python version
- Identify services requiring upgrade (< 3.10)
- Estimate complexity based on dependencies
- Create prioritized upgrade plan

**Task 3.4: Document Upgrade Strategy** (15 min)
- Define Dockerfile update approach
- Identify testing requirements per service
- Plan rollout sequence (low-risk first)
- Document in `docs/planning/python-upgrade-strategy.md`

### Story Points: 5
### Estimated Effort: 2 hours
### Dependencies: None (can run in parallel with Stories 1-2)
### Risk: LOW

---

## Story 4: Verify Infrastructure Requirements

**As a** DevOps engineer
**I want** to validate infrastructure meets rebuild requirements
**So that** the rebuild process completes successfully

### Acceptance Criteria

✅ **AC1:** Docker environment validated
- [ ] Docker version ≥ 20.10 confirmed
- [ ] Docker Compose version ≥ v2.0 confirmed
- [ ] BuildKit enabled and functional
- [ ] Docker daemon responsive and healthy

✅ **AC2:** System resources verified
- [ ] Available memory ≥ 16GB confirmed
- [ ] Available disk space ≥ 50GB confirmed
- [ ] CPU cores ≥ 4 confirmed
- [ ] No resource constraints detected

✅ **AC3:** Node.js versions checked
- [ ] Node.js version in health-dashboard container
- [ ] Node.js version in ai-automation-ui container
- [ ] Node.js ≥ 18.x confirmed for Vite 6
- [ ] Upgrade path to Node.js 20+ documented

✅ **AC4:** Infrastructure report generated
- [ ] All checks passed or documented
- [ ] Upgrade requirements identified
- [ ] Infrastructure blockers noted
- [ ] Remediation plan created if needed

### Tasks

**Task 4.1: Verify Docker Environment** (15 min)
```bash
# Check Docker version
docker --version  # Should be 20.10+
docker info | grep -i version

# Check Docker Compose version
docker compose version  # Should be v2.0+

# Verify BuildKit
docker buildx version

# Test BuildKit functionality
export DOCKER_BUILDKIT=1
docker buildx ls
```

**Task 4.2: Check System Resources** (20 min)
```bash
# Check available memory
free -h | tee infrastructure_resources.txt

# Check disk space
df -h | tee -a infrastructure_resources.txt

# Check CPU
nproc
lscpu | grep -E "Model name|CPU\(s\):" | tee -a infrastructure_resources.txt

# Check Docker stats
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | tee docker_stats.txt
```

**Task 4.3: Verify Node.js Versions** (15 min)
```bash
# Check health-dashboard
docker exec homeiq-dashboard node --version 2>/dev/null || echo "health-dashboard: N/A"

# Check ai-automation-ui
docker exec ai-automation-ui node --version 2>/dev/null || echo "ai-automation-ui: N/A"

# Document in audit file
echo "Frontend Service,Node.js Version,Required,Status" > nodejs_versions_audit.csv
echo "health-dashboard,$(docker exec homeiq-dashboard node --version 2>/dev/null),18.x+,$([ \"$(docker exec homeiq-dashboard node --version 2>/dev/null | cut -d. -f1 | tr -d 'v')\" -ge 18 ] && echo \"OK\" || echo \"NEEDS_UPGRADE\")" >> nodejs_versions_audit.csv
echo "ai-automation-ui,$(docker exec ai-automation-ui node --version 2>/dev/null),18.x+,$([ \"$(docker exec ai-automation-ui node --version 2>/dev/null | cut -d. -f1 | tr -d 'v')\" -ge 18 ] && echo \"OK\" || echo \"NEEDS_UPGRADE\")" >> nodejs_versions_audit.csv

cat nodejs_versions_audit.csv | column -t -s,
```

**Task 4.4: Generate Infrastructure Report** (30 min)
- Compile all infrastructure checks
- Identify any blockers or warnings
- Document upgrade requirements
- Create remediation plan if needed
- Save to `infrastructure_validation_report.md`

### Story Points: 3
### Estimated Effort: 1.5 hours
### Dependencies: None (can run in parallel)
### Risk: LOW

---

## Story 5: Set Up Build Monitoring and Logging

**As a** DevOps engineer
**I want** comprehensive build monitoring and logging
**So that** I can track rebuild progress and troubleshoot issues

### Acceptance Criteria

✅ **AC1:** BuildKit configured for detailed output
- [ ] DOCKER_BUILDKIT=1 environment variable set
- [ ] BUILDKIT_PROGRESS=plain configured
- [ ] COMPOSE_DOCKER_CLI_BUILD=1 set
- [ ] BuildKit cache mounts enabled

✅ **AC2:** Build log directories created
- [ ] `logs/rebuild_[date]/` directory structure created
- [ ] Subdirectories for each phase (0-4) created
- [ ] Log rotation configured
- [ ] Disk space monitoring enabled

✅ **AC3:** Monitoring scripts deployed
- [ ] Service health monitoring script created
- [ ] Resource usage monitoring script created
- [ ] Error log aggregation script created
- [ ] Build progress dashboard script created

✅ **AC4:** Monitoring validated
- [ ] Scripts execute successfully
- [ ] Logs being captured correctly
- [ ] Alerts configured for failures
- [ ] Dashboard accessible

### Tasks

**Task 5.1: Configure BuildKit** (10 min)
```bash
# Enable BuildKit with detailed progress
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain
export COMPOSE_DOCKER_CLI_BUILD=1

# Persist in environment
cat >> ~/.bashrc <<EOF
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain
export COMPOSE_DOCKER_CLI_BUILD=1
EOF

# Verify
echo "DOCKER_BUILDKIT=$DOCKER_BUILDKIT"
echo "BUILDKIT_PROGRESS=$BUILDKIT_PROGRESS"
```

**Task 5.2: Create Build Log Directories** (10 min)
```bash
# Create log structure
mkdir -p logs/rebuild_$(date +%Y%m%d)/{phase0,phase1,phase2,phase3,phase4,deployment}

# Create log symlink for current rebuild
ln -sf logs/rebuild_$(date +%Y%m%d) logs/current_rebuild

# Create logs for each phase
for phase in phase0 phase1 phase2 phase3 phase4 deployment; do
  mkdir -p logs/current_rebuild/$phase/{build,test,health,errors}
done
```

**Task 5.3: Create Monitoring Scripts** (45 min)

Create `scripts/monitor-health.sh`:
```bash
#!/bin/bash
# Monitor service health continuously
while true; do
  echo "=== $(date) ==="
  docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "homeiq|NAMES"
  echo ""
  sleep 300  # Every 5 minutes
done | tee -a logs/current_rebuild/phase0/health/health_monitor.log
```

Create `scripts/monitor-resources.sh`:
```bash
#!/bin/bash
# Monitor resource usage
while true; do
  echo "=== $(date) ==="
  docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
  echo ""
  sleep 300  # Every 5 minutes
done | tee -a logs/current_rebuild/phase0/health/resource_monitor.log
```

Create `scripts/aggregate-errors.sh`:
```bash
#!/bin/bash
# Aggregate errors from all containers
for container in $(docker ps --filter name=homeiq --format "{{.Names}}"); do
  echo "=== Errors from $container ===" >> logs/current_rebuild/phase0/errors/all_errors.log
  docker logs $container --since 1h 2>&1 | grep -i -E "error|exception|failed|critical" >> logs/current_rebuild/phase0/errors/all_errors.log
done
```

**Task 5.4: Start Monitoring** (15 min)
```bash
# Make scripts executable
chmod +x scripts/monitor-*.sh scripts/aggregate-errors.sh

# Start monitoring in background
nohup ./scripts/monitor-health.sh &
nohup ./scripts/monitor-resources.sh &

# Schedule error aggregation (every hour)
(crontab -l 2>/dev/null; echo "0 * * * * cd $(pwd) && ./scripts/aggregate-errors.sh") | crontab -

# Verify monitoring running
ps aux | grep monitor
tail -f logs/current_rebuild/phase0/health/health_monitor.log
```

### Story Points: 3
### Estimated Effort: 1.5 hours
### Dependencies: None (can run in parallel)
### Risk: LOW

---

## Phase 0 Summary

### Total Estimates
- **Story Points:** 19
- **Total Effort:** 8 hours (1 day)
- **Risk Level:** MEDIUM (due to websocket-ingestion service)

### Execution Order
1. **Story 1** (Backups) - MUST complete first (1.5 hours)
2. **Story 2** (WebSocket Fix) - Critical path (1.5 hours)
3. **Stories 3, 4, 5** - Can run in parallel (5 hours total, 2 hours if parallel)

### Success Criteria

Phase 0 is complete when:
- ✅ All backups created and verified
- ✅ websocket-ingestion service healthy
- ✅ Python versions documented for all services
- ✅ Infrastructure validated and ready
- ✅ Build monitoring operational

### Blockers & Risks

**Blocker 1: WebSocket Service Recovery**
- Risk: HIGH
- Impact: Cannot proceed to Phase 1 without healthy ingestion
- Mitigation: Allocate extra time, have rebuild plan ready

**Blocker 2: Python Version Incompatibility**
- Risk: MEDIUM
- Impact: May need Dockerfile updates before rebuild
- Mitigation: Document all requirements in Phase 0

**Blocker 3: Insufficient Resources**
- Risk: LOW
- Impact: Build failures or performance issues
- Mitigation: Verify resources in Story 4, upgrade if needed

### Next Phase

After Phase 0 completion:
→ **Phase 1: Critical Compatibility Fixes** (Week 1)
- Update SQLAlchemy, aiosqlite, FastAPI
- Standardize Pydantic, httpx versions
- Rebuild 15+ services

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-02-04 | Claude Code | Initial Phase 0 breakdown created |
