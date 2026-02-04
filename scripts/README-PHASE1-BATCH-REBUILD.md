# Phase 1: Automated Batch Rebuild System

**Created:** February 4, 2026
**Framework:** TappsCodingAgents with Context7 MCP
**Target:** 40 HomeIQ Services

---

## 🚀 Quick Start

### Prerequisites Check

```bash
# 1. Verify Phase 0 completed
cat REBUILD_STATUS.md | grep "Phase 0"

# 2. Enable BuildKit
source .env.buildkit

# 3. Start monitoring (separate terminal)
./scripts/phase1-monitor-rebuild.sh
```

### Run Batch Rebuild

**Option 1: Rebuild Everything (Recommended)**
```bash
./scripts/phase1-batch-rebuild.sh
```

**Option 2: Dry Run First**
```bash
./scripts/phase1-batch-rebuild.sh --dry-run
```

**Option 3: By Category**
```bash
# Start with low-risk integration services
./scripts/phase1-batch-rebuild.sh --category integration

# Then continue with others
./scripts/phase1-batch-rebuild.sh --category automation
./scripts/phase1-batch-rebuild.sh --category ai-ml
```

---

## 📁 File Structure

```
scripts/
├── phase1-batch-rebuild.sh           # Main orchestration script
├── phase1-monitor-rebuild.sh         # Real-time monitoring dashboard
├── phase1-service-config.yaml        # Service definitions & config
├── phase1-validate-services.sh       # Post-rebuild validation
└── README-PHASE1-BATCH-REBUILD.md    # This file

docs/planning/
└── phase1-batch-rebuild-guide.md     # Comprehensive documentation
```

---

## 📊 What Gets Rebuilt

### 40 Services in 7 Categories

| Category | Count | Risk | Examples |
|----------|-------|------|----------|
| **Integration** | 8 | LOW | weather-api, sports-api, calendar |
| **AI/ML** | 13 | MED | ai-core, ml-service, rag-service |
| **Device** | 7 | MED | device-intelligence, device-health-monitor |
| **Automation** | 6 | LOW | automation-linter, blueprint-index |
| **Analytics** | 2 | LOW | energy-correlator, energy-forecasting |
| **Frontend** | 2 | LOW | health-dashboard, ai-automation-ui |
| **Other** | 2 | LOW | observability-dashboard, ha-simulator |

---

## ⚙️ Key Features

✅ **Parallel Processing** - Build 5 services at once (configurable)
✅ **BuildKit Optimization** - Fast, cached builds with layer optimization
✅ **Automated Health Checks** - Verify service health after rebuild
✅ **Rollback Support** - Automatic rollback on critical failures
✅ **State Management** - Resume from failures with `--continue`
✅ **Real-time Monitoring** - Live dashboard with progress tracking
✅ **Context7 Integration** - Library documentation lookup

---

## 🔧 Command Options

```bash
./scripts/phase1-batch-rebuild.sh [OPTIONS]

Options:
  --batch-size N         Parallel builds (default: 5)
  --category CAT         Build only: integration|ai-ml|device|automation|analytics|frontend|other
  --dry-run             Preview without executing
  --skip-tests          Skip test execution
  --no-cache            Force clean rebuild
  --rollback-on-fail    Auto-rollback on failures
  --continue            Resume from last failure
  --help                Show help
```

### Examples

```bash
# Fast rebuild with larger batches
./scripts/phase1-batch-rebuild.sh --batch-size 8

# Conservative with auto-rollback
./scripts/phase1-batch-rebuild.sh --batch-size 3 --rollback-on-fail

# Resume after fixing errors
./scripts/phase1-batch-rebuild.sh --continue

# Rebuild specific category
./scripts/phase1-batch-rebuild.sh --category integration
```

---

## 📈 Monitoring

### Launch Dashboard

```bash
./scripts/phase1-monitor-rebuild.sh
```

Shows:
- Progress bar (% complete)
- Services by status (completed/failed/pending)
- Category breakdown
- Recent build activity
- Docker container status
- Resource usage

### Manual Status

```bash
# Check rebuild state
cat .rebuild_state_phase1.json

# View service logs
tail -f logs/phase1_builds/*/weather-api.log

# Check Docker
docker-compose ps
docker stats --no-stream | head -10
```

---

## ✅ Validation

After rebuild completes:

```bash
./scripts/phase1-validate-services.sh
```

Checks:
- Rebuild state file
- Docker containers running
- Health endpoints responding
- Build logs for errors

---

## 🔄 Rollback

### Automatic Rollback

```bash
# Enable auto-rollback
./scripts/phase1-batch-rebuild.sh --rollback-on-fail
```

### Manual Rollback

```bash
# Find backup tag
docker images | grep pre-phase1

# Rollback single service
BACKUP_TAG="pre-phase1-rebuild-20260204_140000"
docker tag homeiq-weather-api:${BACKUP_TAG} homeiq-weather-api:latest
docker-compose up -d weather-api

# Rollback all (use Phase 0 backup)
cd backups/phase0_20260204_111804/
bash restore-backup.sh
```

---

## 🐛 Troubleshooting

### Build Fails

```bash
# Check logs
tail -f logs/phase1_builds/*/SERVICE_NAME.log

# Clean and rebuild
docker system prune -a
./scripts/phase1-batch-rebuild.sh --no-cache --category CATEGORY
```

### Health Check Timeout

```bash
# Check service logs
docker logs homeiq-SERVICE_NAME

# Manual health check
docker exec -it homeiq-SERVICE_NAME curl http://localhost:PORT/health
```

### Port Conflicts

```bash
# Find conflicting container
docker ps | grep PORT

# Stop and rebuild
docker stop CONTAINER_ID
./scripts/phase1-batch-rebuild.sh
```

### Resume After Failure

```bash
# Fix issues, then continue
./scripts/phase1-batch-rebuild.sh --continue
```

---

## ⏱️ Estimated Duration

With BuildKit caching and default batch size (5):

| Category | Services | Time |
|----------|----------|------|
| Integration | 8 | ~15-20 min |
| AI/ML | 13 | ~35-45 min |
| Device | 7 | ~20-25 min |
| Automation | 6 | ~15-20 min |
| Analytics | 2 | ~8-10 min |
| Frontend | 2 | ~10-15 min |
| Other | 2 | ~8-10 min |
| **Total** | **40** | **~2-3 hours** |

Adjust with `--batch-size` for faster/slower execution.

---

## 📚 Documentation

**Comprehensive Guide:**
[docs/planning/phase1-batch-rebuild-guide.md](../docs/planning/phase1-batch-rebuild-guide.md)

Includes:
- Detailed architecture
- Service category details
- Usage examples
- Troubleshooting
- Advanced configuration
- Performance tuning

**Related Documents:**
- [Rebuild Deployment Plan](../docs/planning/rebuild-deployment-plan.md)
- [Library Upgrade Summary](../upgrade-summary.md)
- [Phase 0 Execution Report](../docs/planning/phase0-execution-report.md)

---

## 🎯 Success Criteria

Phase 1 complete when:

- [ ] All 40 services rebuilt successfully
- [ ] Critical services pass health checks
- [ ] State file shows 40 completed
- [ ] Docker shows 40+ containers "Up"
- [ ] Validation script passes
- [ ] No blocking errors in logs

### Validation Commands

```bash
# 1. State file
grep -c "completed" .rebuild_state_phase1.json  # Should be 40

# 2. Docker status
docker-compose ps | grep -c "Up"  # Should be 40+

# 3. Run validation
./scripts/phase1-validate-services.sh
```

---

## 🚦 Next Steps

After successful completion:

1. **Update Status**
   ```bash
   # Mark Phase 1 complete
   vim REBUILD_STATUS.md
   ```

2. **Verify Health**
   ```bash
   ./scripts/phase1-validate-services.sh
   docker-compose ps
   ```

3. **Begin Phase 2**
   ```bash
   # Read Phase 2 plan
   cat docs/planning/rebuild-deployment-plan.md | sed -n '/## Phase 2:/,/## Phase 3:/p'
   ```

---

## 📞 Support

### Logs Location

- **Build Logs:** `logs/phase1_builds/<timestamp>/`
- **Master Log:** `logs/phase1_batch_rebuild_<timestamp>.log`
- **State File:** `.rebuild_state_phase1.json`

### Help Commands

```bash
# Script help
./scripts/phase1-batch-rebuild.sh --help

# Monitoring
./scripts/phase1-monitor-rebuild.sh

# Validation
./scripts/phase1-validate-services.sh --help
```

---

## 📝 Configuration

Edit [`phase1-service-config.yaml`](./phase1-service-config.yaml) to customize:

- Batch sizes
- Resource limits
- Timeout values
- Retry policies
- BuildKit settings
- Health check configuration
- Rollback behavior
- Monitoring options

---

## 🏗️ Architecture

```
Orchestrator (phase1-batch-rebuild.sh)
    ├─> Service Categorization (40 services in 7 categories)
    ├─> Batch Processor (parallel builds)
    │   ├─> Build (Docker with BuildKit)
    │   ├─> Test (pytest/npm test)
    │   └─> Health Check (automated)
    ├─> State Manager (JSON tracking)
    ├─> Monitoring Dashboard (real-time)
    └─> Rollback Support (automatic/manual)
```

---

## 🔐 Library Upgrades (Phase 1)

**Python:**
- SQLAlchemy: 1.4.x → 2.0.35+ (breaking)
- aiosqlite: → 0.22.1+
- FastAPI: 0.115.0+ → 0.119.0+
- Pydantic: → 2.12.0+ (standardize)
- httpx: 0.27.x → 0.28.1+

**Node.js:**
- @vitejs/plugin-react: 4.7.0 → 5.1.2
- typescript-eslint: 8.48.0 → 8.53.0

---

## ⚡ Performance Tips

1. **Use larger batch sizes** for faster builds (if resources allow)
   ```bash
   ./scripts/phase1-batch-rebuild.sh --batch-size 10
   ```

2. **Enable BuildKit caching** (default, but verify)
   ```bash
   source .env.buildkit
   ```

3. **Skip tests** during development (re-run with tests before production)
   ```bash
   ./scripts/phase1-batch-rebuild.sh --skip-tests
   ```

4. **Rebuild by category** to isolate issues
   ```bash
   ./scripts/phase1-batch-rebuild.sh --category integration
   ```

---

**Version:** 1.0.0
**Status:** ✅ Ready for Use
**Framework:** TappsCodingAgents with Context7 MCP
