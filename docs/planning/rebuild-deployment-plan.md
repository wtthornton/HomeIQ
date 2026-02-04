# HomeIQ Rebuild and Deployment Plan

**Date:** February 4, 2026
**Status:** ✅ Phase 0 Complete | 📋 Phase 1 Ready
**Current State:** 44/45 services running (websocket-ingestion fixed)
**Progress:** 16.7% (1/6 phases complete)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Critical Issues Identified](#critical-issues-identified)
4. [Rebuild Strategy](#rebuild-strategy)
5. [Deployment Plan](#deployment-plan)
6. [Testing & Validation](#testing--validation)
7. [Rollback Procedures](#rollback-procedures)
8. [Timeline & Resources](#timeline--resources)
9. [Post-Deployment Checklist](#post-deployment-checklist)

---

## Executive Summary

### Overview

This comprehensive plan outlines the strategy to rebuild and redeploy the entire HomeIQ platform, consisting of 48 microservices (45 Python backend services, 2 Node.js frontend applications, plus InfluxDB and Jaeger infrastructure).

### Key Objectives

1. **Fix Critical Issues**: Address the unhealthy websocket-ingestion service
2. **Apply Library Upgrades**: Implement the 4-phase library upgrade plan
3. **Rebuild All Services**: Ensure consistent builds with latest dependencies
4. **Zero-Downtime Deployment**: Maintain service availability during deployment
5. **Validate Health**: Comprehensive health checks post-deployment

### High-Level Timeline

- **Pre-Deployment Preparation**: 1 day
- **Service Rebuild (Phases 1-4)**: 4 weeks (as per upgrade-summary.md)
- **Staged Deployment**: 5 days
- **Post-Deployment Validation**: 2 days
- **Total Duration**: ~5 weeks

---

## Current State Assessment

### Infrastructure

**Docker Environment:**
- Docker Compose v2.0+
- BuildKit enabled for optimized builds
- Multi-stage builds for reduced image sizes
- Layer caching enabled

**Current Deployment:**
- 44 containers running (43 healthy, 1 unhealthy)
- Uptime: 47 hours (most services)
- Resource allocation: Per-service memory/CPU limits configured
- Health checks: Configured for all services
- Logging: JSON format with rotation (10MB max, 3 files)

### Service Inventory

**Infrastructure Services (2):**
1. InfluxDB 2.7.12 - Time-series database (Port 8086) ✓ Healthy
2. Jaeger 1.75.0 - Distributed tracing (Ports 16686, 4317, 4318) ✓ Healthy

**Frontend Services (2):**
1. health-dashboard - React 18 health monitoring UI (Port 3000) ✓ Healthy
2. ai-automation-ui - React 18 AI automation interface (Port 3001) ✓ Healthy

**Core Backend Services (5):**
1. websocket-ingestion - HA event ingestion (Port 8001) ⚠️ **UNHEALTHY**
2. admin-api - System monitoring & control (Port 8004) ✓ Healthy
3. data-api - Centralized query hub (Port 8006) ✓ Healthy
4. data-retention - Data lifecycle management (Port 8080) ✓ Healthy
5. observability-dashboard - Streamlit monitoring (Port 8501) - Not currently running

**External Integration Services (8):**
1. weather-api (Port 8009) ✓ Healthy
2. sports-api (Port 8005) ✓ Healthy
3. carbon-intensity (Port 8010) ✓ Healthy
4. electricity-pricing (Port 8011) ✓ Healthy
5. air-quality (Port 8012) ✓ Healthy
6. calendar-service (Port 8013) ✓ Healthy
7. smart-meter-service (Port 8014) ✓ Healthy
8. log-aggregator (Port 8015) ✓ Healthy

**AI/ML Services (13):**
1. ai-core-service (Port 8018) ✓ Healthy
2. ai-pattern-service (Port 8034) ✓ Healthy
3. ai-automation-service-new (Port 8036) ✓ Healthy
4. ai-query-service (Port 8035) ✓ Healthy
5. ai-training-service (Port 8033) ✓ Healthy
6. ai-code-executor (Port 8030) ✓ Healthy
7. ha-ai-agent-service (Port 8030) ✓ Healthy
8. proactive-agent-service (Port 8031) ✓ Healthy
9. ml-service (Port 8025) ✓ Healthy
10. openvino-service (Port 8026) ✓ Healthy
11. rag-service (Port 8027) ✓ Healthy
12. openai-service (Port 8020) ✓ Healthy
13. ner-service (Port 8031) ✓ Healthy

**Device Management Services (7):**
1. device-intelligence-service (Port 8028) ✓ Healthy
2. device-health-monitor (Port 8019) ✓ Healthy
3. device-context-classifier (Port 8032) ✓ Healthy
4. device-database-client (Port 8022) ✓ Healthy
5. device-recommender (Port 8023) ✓ Healthy
6. device-setup-assistant (Port 8021) ✓ Healthy
7. ha-setup-service (Port 8024) ✓ Healthy

**Automation Services (6):**
1. automation-linter (Port 8016) ✓ Healthy
2. automation-miner (Port 8029) ✓ Healthy
3. blueprint-index (Port 8038) ✓ Healthy
4. blueprint-suggestion-service (Port 8039) ✓ Healthy
5. yaml-validation-service (Port 8037) ✓ Healthy
6. api-automation-edge (Port 8041) ✓ Starting (3 seconds old)

**Analytics Services (2):**
1. energy-correlator (Port 8017) ✓ Healthy
2. rule-recommendation-ml (Port 8040) ✓ Healthy

### Dependencies

**Base Python Requirements** ([requirements-base.txt](c:\cursor\HomeIQ\requirements-base.txt)):
- Python 3.12+ (minimum)
- FastAPI 0.128.x
- Pydantic 2.12.5
- SQLAlchemy 2.0.45
- aiosqlite 0.21.0
- InfluxDB client 1.49.0
- OpenTelemetry suite 1.24.0
- httpx 0.28.1, aiohttp 3.13.3
- pytest 8.3.3, pytest-asyncio 1.3.0

**Node.js Dependencies** ([package.json](c:\cursor\HomeIQ\package.json)):
- React 18.3.1
- TypeScript 5.9.3
- Vite 6.4.1
- Tailwind CSS 3.4.18
- Playwright 1.56.1

### Configuration Files

**Environment Configuration:**
- `.env` - Main environment file with HA credentials, API keys, service configuration
- `infrastructure/.env.*` - Service-specific overrides
- Docker Compose environment sections per service

**Docker Compose Files:**
- `docker-compose.yml` - Primary production configuration (48 services)
- `docker-compose.dev.yml` - Development environment
- `docker-compose.minimal.yml` - Minimal setup
- `docker-compose.simple.yml` - Simple deployment

---

## Critical Issues Identified

### 1. Unhealthy WebSocket Ingestion Service ⚠️ CRITICAL

**Service:** homeiq-websocket
**Status:** Up 47 hours (unhealthy)
**Port:** 8001
**Impact:** HIGH - This is the core service that ingests events from Home Assistant

**Symptoms:**
- Container running but health check failing
- Health check endpoint: `http://localhost:8001/health`
- All other services healthy and running

**Potential Causes:**
1. Connection issue to Home Assistant (WebSocket or HTTP)
2. InfluxDB connection/write failures
3. Health check endpoint misconfigured or not responding
4. Resource exhaustion (memory/CPU)
5. Crashed worker threads/processes

**Investigation Required:**
```bash
# Check service logs
docker logs homeiq-websocket --tail 100

# Check resource usage
docker stats homeiq-websocket --no-stream

# Test health endpoint manually
curl -f http://localhost:8001/health

# Check HA connectivity
docker exec homeiq-websocket curl -f $HA_HTTP_URL/api/
```

**Recommended Fix:**
1. Review logs for error messages
2. Verify Home Assistant connectivity
3. Check InfluxDB write permissions
4. Restart service if necessary: `docker restart homeiq-websocket`
5. Consider rebuilding if code issues identified

### 2. Library Version Inconsistencies

**Issue:** Multiple versions of critical libraries across services
**Impact:** MEDIUM - Potential compatibility issues, security vulnerabilities
**Details:** See [upgrade-summary.md](c:\cursor\HomeIQ\docs\planning\upgrade-summary.md)

**Key Conflicts:**
- FastAPI: 0.115.0 (automation-linter) vs 0.128.x (most services)
- Pydantic: 2.8.2, 2.9.2, 2.12.4 scattered across services
- httpx: Split between 0.27.x and 0.28.1+
- pydantic-settings: calendar-service 11 versions behind

### 3. Missing Observability Dashboard

**Service:** observability-dashboard
**Status:** Not running (defined in docker-compose.yml but not started)
**Port:** 8501
**Impact:** LOW - Reduces visibility into system health

**Action:** Include in rebuild/redeploy or explicitly exclude if not needed

### 4. Python Version Uncertainty

**Issue:** Current Python version across services unknown
**Target:** Python 3.10+ (required for Pandas 3.0, websockets 16.0)
**Impact:** HIGH if upgrading ML/AI libraries (Phase 3)

**Action Required:**
```bash
# Check Python version in each service
docker exec homeiq-data-api python --version
docker exec homeiq-websocket python --version
# Repeat for other services...
```

### 5. Sensitive Data in Configuration

**Issue:** `.env` file contains sensitive credentials
**Location:** c:\cursor\HomeIQ\.env
**Contents:**
- Home Assistant tokens
- OpenAI API keys
- InfluxDB passwords
- MQTT credentials
- GitHub tokens

**Security Concerns:**
- Plain text storage
- File potentially in version control
- Shared secrets across multiple services

**Recommendations:**
1. Verify `.env` is in `.gitignore`
2. Consider secrets management solution (Docker secrets, vault)
3. Rotate credentials after documenting deployment
4. Use environment-specific API keys (dev vs prod)

---

## Rebuild Strategy

### Overview

The rebuild strategy follows a phased approach aligned with the library upgrade plan, ensuring stability and testability at each stage.

### Phase 0: Pre-Rebuild Preparation (1 Day)

**Objectives:**
1. Backup current state
2. Fix critical websocket-ingestion issue
3. Verify infrastructure requirements
4. Set up monitoring for rebuild

**Tasks:**

**0.1. Backup Current State**
```bash
# Backup Docker volumes
docker run --rm -v homeiq_influxdb_data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/influxdb_data_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

docker run --rm -v homeiq_sqlite-data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/sqlite_data_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Backup environment configuration
cp .env .env.backup_$(date +%Y%m%d_%H%M%S)
cp docker-compose.yml docker-compose.yml.backup_$(date +%Y%m%d_%H%M%S)

# Export current Docker images list
docker images --format "{{.Repository}}:{{.Tag}}" | grep homeiq > current_images.txt
```

**0.2. Diagnose and Fix WebSocket Ingestion**
```bash
# Capture diagnostic information
docker logs homeiq-websocket > websocket_logs_$(date +%Y%m%d_%H%M%S).txt
docker inspect homeiq-websocket > websocket_inspect_$(date +%Y%m%d_%H%M%S).json
docker stats homeiq-websocket --no-stream > websocket_stats.txt

# Test connectivity
docker exec homeiq-websocket curl -f http://influxdb:8086/health
docker exec homeiq-websocket env | grep -E "HA_|INFLUX"

# Attempt restart
docker restart homeiq-websocket

# Monitor for 5 minutes
watch -n 10 'docker ps --filter name=websocket --format "{{.Status}}"'

# If still unhealthy, review logs and rebuild specific service
cd /c/cursor/HomeIQ
docker-compose build --no-cache websocket-ingestion
docker-compose up -d websocket-ingestion
```

**0.3. Verify Infrastructure Requirements**
```bash
# Check Docker and Docker Compose versions
docker --version  # Should be 20.10+
docker compose version  # Should be v2.0+

# Check system resources
free -h  # Available memory
df -h  # Available disk space
nproc  # CPU cores

# Verify Python versions in containers
for service in data-api websocket-ingestion admin-api; do
  echo "=== $service ==="
  docker exec homeiq-$service python --version 2>/dev/null || echo "N/A"
done

# Verify Node.js versions in frontend containers
docker exec homeiq-dashboard node --version 2>/dev/null || echo "N/A"
docker exec ai-automation-ui node --version 2>/dev/null || echo "N/A"
```

**0.4. Set Up Build Monitoring**
```bash
# Enable BuildKit with progress output
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

# Create build log directory
mkdir -p logs/rebuild_$(date +%Y%m%d)
```

### Phase 1: Critical Compatibility Fixes (Week 1)

**Aligned with:** Library Upgrade Plan Phase 1
**Risk Level:** LOW-MEDIUM
**Services Affected:** 15+ Python services, 2 Node.js services
**Build Strategy:** Service-by-service with immediate testing

**Objectives:**
1. Update SQLAlchemy 2.0.35+ → 2.0.46
2. Update aiosqlite 0.20.x/0.21.x → 0.22.1
3. Standardize FastAPI → 0.119.0+
4. Standardize Pydantic → 2.12.0
5. Standardize httpx → 0.28.1+
6. Update Node.js build tools

**Implementation Steps:**

**1.1. Update requirements-base.txt**
```bash
cd /c/cursor/HomeIQ

# Backup current file
cp requirements-base.txt requirements-base.txt.backup

# Update base requirements (manual edit or script)
# Changes:
# - sqlalchemy>=2.0.45,<3.0.0 → sqlalchemy>=2.0.46,<3.0.0
# - aiosqlite>=0.21.0,<0.22.0 → aiosqlite>=0.22.1,<0.23.0
# - fastapi>=0.128.0,<0.129.0 → fastapi>=0.119.0,<0.130.0
# - pydantic>=2.12.5,<3.0.0 (keep current)
# - httpx>=0.28.1,<0.29.0 (keep current)
```

**1.2. Update Service-Specific Requirements**
```bash
# Update automation-linter (most outdated)
# services/automation-linter/requirements.txt
# Update FastAPI from 0.115.0 to >=0.119.0

# Update calendar-service (pydantic-settings outdated)
# services/calendar-service/requirements.txt
# Update pydantic-settings from 2.1.0 to >=2.12.0,<3.0.0
```

**1.3. Rebuild Infrastructure Services First**
```bash
cd /c/cursor/HomeIQ

# InfluxDB and Jaeger don't need rebuilding (use official images)
# But restart to ensure clean state
docker-compose restart influxdb jaeger

# Wait for health
sleep 30
docker ps --filter name=influxdb --filter name=jaeger
```

**1.4. Rebuild Core Services (Sequential)**
```bash
# Build order: data-api → websocket-ingestion → admin-api

echo "Building data-api..."
docker-compose build --no-cache data-api
docker-compose up -d data-api
sleep 20
docker ps --filter name=data-api --format "{{.Status}}"

echo "Building websocket-ingestion..."
docker-compose build --no-cache websocket-ingestion
docker-compose up -d websocket-ingestion
sleep 30
docker ps --filter name=websocket --format "{{.Status}}"

echo "Building admin-api..."
docker-compose build --no-cache admin-api
docker-compose up -d admin-api
sleep 20
docker ps --filter name=admin --format "{{.Status}}"

# Verify health of all three
docker ps --filter name="data-api|websocket|admin" --format "table {{.Names}}\t{{.Status}}"
```

**1.5. Rebuild Data & Integration Services (Parallel)**
```bash
# Build data-retention, all external integration services
SERVICES="data-retention weather-api sports-api carbon-intensity electricity-pricing air-quality calendar-service smart-meter-service log-aggregator"

for service in $SERVICES; do
  echo "Building $service..."
  docker-compose build --no-cache $service &
done

# Wait for all builds to complete
wait

# Deploy all services
docker-compose up -d $SERVICES

# Wait for health checks
sleep 60
docker ps --filter name="data-retention|weather|sports|carbon|electricity|air-quality|calendar|smart-meter|log-aggregator" --format "table {{.Names}}\t{{.Status}}"
```

**1.6. Rebuild Frontend Services**
```bash
# Update package.json dependencies for both dashboards
cd services/health-dashboard
npm install @vitejs/plugin-react@5.1.2 typescript-eslint@8.53.0
cd ../ai-automation-ui
npm install @vitejs/plugin-react@5.1.2 typescript-eslint@8.53.0
cd ../..

# Rebuild both frontends
docker-compose build --no-cache health-dashboard ai-automation-ui
docker-compose up -d health-dashboard ai-automation-ui

# Wait and verify
sleep 30
docker ps --filter name="dashboard|automation-ui" --format "table {{.Names}}\t{{.Status}}"
```

**1.7. Test Phase 1 Deployments**
```bash
# Run validation script
node validate-deployment.js

# Test API endpoints
curl -f http://localhost:8006/health  # data-api
curl -f http://localhost:8001/health  # websocket-ingestion
curl -f http://localhost:8004/health  # admin-api

# Test frontend access
curl -f http://localhost:3000  # health-dashboard
curl -f http://localhost:3001  # ai-automation-ui

# Check Jaeger tracing
curl -f http://localhost:16686/
```

**Phase 1 Success Criteria:**
- ✓ All rebuilt services show "healthy" status
- ✓ No errors in service logs (last 100 lines)
- ✓ API endpoints respond correctly
- ✓ Frontend dashboards load successfully
- ✓ InfluxDB receiving data (check via Jaeger)
- ✓ No service restarts in 1 hour

### Phase 2: Standard Library Updates (Week 2)

**Aligned with:** Library Upgrade Plan Phase 2
**Risk Level:** LOW-MEDIUM
**Services Affected:** 30+ Python services
**Build Strategy:** Service group batches with regression testing

**Objectives:**
1. Update pytest 8.3.x → 9.0.2
2. Update pytest-asyncio 0.23.0 → 1.3.0 (BREAKING)
3. Update tenacity 8.2.3 → 9.1.2 (MAJOR)
4. Migrate asyncio-mqtt → aiomqtt 2.4.0
5. Update python-dotenv → 1.2.1
6. Update influxdb3-python 0.3.0 → 0.17.0
7. Update Node.js test libraries

**Implementation Steps:**

**2.1. Update requirements-base.txt**
```bash
cd /c/cursor/HomeIQ

# Update base requirements with Phase 2 changes
# Key updates:
# - pytest>=8.3.3,<9.0.0 → pytest>=9.0.2,<10.0.0
# - pytest-asyncio>=1.3.0,<2.0.0 (already updated)
# - tenacity>=8.0.0,<9.0.0 → tenacity>=9.1.2,<10.0.0
# - python-dotenv>=1.2.1,<2.0.0 (keep current)
# - influxdb-client>=1.49.0,<2.0.0 → influxdb3-python>=0.17.0,<1.0.0 (breaking change!)
```

**2.2. Handle BREAKING CHANGES**

**2.2.1. pytest-asyncio 1.x Migration**
- Update all test fixtures to use `@pytest.mark.asyncio` correctly
- Review async test patterns in all service test suites
- Update pytest.ini configurations if needed

**2.2.2. tenacity 9.x Migration**
- Review retry decorators across all services
- Update any custom retry logic
- Test retry behavior in error scenarios

**2.2.3. asyncio-mqtt → aiomqtt Migration**
- Find all services using MQTT
```bash
cd /c/cursor/HomeIQ
grep -r "asyncio_mqtt" services/*/requirements.txt
grep -r "import asyncio_mqtt" services/*/src/
```
- Update imports: `from asyncio_mqtt import Client` → `from aiomqtt import Client`
- Update requirements.txt in affected services
- Rebuild and test MQTT connectivity

**2.2.4. influxdb-client → influxdb3-python Migration** ⚠️ HIGH IMPACT
- This affects ALL services writing to InfluxDB
- Review migration guide: https://github.com/InfluxCommunity/influxdb3-python
- Update shared/influxdb_query_client.py
- Update all service InfluxDB write logic
- Extensive testing required

**2.3. Rebuild AI/ML Services (Batch 1)**
```bash
# Build AI core services
SERVICES="ai-core-service ai-pattern-service ai-automation-service-new ai-query-service ai-training-service ai-code-executor ha-ai-agent-service proactive-agent-service"

for service in $SERVICES; do
  echo "Building $service..."
  docker-compose build --no-cache $service &
done
wait

docker-compose up -d $SERVICES
sleep 60
docker ps --filter name="ai-|proactive" --format "table {{.Names}}\t{{.Status}}"
```

**2.4. Rebuild ML & OpenVINO Services (Batch 2)**
```bash
SERVICES="ml-service openvino-service rag-service openai-service ner-service"

for service in $SERVICES; do
  echo "Building $service..."
  docker-compose build --no-cache $service &
done
wait

docker-compose up -d $SERVICES
sleep 60
docker ps --filter name="ml-|openvino|rag|openai|ner" --format "table {{.Names}}\t{{.Status}}"
```

**2.5. Rebuild Device Services (Batch 3)**
```bash
SERVICES="device-intelligence-service device-health-monitor device-context-classifier device-database-client device-recommender device-setup-assistant ha-setup-service"

for service in $SERVICES; do
  echo "Building $service..."
  docker-compose build --no-cache $service &
done
wait

docker-compose up -d $SERVICES
sleep 60
docker ps --filter name="device-|ha-setup" --format "table {{.Names}}\t{{.Status}}"
```

**2.6. Rebuild Automation Services (Batch 4)**
```bash
SERVICES="automation-linter automation-miner blueprint-index blueprint-suggestion-service yaml-validation-service api-automation-edge"

for service in $SERVICES; do
  echo "Building $service..."
  docker-compose build --no-cache $service &
done
wait

docker-compose up -d $SERVICES
sleep 60
docker ps --filter name="automation-|blueprint-|yaml-|api-automation" --format "table {{.Names}}\t{{.Status}}"
```

**2.7. Rebuild Analytics Services (Batch 5)**
```bash
SERVICES="energy-correlator rule-recommendation-ml"

for service in $SERVICES; do
  echo "Building $service..."
  docker-compose build --no-cache $service &
done
wait

docker-compose up -d $SERVICES
sleep 30
docker ps --filter name="energy-|rule-recommendation" --format "table {{.Names}}\t{{.Status}}"
```

**2.8. Update and Rebuild Frontend Services**
```bash
cd services/health-dashboard
npm install vitest@4.0.17 @playwright/test@1.58.1 happy-dom@20.5.0 msw@2.12.8

cd ../ai-automation-ui
npm install vitest@4.0.17 @playwright/test@1.58.1 happy-dom@20.5.0 msw@2.12.8

cd ../..
docker-compose build --no-cache health-dashboard ai-automation-ui
docker-compose up -d health-dashboard ai-automation-ui
```

**2.9. Run Comprehensive Tests**
```bash
# Run all Python unit tests
npm run test:unit:python

# Run all TypeScript unit tests
npm run test:unit:typescript

# Run E2E tests
npm run test:e2e

# Check test coverage
npm run test:coverage
```

**Phase 2 Success Criteria:**
- ✓ All 48 services rebuilt and healthy
- ✓ All unit tests passing (Python & TypeScript)
- ✓ E2E tests passing
- ✓ Test coverage maintained at 80%+
- ✓ No InfluxDB write errors after migration
- ✓ MQTT services connecting successfully
- ✓ No service restarts in 2 hours

### Phase 3: ML/AI Library Upgrades (Week 3)

**Aligned with:** Library Upgrade Plan Phase 3
**Risk Level:** HIGH
**Services Affected:** ml-service, ai-pattern-service, ha-ai-agent-service, rule-recommendation-ml
**Build Strategy:** Isolated environment, extensive testing, gradual rollout

**⚠️ CRITICAL: This phase requires Python 3.10+ for full compatibility**

**Objectives:**
1. Upgrade NumPy 1.26.x → 2.4.2 (MAJOR - breaking changes)
2. Upgrade Pandas 2.2.x → 3.0.0 (MAJOR - breaking changes, requires NumPy 2.x)
3. Update scikit-learn 1.5.x → 1.8.0
4. Update scipy 1.16.3 → 1.17.0
5. Update OpenAI SDK 1.54.0 → 2.16.0 (MAJOR)
6. Update tiktoken 0.8.0 → 0.12.0

**Pre-Phase 3 Checklist:**
```bash
# ✓ Verify Python 3.10+ in all ML services
docker exec homeiq-ml-service python --version
docker exec homeiq-ai-pattern-service python --version
docker exec homeiq-ha-ai-agent-service python --version
docker exec homeiq-rule-recommendation-ml python --version

# If any show Python < 3.10, update Dockerfiles:
# FROM python:3.12-slim  # or 3.10-slim minimum
```

**Implementation Steps:**

**3.1. Set Up Isolated Testing Environment**
```bash
# Create test docker-compose for ML services only
cat > docker-compose.ml-test.yml <<EOF
version: '3.8'
services:
  ml-service-test:
    build:
      context: .
      dockerfile: services/ml-service/Dockerfile
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
    depends_on:
      - influxdb
    networks:
      - homeiq-network
networks:
  homeiq-network:
    external: true
EOF
```

**3.2. Update ML Service Requirements**
```bash
# Create Phase 3 requirements file
cat > services/ml-service/requirements-phase3.txt <<EOF
-r ../../requirements-base.txt

# ML/AI Libraries - Phase 3 Upgrades
numpy>=2.4.2,<3.0.0  # MAJOR UPGRADE
pandas>=3.0.0,<4.0.0  # MAJOR UPGRADE - requires NumPy 2.x
scipy>=1.17.0,<2.0.0
scikit-learn>=1.8.0,<2.0.0

# OpenAI SDK - MAJOR UPGRADE
openai>=2.16.0,<3.0.0
tiktoken>=0.12.0,<1.0.0

# Additional ML dependencies
matplotlib>=3.8.0,<4.0.0
seaborn>=0.13.0,<0.14.0
EOF

# Copy to other ML services
cp services/ml-service/requirements-phase3.txt services/ai-pattern-service/
cp services/ml-service/requirements-phase3.txt services/ha-ai-agent-service/
cp services/ml-service/requirements-phase3.txt services/rule-recommendation-ml/
```

**3.3. Update Code for NumPy 2.x Breaking Changes**

**Common NumPy 2.x Breaking Changes:**
1. Changed dtype behavior
2. Array casting rules stricter
3. Some deprecated functions removed
4. New default random number generator

**Code Updates Required:**
```bash
# Find all NumPy usage in ML services
cd /c/cursor/HomeIQ
find services/ml-service services/ai-pattern-service services/ha-ai-agent-service services/rule-recommendation-ml \
  -name "*.py" -exec grep -l "import numpy" {} \;

# Review each file for:
# - np.asarray() calls (may need dtype= parameter)
# - np.random usage (update to np.random.Generator)
# - Deprecated np.* functions
```

**3.4. Update Code for Pandas 3.0 Breaking Changes**

**Common Pandas 3.0 Breaking Changes:**
1. Dedicated string dtype (PyArrow-backed) by default
2. Copy-on-Write enabled by default
3. Some deprecated methods removed
4. Changed default behaviors

**Code Updates Required:**
```bash
# Find all Pandas usage
find services/ml-service services/ai-pattern-service services/ha-ai-agent-service services/rule-recommendation-ml \
  -name "*.py" -exec grep -l "import pandas" {} \;

# Review each file for:
# - String columns (will be PyArrow strings by default)
# - DataFrame.append() usage (removed, use concat)
# - Inplace operations behavior changes
# - Deprecated pd.* functions
```

**3.5. Update Code for OpenAI SDK 2.x Breaking Changes**

**Common OpenAI SDK 2.x Breaking Changes:**
1. API structure changes
2. New client initialization pattern
3. Changed response formats
4. Updated error handling

**Code Updates Required:**
```bash
# Find all OpenAI SDK usage
find services/ -name "*.py" -exec grep -l "import openai" {} \;

# Review migration guide and update:
# - Client initialization
# - Completion/Chat API calls
# - Error handling
# - Response parsing
```

**3.6. Rebuild and Test ML Services One by One**

**3.6.1. ml-service**
```bash
cd /c/cursor/HomeIQ

# Update requirements
cp services/ml-service/requirements-phase3.txt services/ml-service/requirements.txt

# Rebuild
docker-compose build --no-cache ml-service

# Test in isolation
docker-compose -f docker-compose.ml-test.yml up -d ml-service-test

# Run ML tests
docker exec ml-service-test pytest /app/tests/ -v

# Validate model outputs
docker exec ml-service-test python -c "
import numpy as np
import pandas as pd
import sklearn
print(f'NumPy: {np.__version__}')
print(f'Pandas: {pd.__version__}')
print(f'scikit-learn: {sklearn.__version__}')
"

# If tests pass, deploy
docker-compose up -d ml-service
sleep 30
docker ps --filter name=ml-service --format "{{.Status}}"
```

**3.6.2. ai-pattern-service**
```bash
# Repeat process for ai-pattern-service
cp services/ai-pattern-service/requirements-phase3.txt services/ai-pattern-service/requirements.txt
docker-compose build --no-cache ai-pattern-service
# Run specific pattern detection tests
docker exec ai-pattern-service pytest /app/tests/ -v -k "pattern"
docker-compose up -d ai-pattern-service
```

**3.6.3. ha-ai-agent-service**
```bash
# Repeat process for ha-ai-agent-service
cp services/ha-ai-agent-service/requirements-phase3.txt services/ha-ai-agent-service/requirements.txt
docker-compose build --no-cache ha-ai-agent-service
# Test OpenAI integration
docker exec ha-ai-agent-service pytest /app/tests/ -v -k "openai"
docker-compose up -d ha-ai-agent-service
```

**3.6.4. rule-recommendation-ml**
```bash
# Repeat process for rule-recommendation-ml
cp services/rule-recommendation-ml/requirements-phase3.txt services/rule-recommendation-ml/requirements.txt
docker-compose build --no-cache rule-recommendation-ml
# Test ML recommendations
docker exec rule-recommendation-ml pytest /app/tests/ -v
docker-compose up -d rule-recommendation-ml
```

**3.7. Comprehensive ML Validation**
```bash
# Run full ML test suite
npm run test:unit:python -- services/ml-service services/ai-pattern-service services/ha-ai-agent-service services/rule-recommendation-ml

# Validate model accuracy
# (Run your specific model validation scripts here)

# Check for performance regressions
# (Run benchmarks and compare to baseline)

# Monitor for 24 hours for memory leaks or crashes
docker stats --no-stream | grep -E "ml-service|ai-pattern|ha-ai-agent|rule-recommendation"
```

**Phase 3 Success Criteria:**
- ✓ All ML services rebuilt with NumPy 2.x, Pandas 3.0
- ✓ All ML unit tests passing
- ✓ Model accuracy maintained or improved
- ✓ No performance regressions (inference time within 10% of baseline)
- ✓ No memory leaks detected (24-hour stability test)
- ✓ OpenAI API integration working correctly
- ✓ Pattern detection producing expected results
- ✓ Recommendation quality unchanged or improved

**⚠️ Rollback Plan for Phase 3:**
If critical issues arise with ML services:
```bash
# Revert to previous images
docker-compose down ml-service ai-pattern-service ha-ai-agent-service rule-recommendation-ml
docker tag homeiq-ml-service:latest homeiq-ml-service:phase3-failed
docker tag homeiq-ml-service:phase2-backup homeiq-ml-service:latest
# (Repeat for other ML services)
docker-compose up -d ml-service ai-pattern-service ha-ai-agent-service rule-recommendation-ml
```

### Phase 4: Frontend Major Updates (Week 4)

**Aligned with:** Library Upgrade Plan Phase 4
**Risk Level:** HIGH (if aggressive path) / LOW (if conservative path)
**Services Affected:** health-dashboard, ai-automation-ui
**Build Strategy:** Conservative first, aggressive later

**Decision Point: Conservative vs Aggressive Path**

**Option A: Conservative (RECOMMENDED)**
- Stay on React 18, Vite 6, Tailwind 3
- Apply all minor/patch updates from Phases 1-2
- Focus on stability
- Timeline: 2 days

**Option B: Aggressive**
- React 18 → 19 (MAJOR - breaking changes)
- Vite 6 → 7 (requires Node.js 20.19+)
- Tailwind 3 → 4 (MAJOR - breaking changes)
- Timeline: 5 days + extensive testing

**⚠️ Recommendation: Start with Option A, plan Option B for future sprint**

**Implementation Steps (Conservative Path):**

**4.1. Apply Accumulated Updates**
```bash
cd services/health-dashboard
npm install \
  @vitejs/plugin-react@5.1.2 \
  typescript-eslint@8.53.0 \
  vitest@4.0.17 \
  @playwright/test@1.58.1 \
  happy-dom@20.5.0 \
  msw@2.12.8

cd ../ai-automation-ui
npm install \
  @vitejs/plugin-react@5.1.2 \
  typescript-eslint@8.53.0 \
  vitest@4.0.17 \
  @playwright/test@1.58.1 \
  happy-dom@20.5.0 \
  msw@2.12.8
```

**4.2. Rebuild and Test**
```bash
cd /c/cursor/HomeIQ

# Build production bundles locally first
cd services/health-dashboard
npm run build
npm run test
cd ../ai-automation-ui
npm run build
npm run test
cd ../..

# Rebuild Docker images
docker-compose build --no-cache health-dashboard ai-automation-ui

# Deploy
docker-compose up -d health-dashboard ai-automation-ui

# Verify
curl -f http://localhost:3000
curl -f http://localhost:3001

# Run E2E tests
npm run test:e2e
```

**Phase 4 Success Criteria:**
- ✓ Both frontend services rebuilt and healthy
- ✓ All React components rendering correctly
- ✓ No console errors in browser
- ✓ E2E tests passing
- ✓ Performance maintained (load time within 10% of baseline)
- ✓ No visual regressions

---

## Deployment Plan

### Deployment Strategy

**Approach:** Rolling deployment with health checks and rollback capability
**Downtime:** Zero-downtime deployment (services update one at a time)
**Duration:** 5 days (after all phases complete)
**Environment:** Production (Windows Docker environment)

### Deployment Phases

#### Day 1: Infrastructure & Core Services

**Morning (8 AM - 12 PM):**
```bash
# 1. Final backup before deployment
./scripts/backup-all.sh

# 2. Deploy infrastructure services (should not require rebuild)
docker-compose restart influxdb jaeger

# 3. Deploy core services with zero-downtime
docker-compose up -d --no-deps --build data-api
sleep 30
docker ps --filter name=data-api

docker-compose up -d --no-deps --build websocket-ingestion
sleep 30
docker ps --filter name=websocket

docker-compose up -d --no-deps --build admin-api
sleep 30
docker ps --filter name=admin

docker-compose up -d --no-deps --build data-retention
sleep 30
docker ps --filter name=data-retention

# 4. Verify core services health
for service in data-api websocket admin data-retention; do
  curl -f http://localhost:$(docker port homeiq-$service | cut -d: -f2)/health || echo "$service health check failed"
done
```

**Afternoon (1 PM - 5 PM):**
```bash
# 5. Deploy frontend services
docker-compose up -d --no-deps --build health-dashboard ai-automation-ui
sleep 30

# 6. Smoke test frontend
curl -f http://localhost:3000
curl -f http://localhost:3001

# 7. Monitor for 4 hours
watch -n 60 'docker ps --format "table {{.Names}}\t{{.Status}}" | head -10'
```

#### Day 2: External Integration Services

**Morning (8 AM - 12 PM):**
```bash
# Deploy all external integration services
SERVICES="weather-api sports-api carbon-intensity electricity-pricing air-quality calendar-service smart-meter-service log-aggregator"

for service in $SERVICES; do
  docker-compose up -d --no-deps --build $service
  sleep 20
  docker ps --filter name=$service --format "{{.Status}}"
done

# Verify all health checks
for service in $SERVICES; do
  port=$(docker port homeiq-$service 2>/dev/null | head -1 | cut -d: -f2)
  if [ -n "$port" ]; then
    curl -f http://localhost:$port/health || echo "$service health check failed"
  fi
done
```

**Afternoon (1 PM - 5 PM):**
```bash
# Verify data flowing correctly
# - Weather data appearing in InfluxDB
# - Sports events being tracked
# - Carbon intensity metrics present
# - Air quality data updating

# Check InfluxDB for recent data
docker exec homeiq-influxdb influx query 'from(bucket: "home_assistant_events") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "weather_data") |> count()'
```

#### Day 3: AI/ML Services (Critical)

**Morning (8 AM - 10 AM):**
```bash
# Deploy AI core services one by one with extra monitoring
SERVICES="ai-core-service ai-pattern-service ai-query-service"

for service in $SERVICES; do
  echo "=== Deploying $service ==="
  docker-compose up -d --no-deps --build $service
  sleep 60  # Extra wait time for AI services

  # Check status and logs
  docker ps --filter name=$service
  docker logs --tail 50 homeiq-$service

  # Verify health
  port=$(docker port homeiq-$service 2>/dev/null | head -1 | cut -d: -f2)
  if [ -n "$port" ]; then
    curl -f http://localhost:$port/health || echo "WARNING: $service health check failed"
  fi
done
```

**Late Morning (10 AM - 12 PM):**
```bash
# Deploy automation and agent services
SERVICES="ai-automation-service-new ai-code-executor ha-ai-agent-service proactive-agent-service"

for service in $SERVICES; do
  docker-compose up -d --no-deps --build $service
  sleep 60
  docker ps --filter name=$service
done
```

**Afternoon (1 PM - 5 PM):**
```bash
# Deploy ML services with extended monitoring
SERVICES="ml-service openvino-service rag-service openai-service ner-service ai-training-service"

for service in $SERVICES; do
  echo "=== Deploying $service ==="
  docker-compose up -d --no-deps --build $service
  sleep 60

  # Monitor resource usage
  docker stats --no-stream homeiq-$service

  # Check logs for errors
  docker logs --tail 100 homeiq-$service | grep -i error || echo "No errors found"
done

# Run ML validation tests
npm run test:unit:python -- services/ml-service services/ai-pattern-service
```

#### Day 4: Device & Automation Services

**Morning (8 AM - 12 PM):**
```bash
# Deploy device management services
SERVICES="device-intelligence-service device-health-monitor device-context-classifier device-database-client device-recommender device-setup-assistant ha-setup-service"

for service in $SERVICES; do
  docker-compose up -d --no-deps --build $service
  sleep 30
  docker ps --filter name=$service --format "{{.Status}}"
done

# Verify device intelligence working
docker exec homeiq-device-intelligence curl -f http://localhost:8019/health
```

**Afternoon (1 PM - 5 PM):**
```bash
# Deploy automation services
SERVICES="automation-linter automation-miner blueprint-index blueprint-suggestion-service yaml-validation-service api-automation-edge"

for service in $SERVICES; do
  docker-compose up -d --no-deps --build $service
  sleep 30
  docker ps --filter name=$service --format "{{.Status}}"
done

# Test automation linter
docker exec homeiq-automation-linter curl -f http://localhost:8020/health
```

#### Day 5: Analytics & Final Validation

**Morning (8 AM - 10 AM):**
```bash
# Deploy remaining analytics services
SERVICES="energy-correlator rule-recommendation-ml"

for service in $SERVICES; do
  docker-compose up -d --no-deps --build $service
  sleep 30
  docker ps --filter name=$service --format "{{.Status}}"
done
```

**Late Morning (10 AM - 12 PM):**
```bash
# Deploy observability dashboard (if desired)
docker-compose up -d --no-deps --build observability-dashboard
sleep 30
curl -f http://localhost:8501/_stcore/health
```

**Afternoon (1 PM - 5 PM):**
```bash
# Comprehensive validation
./scripts/deploy.sh status

# Run full test suite
npm run validate
npm run test
npm run test:e2e

# Check all service health
for container in $(docker ps --filter name=homeiq --format "{{.Names}}"); do
  echo "=== $container ==="
  docker inspect $container --format='{{.State.Health.Status}}' 2>/dev/null || echo "No health check"
done

# Monitor for final hour
watch -n 60 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```

### Deployment Rollback Procedures

#### Emergency Rollback (Critical Failure)

**Trigger Conditions:**
- Multiple service crashes
- Data corruption detected
- Critical security vulnerability
- Performance degradation >50%

**Emergency Rollback Script:**
```bash
#!/bin/bash
# emergency-rollback.sh

echo "EMERGENCY ROLLBACK INITIATED"
date

# Stop all services
docker-compose --profile production down --remove-orphans

# Restore previous images
# (Assumes images were tagged before rebuild)
for service in $(docker images --format "{{.Repository}}" | grep homeiq | sort -u); do
  docker tag $service:latest $service:failed-deployment
  docker tag $service:pre-rebuild $service:latest
done

# Restore database backups
echo "Restoring InfluxDB data..."
# (Add restore commands here)

echo "Restoring SQLite data..."
# (Add restore commands here)

# Restart all services with previous images
docker-compose --profile production up -d

# Wait for health checks
sleep 120

# Verify services
docker ps --format "table {{.Names}}\t{{.Status}}"

echo "EMERGENCY ROLLBACK COMPLETE"
date
```

#### Service-Specific Rollback

**For Individual Service Failures:**
```bash
# Example: Rolling back ai-pattern-service
SERVICE="ai-pattern-service"

# Stop the service
docker-compose stop $SERVICE

# Restore previous image
docker tag homeiq-$SERVICE:latest homeiq-$SERVICE:failed
docker tag homeiq-$SERVICE:phase2-backup homeiq-$SERVICE:latest

# Restart service
docker-compose up -d $SERVICE

# Verify health
sleep 30
docker ps --filter name=$SERVICE
curl -f http://localhost:$(docker port homeiq-$SERVICE | cut -d: -f2)/health
```

---

## Testing & Validation

### Test Strategy

**Levels of Testing:**
1. Unit Tests (per service)
2. Integration Tests (service-to-service)
3. End-to-End Tests (full workflow)
4. Performance Tests (baseline comparison)
5. Security Tests (vulnerability scanning)

### Test Execution Plan

#### Phase 1: Unit Testing

```bash
# Run all Python unit tests
npm run test:unit:python

# Run individual service tests
docker exec homeiq-data-api pytest /app/tests/ -v
docker exec homeiq-websocket pytest /app/tests/ -v
docker exec homeiq-admin pytest /app/tests/ -v

# Run all TypeScript unit tests
npm run test:unit:typescript

# Generate coverage reports
npm run test:coverage
```

**Success Criteria:**
- ✓ All tests passing
- ✓ Coverage ≥ 80% for all services
- ✓ No critical bugs introduced

#### Phase 2: Integration Testing

```bash
# Test InfluxDB write pipeline
# websocket-ingestion → InfluxDB → data-api query

# 1. Trigger event in Home Assistant
# 2. Verify event received by websocket-ingestion
docker logs homeiq-websocket --tail 50 | grep "Event received"

# 3. Query event from data-api
curl http://localhost:8006/api/v1/events?limit=1

# Test external API integrations
curl http://localhost:8009/api/v1/weather/current  # Weather API
curl http://localhost:8005/api/v1/sports/upcoming  # Sports API

# Test AI automation flow
curl -X POST http://localhost:8036/api/v1/automations/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "Turn on lights when motion detected"}'

# Test device intelligence
curl http://localhost:8028/api/v1/devices/health
```

**Success Criteria:**
- ✓ Data flowing through entire pipeline
- ✓ External APIs responding correctly
- ✓ AI services generating valid outputs
- ✓ Device intelligence classifying correctly

#### Phase 3: End-to-End Testing

```bash
# Run Playwright E2E tests
npm run test:e2e

# E2E Test Scenarios:
# 1. User opens health dashboard, views service status
# 2. User navigates to AI automation UI
# 3. User creates natural language automation
# 4. System generates automation YAML
# 5. Automation linter validates YAML
# 6. User views device health
# 7. User checks energy correlations
```

**Success Criteria:**
- ✓ All E2E scenarios passing
- ✓ No UI errors in console
- ✓ Performance within acceptable range

#### Phase 4: Performance Testing

```bash
# Baseline performance metrics
# (Run before and after rebuild)

# API response times
for endpoint in \
  "http://localhost:8006/health" \
  "http://localhost:8006/api/v1/devices" \
  "http://localhost:8006/api/v1/events?limit=100"; do
  echo "Testing $endpoint"
  time curl -s $endpoint > /dev/null
done

# Frontend load times
# Use browser dev tools or Lighthouse

# ML inference times
time docker exec homeiq-ml-service python -c "
from ml_service import model
result = model.predict(sample_data)
print(result)
"

# Database query performance
docker exec homeiq-influxdb influx query '
from(bucket: "home_assistant_events")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "home_assistant_events")
  |> count()
' --profilers query-duration
```

**Success Criteria:**
- ✓ API response times within 10% of baseline
- ✓ Frontend load times within 10% of baseline
- ✓ ML inference times within 10% of baseline
- ✓ Database queries within 15% of baseline

#### Phase 5: Security Testing

```bash
# Vulnerability scanning
# Run Trivy on all images
for image in $(docker images --format "{{.Repository}}:{{.Tag}}" | grep homeiq); do
  echo "Scanning $image"
  trivy image --severity HIGH,CRITICAL $image
done

# Check for exposed secrets
# (Ensure .env not in version control)
git status | grep .env && echo "WARNING: .env may be tracked"

# Verify API authentication
curl http://localhost:8006/api/v1/devices  # Should require auth
curl -H "X-API-Key: invalid" http://localhost:8006/api/v1/devices  # Should fail

# Check for open ports
nmap localhost -p 1-65535 | grep open
```

**Success Criteria:**
- ✓ No HIGH or CRITICAL vulnerabilities
- ✓ No secrets exposed in version control
- ✓ Authentication working correctly
- ✓ Only intended ports exposed

### Continuous Monitoring

**Post-Deployment Monitoring (48 hours):**
```bash
# Monitor service health
watch -n 300 'docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "homeiq|NAMES"'

# Monitor resource usage
watch -n 300 'docker stats --no-stream --format "table {{.Name}}\t{{CPUPerc}}\t{{MemUsage}}"'

# Monitor logs for errors
for container in $(docker ps --filter name=homeiq --format "{{.Names}}"); do
  docker logs $container --since 1h 2>&1 | grep -i error >> deployment_errors.log
done

# Monitor Jaeger for service traces
curl http://localhost:16686/api/traces?service=websocket-ingestion&limit=10

# Check InfluxDB write rates
docker exec homeiq-influxdb influx query '
from(bucket: "home_assistant_events")
  |> range(start: -1h)
  |> group()
  |> count()
'
```

**Alerting:**
- Set up alerts for service health failures
- Monitor memory usage >90%
- Alert on error rate increases
- Track response time degradation

---

## Rollback Procedures

### Pre-Rollback Checklist

Before initiating rollback:
1. ✓ Identify specific failure (service, issue, impact)
2. ✓ Determine if partial or full rollback needed
3. ✓ Notify stakeholders
4. ✓ Capture diagnostic information
5. ✓ Verify backups available

### Full System Rollback

**Scenario:** Critical system-wide failure requiring full rollback

**Steps:**
```bash
cd /c/cursor/HomeIQ

# 1. Stop all services
docker-compose --profile production down --remove-orphans

# 2. Restore Docker images (if tagged before rebuild)
for service in $(docker images --format "{{.Repository}}" | grep homeiq | sort -u); do
  if docker images | grep -q "$service:pre-rebuild"; then
    docker tag $service:latest $service:failed-rebuild
    docker tag $service:pre-rebuild $service:latest
    echo "Restored $service"
  fi
done

# 3. Restore database backups
# InfluxDB
BACKUP_FILE=$(ls -t backups/influxdb_data_*.tar.gz | head -1)
docker run --rm -v homeiq_influxdb_data:/data -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/$(basename $BACKUP_FILE) -C /data

# SQLite
BACKUP_FILE=$(ls -t backups/sqlite_data_*.tar.gz | head -1)
docker run --rm -v homeiq_sqlite-data:/data -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/$(basename $BACKUP_FILE) -C /data

# 4. Restore environment configuration
cp .env.backup_* .env

# 5. Restart all services
docker-compose --profile production up -d

# 6. Wait for health checks
sleep 120

# 7. Verify services
docker ps --format "table {{.Names}}\t{{.Status}}"

# 8. Run basic tests
npm run validate
curl http://localhost:8006/health
curl http://localhost:8001/health
curl http://localhost:3000
```

### Partial Service Rollback

**Scenario:** Individual service or service group failure

**Example: Rolling back AI/ML services**
```bash
# Stop affected services
docker-compose stop ml-service ai-pattern-service ha-ai-agent-service rule-recommendation-ml

# Restore previous images
for service in ml-service ai-pattern-service ha-ai-agent-service rule-recommendation-ml; do
  docker tag homeiq-$service:latest homeiq-$service:failed-phase3
  docker tag homeiq-$service:phase2-backup homeiq-$service:latest
done

# Restart services
docker-compose up -d ml-service ai-pattern-service ha-ai-agent-service rule-recommendation-ml

# Verify health
sleep 60
docker ps --filter name="ml-service|ai-pattern|ha-ai-agent|rule-recommendation" --format "table {{.Names}}\t{{.Status}}"
```

### Post-Rollback Actions

1. **Root Cause Analysis**
   - Review logs: `docker logs <container> > rollback_analysis.log`
   - Check resource metrics
   - Identify specific failure point

2. **Documentation**
   - Document failure scenario
   - Record rollback steps taken
   - Note lessons learned

3. **Communication**
   - Notify stakeholders of rollback completion
   - Provide status update
   - Share timeline for retry

4. **Planning Next Attempt**
   - Review what went wrong
   - Update deployment plan
   - Add additional safeguards
   - Schedule retry deployment

---

## Timeline & Resources

### Overall Timeline (6 Weeks)

| Week | Phase | Activities | Risk Level | Effort |
|------|-------|------------|------------|--------|
| 0 | Pre-Deployment Prep | Backup, diagnose websocket issue, verify infrastructure | LOW | 1 day |
| 1 | Phase 1: Critical Compatibility | Update SQLAlchemy, aiosqlite, FastAPI, standardize versions | LOW-MED | 5 days |
| 2 | Phase 2: Standard Libraries | Update pytest, tenacity, influxdb3-python, MQTT migration | LOW-MED | 5 days |
| 3 | Phase 3: ML/AI Upgrades | NumPy 2.x, Pandas 3.0, scikit-learn, OpenAI SDK | HIGH | 5 days |
| 4 | Phase 4: Frontend Updates | Conservative path: minor updates; Aggressive: React 19, Vite 7 | MED-HIGH | 5 days |
| 5 | Deployment | Staged deployment across 5 days | LOW-MED | 5 days |
| 6 | Post-Deployment | Validation, monitoring, documentation | LOW | 5 days |

**Total Duration:** 6 weeks (with buffer)

### Resource Requirements

#### Personnel

1. **Backend Engineer (Senior)** - Lead
   - Python services rebuild (Phases 1-3)
   - Docker/deployment expertise
   - 100% allocation

2. **Frontend Engineer (Mid-Senior)**
   - React/Node.js services (Phase 4)
   - UI testing and validation
   - 50% allocation

3. **ML Engineer**
   - ML/AI library upgrades (Phase 3)
   - Model validation and testing
   - 100% allocation Week 3 only

4. **DevOps Engineer**
   - Deployment automation
   - Monitoring setup
   - Rollback procedures
   - 50% allocation

5. **QA Engineer**
   - Test execution
   - Validation
   - Issue tracking
   - 75% allocation

#### Infrastructure

**Development/Testing:**
- Staging environment (Docker Compose, mirroring production)
- Isolated ML testing environment
- CI/CD pipeline updates

**Production:**
- Existing Windows Docker environment
- Sufficient disk space for image builds (~20GB)
- Sufficient memory for parallel builds (~16GB)

**Backup Storage:**
- 50GB for database backups
- Version-controlled image backups

### Cost Estimate

**Direct Costs:**
- Personnel: 5 team members × 6 weeks (varies by allocation)
- Infrastructure: Minimal (existing environment)
- Tools: Docker licenses (if applicable), CI/CD credits

**Indirect Costs:**
- Testing time
- Potential downtime (planned: 0, unplanned: buffer 4 hours)
- Rollback scenarios

**Total Estimated Cost:** (Calculate based on team hourly rates)

---

## Post-Deployment Checklist

### Immediate Post-Deployment (Day 1)

- [ ] All 48 services running
- [ ] All services showing "healthy" status
- [ ] No error logs in past hour
- [ ] API endpoints responding correctly
  - [ ] http://localhost:8086/health (InfluxDB)
  - [ ] http://localhost:8001/health (websocket-ingestion)
  - [ ] http://localhost:8004/health (admin-api)
  - [ ] http://localhost:8006/health (data-api)
- [ ] Frontend dashboards loading
  - [ ] http://localhost:3000 (health-dashboard)
  - [ ] http://localhost:3001 (ai-automation-ui)
- [ ] Jaeger UI accessible (http://localhost:16686)
- [ ] InfluxDB receiving data
- [ ] Data-api queries working
- [ ] External integrations active (weather, sports, etc.)

### 24-Hour Validation (Day 2)

- [ ] No service restarts in 24 hours
- [ ] Resource usage within normal ranges
  - [ ] Memory usage <80% for all services
  - [ ] CPU usage <70% average
- [ ] No critical errors in logs
- [ ] Data flowing correctly through pipeline
  - [ ] HA events → websocket → InfluxDB → data-api
- [ ] AI/ML services producing valid outputs
- [ ] Device intelligence classifying correctly
- [ ] Automation linter validating successfully

### 48-Hour Stability (Day 3)

- [ ] All unit tests passing
- [ ] All E2E tests passing
- [ ] Performance within 10% of baseline
  - [ ] API response times
  - [ ] Frontend load times
  - [ ] ML inference times
- [ ] No memory leaks detected
- [ ] No database issues
- [ ] External API integrations stable

### Week 1 Review

- [ ] Full test suite passing
- [ ] Performance metrics stable
- [ ] No unplanned restarts
- [ ] User acceptance testing complete
- [ ] Documentation updated
- [ ] Team trained on changes
- [ ] Rollback procedures tested (in staging)

### Week 2 Sign-Off

- [ ] All success criteria met
- [ ] No critical issues outstanding
- [ ] Monitoring alerts configured
- [ ] Backup procedures verified
- [ ] Post-mortem completed (if issues occurred)
- [ ] Lessons learned documented
- [ ] Stakeholder sign-off obtained

---

## Appendices

### Appendix A: Service Dependency Map

```
Infrastructure Layer:
  ├─ InfluxDB (8086) - Time-series database
  └─ Jaeger (16686, 4317, 4318) - Distributed tracing

Core Services Layer:
  ├─ data-api (8006) - [depends: influxdb]
  ├─ websocket-ingestion (8001) - [depends: influxdb, data-api]
  ├─ admin-api (8004) - [depends: influxdb, websocket, data-api]
  └─ data-retention (8080) - [depends: influxdb]

Frontend Layer:
  ├─ health-dashboard (3000) - [depends: data-api, admin-api]
  └─ ai-automation-ui (3001) - [depends: data-api, ai-automation-service]

External Integration Layer:
  ├─ weather-api (8009) - [depends: influxdb]
  ├─ sports-api (8005) - [depends: influxdb]
  ├─ carbon-intensity (8010) - [depends: influxdb]
  ├─ electricity-pricing (8011) - [depends: influxdb]
  ├─ air-quality (8012) - [depends: influxdb]
  ├─ calendar-service (8013) - [depends: influxdb]
  ├─ smart-meter-service (8014) - [depends: influxdb]
  └─ log-aggregator (8015) - [depends: all services]

AI/ML Services Layer:
  ├─ ai-core-service (8018) - [depends: data-api, influxdb]
  ├─ ai-pattern-service (8034) - [depends: data-api, ml-service]
  ├─ ai-automation-service-new (8036) - [depends: ai-core, automation-linter]
  ├─ ai-query-service (8035) - [depends: data-api, openai-service]
  ├─ ai-training-service (8033) - [depends: data-api, ml-service]
  ├─ ai-code-executor (8030) - [depends: data-api]
  ├─ ha-ai-agent-service (8030) - [depends: openai-service, rag-service]
  ├─ proactive-agent-service (8031) - [depends: ai-pattern-service]
  ├─ ml-service (8025) - [depends: data-api]
  ├─ openvino-service (8026) - [depends: ml-service]
  ├─ rag-service (8027) - [depends: data-api]
  ├─ openai-service (8020) - [depends: data-api]
  └─ ner-service (8031) - [depends: openai-service]

Device Management Layer:
  ├─ device-intelligence-service (8028) - [depends: data-api, ml-service]
  ├─ device-health-monitor (8019) - [depends: device-intelligence]
  ├─ device-context-classifier (8032) - [depends: device-intelligence]
  ├─ device-database-client (8022) - [depends: data-api]
  ├─ device-recommender (8023) - [depends: device-intelligence]
  ├─ device-setup-assistant (8021) - [depends: device-intelligence]
  └─ ha-setup-service (8024) - [depends: data-api]

Automation Layer:
  ├─ automation-linter (8016) - [standalone]
  ├─ automation-miner (8029) - [depends: data-api, ai-pattern-service]
  ├─ blueprint-index (8038) - [depends: data-api]
  ├─ blueprint-suggestion-service (8039) - [depends: blueprint-index]
  ├─ yaml-validation-service (8037) - [depends: automation-linter]
  └─ api-automation-edge (8041) - [depends: ai-automation-service]

Analytics Layer:
  ├─ energy-correlator (8017) - [depends: data-api]
  └─ rule-recommendation-ml (8040) - [depends: ml-service, automation-miner]
```

### Appendix B: Port Allocation Reference

| Port | Service | Protocol | Purpose |
|------|---------|----------|---------|
| 3000 | health-dashboard | HTTP | Health monitoring UI |
| 3001 | ai-automation-ui | HTTP | AI automation interface |
| 4317 | jaeger | gRPC | OTLP gRPC receiver |
| 4318 | jaeger | HTTP | OTLP HTTP receiver |
| 8001 | websocket-ingestion | HTTP | HA event ingestion |
| 8004 | admin-api | HTTP | System admin/control |
| 8005 | sports-api | HTTP | Sports data |
| 8006 | data-api | HTTP | Data query hub |
| 8009 | weather-api | HTTP | Weather data |
| 8010 | carbon-intensity | HTTP | Carbon metrics |
| 8011 | electricity-pricing | HTTP | Energy pricing |
| 8012 | air-quality | HTTP | Air quality data |
| 8013 | calendar-service | HTTP | Calendar events |
| 8014 | smart-meter-service | HTTP | Meter readings |
| 8015 | log-aggregator | HTTP | Log collection |
| 8016 | automation-linter | HTTP | YAML validation |
| 8017 | energy-correlator | HTTP | Energy analytics |
| 8018 | ai-core-service | HTTP | AI orchestration |
| 8019 | device-health-monitor | HTTP | Device monitoring |
| 8020 | openai-service | HTTP | OpenAI integration |
| 8021 | device-setup-assistant | HTTP | Device onboarding |
| 8022 | device-database-client | HTTP | Device DB access |
| 8023 | device-recommender | HTTP | Device suggestions |
| 8024 | ha-setup-service | HTTP | HA setup wizard |
| 8025 | ml-service | HTTP | ML operations |
| 8026 | openvino-service | HTTP | Model inference |
| 8027 | rag-service | HTTP | RAG operations |
| 8028 | device-intelligence | HTTP | Device classification |
| 8029 | automation-miner | HTTP | Automation discovery |
| 8030 | ai-code-executor | HTTP | Code execution |
| 8031 | proactive-agent | HTTP | Proactive suggestions |
| 8032 | device-context-classifier | HTTP | Device classification |
| 8033 | ai-training-service | HTTP | Model training |
| 8034 | ai-pattern-service | HTTP | Pattern detection |
| 8035 | ai-query-service | HTTP | NL query processing |
| 8036 | ai-automation-service | HTTP | Automation generation |
| 8037 | yaml-validation | HTTP | YAML validation API |
| 8038 | blueprint-index | HTTP | Blueprint registry |
| 8039 | blueprint-suggestion | HTTP | Blueprint recommendations |
| 8040 | rule-recommendation-ml | HTTP | ML-based rule suggestions |
| 8041 | api-automation-edge | HTTP | Edge automation API |
| 8080 | data-retention | HTTP | Data lifecycle mgmt |
| 8086 | influxdb | HTTP | Time-series database |
| 8501 | observability-dashboard | HTTP | Streamlit monitoring |
| 16686 | jaeger | HTTP | Tracing UI |

### Appendix C: Environment Variables Reference

**Critical Environment Variables:**
- `HOME_ASSISTANT_URL` / `HA_HTTP_URL` - Home Assistant HTTP endpoint
- `HOME_ASSISTANT_TOKEN` / `HA_TOKEN` - Home Assistant auth token
- `NABU_CASA_URL` - Nabu Casa cloud endpoint
- `NABU_CASA_TOKEN` - Nabu Casa auth token
- `INFLUXDB_URL` - InfluxDB endpoint
- `INFLUXDB_TOKEN` - InfluxDB auth token
- `INFLUXDB_ORG` - InfluxDB organization
- `INFLUXDB_BUCKET` - InfluxDB bucket name
- `OPENAI_API_KEY` - OpenAI API key
- `WEATHER_API_KEY` - OpenWeather API key
- `API_KEY` - Shared service API key
- `LOG_LEVEL` - Logging verbosity (INFO, DEBUG, etc.)
- `DEPLOYMENT_MODE` - Deployment mode (production, development)
- `OTLP_ENDPOINT` - OpenTelemetry endpoint (Jaeger)

### Appendix D: Useful Commands

**Docker Management:**
```bash
# View all running services
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check service health
docker ps --filter health=unhealthy

# View service logs
docker logs -f homeiq-<service-name>

# Restart specific service
docker-compose restart <service-name>

# Rebuild and restart service
docker-compose up -d --no-deps --build <service-name>

# Stop all services
docker-compose down --remove-orphans

# Clean up unused images
docker image prune -a

# Check resource usage
docker stats --no-stream
```

**Testing:**
```bash
# Run all tests
npm run validate

# Run Python unit tests
npm run test:unit:python

# Run TypeScript unit tests
npm run test:unit:typescript

# Run E2E tests
npm run test:e2e

# Generate coverage reports
npm run test:coverage
```

**Monitoring:**
```bash
# Check service health endpoints
for port in 8001 8004 8006 8009 8086; do
  echo "Port $port:"
  curl -f http://localhost:$port/health 2>/dev/null && echo "OK" || echo "FAIL"
done

# Monitor logs for errors
docker-compose logs -f --tail=100 | grep -i error

# Check InfluxDB data
docker exec homeiq-influxdb influx query 'from(bucket:"home_assistant_events") |> range(start:-1h) |> count()'

# View Jaeger traces
open http://localhost:16686
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-04 | Claude Code | Initial comprehensive rebuild and deployment plan created |

---

**End of Document**

For questions or clarifications about this plan, please refer to:
- [Library Upgrade Summary](c:\cursor\HomeIQ\docs\planning\upgrade-summary.md)
- [Deployment Guide](c:\cursor\HomeIQ\docs\DEPLOYMENT_GUIDE.md)
- [Docker Compose Configuration](c:\cursor\HomeIQ\docker-compose.yml)
- [Deployment Script](c:\cursor\HomeIQ\scripts\deploy.sh)
