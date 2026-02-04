# Phase 1: Automated Batch Rebuild Guide

**Date:** February 4, 2026
**Status:** Ready for Execution
**Target:** 40 Services
**Framework:** TappsCodingAgents with Context7 MCP

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Service Categories](#service-categories)
5. [Usage Examples](#usage-examples)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)
9. [Advanced Configuration](#advanced-configuration)

---

## Overview

### What This Does

The Phase 1 automated batch rebuild system provides:

✅ **Parallel Batch Processing** - Rebuild multiple services simultaneously (default: 5 at a time)
✅ **BuildKit Optimization** - Fast, cached builds with layer optimization
✅ **Automated Health Checks** - Verify service health after each rebuild
✅ **Rollback Support** - Automatic rollback on critical failures
✅ **Real-time Monitoring** - Live dashboard showing rebuild progress
✅ **State Management** - Resume from failures with `--continue` flag
✅ **Context7 Integration** - Library documentation and pattern lookup

### Services Covered

**40 Services** organized into 7 categories:

| Category | Count | Examples |
|----------|-------|----------|
| Integration | 8 | weather-api, sports-api, calendar-service |
| AI/ML | 13 | ai-core-service, ml-service, rag-service |
| Device | 7 | device-intelligence-service, device-health-monitor |
| Automation | 6 | automation-linter, blueprint-index |
| Analytics | 2 | energy-correlator, energy-forecasting |
| Frontend | 2 | health-dashboard, ai-automation-ui |
| Other | 2 | observability-dashboard, ha-simulator |

### Library Upgrades Applied

**Phase 1 Critical Compatibility Fixes:**

- **SQLAlchemy:** 1.4.x → 2.0.35+ (breaking changes, async support)
- **aiosqlite:** Current → 0.22.1+ (async improvements)
- **FastAPI:** 0.115.0+ → 0.119.0+ (performance improvements)
- **Pydantic:** Standardize on 2.12.0+ (consistency)
- **httpx:** 0.27.x → 0.28.1+ (HTTP client improvements)

---

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 1 Batch Rebuild System                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   Orchestrator    │
                    │  (Master Script)  │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ Batch 1 │          │ Batch 2 │          │ Batch N │
   │ (5 svc) │          │ (5 svc) │          │ (5 svc) │
   └────┬────┘          └────┬────┘          └────┬────┘
        │                     │                     │
   ┌────▼───────────────┐────▼───────────────┐────▼──────────────┐
   │ Parallel Builders  │ Parallel Builders  │ Parallel Builders │
   ├────────────────────┤────────────────────┤───────────────────┤
   │ • Build (Docker)   │ • Build (Docker)   │ • Build (Docker)  │
   │ • Test (pytest)    │ • Test (pytest)    │ • Test (pytest)   │
   │ • Health Check     │ • Health Check     │ • Health Check    │
   │ • State Update     │ • State Update     │ • State Update    │
   └────────────────────┘────────────────────┘───────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   State Manager   │
                    │  (JSON tracking)  │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ Logging │          │ Monitor │          │Rollback │
   │ System  │          │Dashboard│          │ Support │
   └─────────┘          └─────────┘          └─────────┘
```

### Key Components

1. **phase1-batch-rebuild.sh** - Main orchestration script
2. **phase1-monitor-rebuild.sh** - Real-time monitoring dashboard
3. **phase1-service-config.yaml** - Service definitions and configuration
4. **.rebuild_state_phase1.json** - State tracking (auto-generated)

---

## Quick Start

### Prerequisites

```bash
# 1. Verify Phase 0 completed
cat REBUILD_STATUS.md

# 2. Ensure BuildKit enabled
source .env.buildkit

# 3. Check Docker resources
docker system df
docker stats --no-stream | head -5

# 4. Verify backups exist
ls -lh backups/
```

### Basic Usage

**Option 1: Rebuild All Services (Recommended)**

```bash
# Default: 5 services per batch
./scripts/phase1-batch-rebuild.sh

# With monitoring in another terminal
./scripts/phase1-monitor-rebuild.sh
```

**Option 2: Test with Dry Run**

```bash
# See what would happen without executing
./scripts/phase1-batch-rebuild.sh --dry-run
```

**Option 3: Rebuild by Category**

```bash
# Rebuild only integration services first (8 services)
./scripts/phase1-batch-rebuild.sh --category integration

# Then AI/ML services (13 services)
./scripts/phase1-batch-rebuild.sh --category ai-ml
```

**Option 4: Custom Batch Size**

```bash
# Larger batches for faster execution (requires more resources)
./scripts/phase1-batch-rebuild.sh --batch-size 8

# Smaller batches for conservative approach
./scripts/phase1-batch-rebuild.sh --batch-size 3
```

---

## Service Categories

### 1. Integration Services (8)

**Purpose:** External API integrations (weather, sports, calendar, etc.)
**Risk Level:** LOW
**Dependencies:** None
**Recommended:** Start here for validation

```bash
./scripts/phase1-batch-rebuild.sh --category integration
```

**Services:**
- weather-api (Port 8009)
- sports-api (Port 8005)
- carbon-intensity-service (Port 8010)
- electricity-pricing-service (Port 8011)
- air-quality-service (Port 8012)
- calendar-service (Port 8013)
- smart-meter-service (Port 8014)
- log-aggregator (Port 8015)

---

### 2. AI/ML Services (13)

**Purpose:** AI/ML processing and inference
**Risk Level:** MEDIUM-HIGH
**Dependencies:** None (Phase 3 will handle NumPy 2.x/Pandas 3.0)
**Note:** Phase 1 only updates FastAPI/Pydantic, no ML library changes

```bash
./scripts/phase1-batch-rebuild.sh --category ai-ml
```

**Services:**
- ai-core-service (Port 8018) - CRITICAL
- ai-pattern-service (Port 8034)
- ai-automation-service-new (Port 8036)
- ai-query-service (Port 8035)
- ai-training-service (Port 8033)
- ai-code-executor (Port 8030)
- ha-ai-agent-service (Port 8030)
- proactive-agent-service (Port 8031)
- ml-service (Port 8020) - CRITICAL
- openvino-service (Port 8032)
- rag-service (Port 8037)
- nlp-fine-tuning (Port 8038)
- rule-recommendation-ml (Port 8039)

---

### 3. Device Services (7)

**Purpose:** Device management and intelligence
**Risk Level:** MEDIUM
**Dependencies:** None

```bash
./scripts/phase1-batch-rebuild.sh --category device
```

**Services:**
- device-intelligence-service (Port 8019) - CRITICAL
- device-context-classifier (Port 8021)
- device-database-client (Port 8022)
- device-health-monitor (Port 8023)
- device-recommender (Port 8024)
- device-setup-assistant (Port 8025)
- model-prep (Port 8026)

---

### 4. Automation Services (6)

**Purpose:** Automation linting and blueprint management
**Risk Level:** LOW
**Dependencies:** None

```bash
./scripts/phase1-batch-rebuild.sh --category automation
```

**Services:**
- automation-linter (Port 8016) - **Most outdated FastAPI version!**
- automation-miner (Port 8017)
- blueprint-index (Port 8027)
- blueprint-suggestion-service (Port 8028)
- yaml-validation-service (Port 8029)
- api-automation-edge (Port 8040)

---

### 5. Analytics Services (2)

**Purpose:** Energy analytics and forecasting
**Risk Level:** LOW
**Dependencies:** None

```bash
./scripts/phase1-batch-rebuild.sh --category analytics
```

**Services:**
- energy-correlator (Port 8041)
- energy-forecasting (Port 8042)

---

### 6. Frontend Services (2)

**Purpose:** React/Node.js web applications
**Risk Level:** LOW (conservative updates)
**Dependencies:** None
**Note:** Staying on React 18, Vite 6 for Phase 1

```bash
./scripts/phase1-batch-rebuild.sh --category frontend
```

**Services:**
- health-dashboard (Port 3000) - CRITICAL
- ai-automation-ui (Port 3001) - CRITICAL

---

### 7. Other Services (2)

**Purpose:** Observability and simulation
**Risk Level:** LOW
**Dependencies:** None

```bash
./scripts/phase1-batch-rebuild.sh --category other
```

**Services:**
- observability-dashboard (Port 8501)
- ha-simulator (Port 8043)

---

## Usage Examples

### Example 1: Safe Production Rollout

```bash
# Step 1: Dry run to validate
./scripts/phase1-batch-rebuild.sh --dry-run

# Step 2: Start monitoring in separate terminal
./scripts/phase1-monitor-rebuild.sh

# Step 3: Rebuild integration services (lowest risk)
./scripts/phase1-batch-rebuild.sh --category integration --rollback-on-fail

# Step 4: Verify health
docker-compose ps | grep integration

# Step 5: Continue with other categories
./scripts/phase1-batch-rebuild.sh --category automation --rollback-on-fail
./scripts/phase1-batch-rebuild.sh --category analytics --rollback-on-fail
./scripts/phase1-batch-rebuild.sh --category device --rollback-on-fail
./scripts/phase1-batch-rebuild.sh --category ai-ml --rollback-on-fail
./scripts/phase1-batch-rebuild.sh --category frontend --rollback-on-fail
./scripts/phase1-batch-rebuild.sh --category other --rollback-on-fail
```

### Example 2: Fast Development Rebuild

```bash
# Rebuild all at once with larger batches
./scripts/phase1-batch-rebuild.sh --batch-size 10 --skip-tests
```

### Example 3: Conservative Approach

```bash
# Small batches, no cache, auto-rollback
./scripts/phase1-batch-rebuild.sh \
  --batch-size 3 \
  --no-cache \
  --rollback-on-fail
```

### Example 4: Resume from Failure

```bash
# Initial run fails at service 15
./scripts/phase1-batch-rebuild.sh
# ... build errors occur ...

# Fix issues, then continue from where it failed
./scripts/phase1-batch-rebuild.sh --continue
```

---

## Monitoring

### Real-time Dashboard

Launch the monitoring dashboard in a separate terminal:

```bash
./scripts/phase1-monitor-rebuild.sh
```

**Dashboard Shows:**
- Progress bar with completion percentage
- Services completed, failed, pending
- Breakdown by category
- Recent build activity
- Docker container status
- Resource usage (CPU, memory)

**Example Output:**

```
╔══════════════════════════════════════════════════════════════════════════╗
║  HomeIQ Phase 1: Batch Rebuild Monitor
║  2026-02-04 14:32:15
╚══════════════════════════════════════════════════════════════════════════╝

Progress:
  [████████████████████████████░░░░░░░░░░░░░░░░░░░░░░] 57%

Status Summary:
  ✅ Completed: 23 / 40
  ❌ Failed:    2 / 40
  ⏳ Pending:   15 / 40

Services by Category:
  Integration:     [ 8/ 8] ✅ complete
  AI/ML:          [ 7/13] ⋯ 6 pending
  Device:         [ 5/ 7] ⋯ 2 pending
  Automation:     [ 3/ 6] ⋯ 3 pending
  Analytics:      [ 0/ 2] ⋯ 2 pending
  Frontend:       [ 0/ 2] ⋯ 2 pending
  Other:          [ 0/ 2] ⋯ 2 pending
```

### Manual Status Check

```bash
# Check state file
cat .rebuild_state_phase1.json

# View logs for specific service
tail -f logs/phase1_builds/*/weather-api.log

# Check Docker status
docker-compose ps | grep -E "Up|Exit"

# View resource usage
docker stats --no-stream | head -15
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Build Fails - Dependency Resolution

**Error:**
```
ERROR: Could not find a version that satisfies the requirement sqlalchemy>=2.0.35
```

**Solution:**
```bash
# Clear pip cache and rebuild
docker system prune -a
./scripts/phase1-batch-rebuild.sh --no-cache --category integration
```

#### Issue 2: Port Conflicts

**Error:**
```
ERROR: for weather-api  Cannot start service: port is already allocated
```

**Solution:**
```bash
# Find and stop conflicting service
docker ps | grep 8009
docker stop <container-id>

# Or rebuild with port mapping fix
docker-compose down
./scripts/phase1-batch-rebuild.sh
```

#### Issue 3: Health Check Timeout

**Error:**
```
ERROR: Health check timeout: ai-core-service
```

**Solution:**
```bash
# Check logs for startup errors
docker logs homeiq-ai-core-service

# Increase timeout or check service manually
docker exec -it homeiq-ai-core-service curl -f http://localhost:8018/health
```

#### Issue 4: Out of Disk Space

**Error:**
```
ERROR: no space left on device
```

**Solution:**
```bash
# Clean up Docker
docker system prune -a --volumes
docker image prune -a

# Check space
df -h
```

#### Issue 5: Test Failures

**Error:**
```
WARNING: Tests failed: automation-linter
```

**Solution:**
```bash
# Check test logs
cat logs/phase1_builds/*/automation-linter_test.log

# Skip tests if non-critical
./scripts/phase1-batch-rebuild.sh --skip-tests --category automation
```

---

## Rollback Procedures

### Automatic Rollback

Enable automatic rollback on critical failures:

```bash
./scripts/phase1-batch-rebuild.sh --rollback-on-fail
```

This will:
1. Detect build/health check failures
2. Stop failed service
3. Restore from backup tag
4. Restart service with previous version

### Manual Rollback

#### Rollback Single Service

```bash
# Find backup tag
docker images | grep weather-api | grep pre-phase1

# Tag and restart
docker tag homeiq-weather-api:pre-phase1-rebuild-20260204_140000 homeiq-weather-api:latest
docker-compose up -d weather-api
```

#### Rollback Entire Batch

```bash
# Restore all services from backup
BACKUP_TAG="pre-phase1-rebuild-20260204_140000"

for service in weather-api sports-api calendar-service; do
    docker tag homeiq-${service}:${BACKUP_TAG} homeiq-${service}:latest
done

docker-compose up -d
```

#### Full System Rollback

```bash
# Use Phase 0 backup
cd backups/phase0_20260204_111804/
bash restore-backup.sh

# Or manually restore from saved images
docker images --format "{{.Repository}}:{{.Tag}}" | grep "pre-rebuild" | \
  while read img; do
    service=$(echo $img | cut -d: -f1 | sed 's/homeiq-//')
    docker tag $img homeiq-${service}:latest
  done

docker-compose up -d
```

---

## Advanced Configuration

### Custom Batch Processing

Edit `scripts/phase1-service-config.yaml`:

```yaml
batch_config:
  default_batch_size: 8           # Increase for faster builds
  max_parallel_builds: 15         # Max concurrent Docker builds
  build_timeout_seconds: 900      # 15 minutes per build
  test_timeout_seconds: 600       # 10 minutes per test suite

  retry:
    max_attempts: 5               # Retry failed builds
    backoff_seconds: 60
    exponential: true
```

### Resource Limits

Adjust Docker resource limits:

```yaml
resources:
  memory_limit: "4g"              # Increase for ML services
  cpu_limit: "4.0"                # Use more cores
```

### BuildKit Optimization

```yaml
buildkit:
  enabled: true
  cache: true                     # Use build cache
  inline_cache: true              # Embed cache in image
  progress: "plain"               # Detailed output
```

### Context7 Integration

Enable library documentation lookup:

```yaml
context7_integration:
  enabled: true
  library_docs:
    - "sqlalchemy"
    - "fastapi"
    - "pydantic"
  patterns:
    - "async-sqlalchemy"
    - "fastapi-best-practices"
```

---

## Performance Tuning

### Optimal Batch Sizes

Based on system resources:

| System RAM | CPU Cores | Recommended Batch Size |
|------------|-----------|------------------------|
| 8 GB       | 4 cores   | 3-4 services           |
| 16 GB      | 8 cores   | 5-6 services           |
| 32 GB      | 16 cores  | 8-10 services          |
| 64 GB+     | 32 cores  | 12-15 services         |

### Build Time Estimates

With BuildKit caching enabled:

| Category | Services | Est. Build Time |
|----------|----------|-----------------|
| Integration | 8 | 15-20 min |
| AI/ML | 13 | 35-45 min |
| Device | 7 | 20-25 min |
| Automation | 6 | 15-20 min |
| Analytics | 2 | 8-10 min |
| Frontend | 2 | 10-15 min |
| Other | 2 | 8-10 min |
| **Total** | **40** | **~2-3 hours** |

---

## Success Criteria

### Phase 1 Complete When:

- [ ] All 40 services rebuilt successfully
- [ ] All critical services pass health checks
- [ ] Test suite passes (or `--skip-tests` used with justification)
- [ ] No port conflicts
- [ ] Resource usage within limits
- [ ] Monitoring dashboard shows 100% completion
- [ ] State file shows all services "completed"
- [ ] Docker Compose shows all services "Up"

### Validation Commands

```bash
# 1. Check state
cat .rebuild_state_phase1.json | grep -c "completed"  # Should be 40

# 2. Check Docker
docker-compose ps | grep -c "Up"  # Should be 40+

# 3. Check health
docker ps --format "{{.Names}}\t{{.Status}}" | grep "healthy"

# 4. Check logs
find logs/phase1_builds/ -name "*.log" -exec grep -l "ERROR" {} \;

# 5. Run validation script
./scripts/phase1-validate-services.sh
```

---

## Next Steps

### After Phase 1 Completion:

1. **Update Status**
   ```bash
   # Update REBUILD_STATUS.md
   echo "Phase 1: ✅ COMPLETE" >> REBUILD_STATUS.md
   ```

2. **Create Phase 1 Report**
   ```bash
   # Generate completion report
   ./scripts/phase1-generate-report.sh
   ```

3. **Begin Phase 2**
   ```bash
   # Read Phase 2 plan
   cat docs/planning/rebuild-deployment-plan.md | sed -n '/## Phase 2:/,/## Phase 3:/p'

   # Prepare Phase 2
   ./scripts/phase2-prepare.sh
   ```

---

## Support

### Documentation

- **Main Plan:** [docs/planning/rebuild-deployment-plan.md](./rebuild-deployment-plan.md)
- **Library Upgrade Summary:** [upgrade-summary.md](../../upgrade-summary.md)
- **Phase 0 Report:** [phase0-execution-report.md](./phase0-execution-report.md)

### Logs

- **Build Logs:** `logs/phase1_builds/<timestamp>/`
- **Master Log:** `logs/phase1_batch_rebuild_<timestamp>.log`
- **State File:** `.rebuild_state_phase1.json`

### Commands

```bash
# View help
./scripts/phase1-batch-rebuild.sh --help

# Check status
./scripts/phase1-monitor-rebuild.sh

# Validate
./scripts/phase1-validate-services.sh
```

---

**Document Version:** 1.0.0
**Last Updated:** February 4, 2026
**Framework:** TappsCodingAgents with Context7 MCP
**Status:** ✅ Ready for Execution
