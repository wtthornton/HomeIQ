# Epic 40: Dual Deployment Configuration (Test & Production)

**Epic ID:** 40  
**Title:** Dual Deployment Configuration (Test & Production)  
**Status:** Planning  
**Priority:** High  
**Complexity:** High  
**Timeline:** 4-6 weeks  
**Story Points:** 40-55  
**Type:** Infrastructure & Deployment  
**Depends on:** Epic 33-35 (Synthetic External Data Generation) - Must be implemented LAST

---

## Epic Goal

Create completely isolated test and production deployment configurations with full database separation, container isolation, and clear deployment commands. Test deployment uses only synthetic/mock data creation, disables external API feeds, but keeps all AI services operational. Production deployment explicitly blocks data generation services.

## Epic Description

### Current Problem

**Lack of Environment Isolation:**
- No clear separation between test and production environments
- Shared databases and infrastructure make testing risky
- External API services (weather, carbon, etc.) consume quota during testing
- No safeguards to prevent data generation services in production
- Difficult to test InfluxDB version upgrades safely
- Test HA container exists but not integrated into a complete test deployment

**Testing Challenges:**
- Cannot test synthetic data generation without affecting production
- External API calls consume real API quotas during testing
- Production HA connection prevents testing with mock data
- No way to validate deployment changes before production

### Solution

**Dual Deployment Architecture (NUC-Optimized):**
1. **Test Deployment** (`docker-compose.test.yml`):
   - **Option A (Recommended)**: Separate InfluxDB bucket in same instance (lighter, 8GB NUC-friendly)
   - **Option B**: Separate InfluxDB instance on port 8087 (for version upgrade testing, requires 16GB NUC)
   - Separate SQLite databases
   - Separate Docker networks
   - HA test container integration
   - External API services disabled (weather, carbon, electricity, air-quality, calendar, smart-meter, sports-data)
   - OpenAI/AI services enabled (patterns, Ask AI, all downstream AI)
   - Synthetic data generators enabled
   - Mock data creation services enabled
   - Environment variable: `DEPLOYMENT_MODE=test`
   - Resource limits optimized for NUC (memory/CPU constraints)

2. **Production Deployment** (`docker-compose.prod.yml`):
   - All external API services enabled
   - OpenAI/AI services enabled
   - Data generation services explicitly disabled/blocked
   - Production HA connection only
   - Environment variable: `DEPLOYMENT_MODE=production`
   - Validation checks prevent test services from starting
   - Resource limits for NUC deployment

**Important: NUC Resource Constraints:**
- **Test and Production are MUTUALLY EXCLUSIVE** - cannot run both simultaneously on 8GB NUC
- **16GB NUC**: Can optionally run both with careful resource management (not recommended for daily use)
- **Resource-efficient**: Separate buckets preferred over separate instances for 8GB NUC

**Deployment Commands:**
- `./scripts/deploy.sh test` - Deploy to test environment
- `./scripts/deploy.sh production` or `./scripts/deploy.sh prod` - Deploy to production
- Commands handle all environment setup, validation, and service orchestration

### Existing System Context

**Current Deployment Files:**
- `docker-compose.yml` - Main production file (all services)
- `docker-compose.dev.yml` - Development with ha-simulator
- `docker-compose.prod.yml` - Production overrides
- `docker-compose.minimal.yml` - Minimal services
- Test profile already exists for HA test container

**HA Test Container (Already Implemented):**
- `home-assistant-test` service in `docker-compose.yml` (profile: test)
- Port 8124 for test HA web UI
- `websocket-ingestion-test` service (profile: test, port 8002)
- Separate InfluxDB bucket: `home_assistant_events_test`
- Setup scripts: `scripts/setup_ha_test.sh`

**External Data Services (To Disable in Test):**
- `weather-api` (Port 8009)
- `carbon-intensity-service` (Port 8010)
- `electricity-pricing-service` (Port 8011)
- `air-quality-service` (Port 8012)
- `calendar-service` (Port 8013)
- `smart-meter-service` (Port 8014)
- `sports-data` (Port 8005)

**AI Services (Keep Enabled in Both):**
- `ai-automation-service` (Port 8018/8024)
- `ai-core-service` (Port 8018)
- `openai-service` (Port 8020)
- `device-intelligence-service` (Port 8019/8028)
- `automation-miner` (Port 8019/8029)
- Pattern detection, Ask AI, all downstream AI processing

**Data Generation Services (Test Only, Block in Production):**
- Synthetic data generators (Epic 33-35)
- Mock data creation services
- Test data seeding services

## Business Value

- **Safe Testing**: Complete isolation allows testing without production risk
- **Cost Savings**: No external API quota consumption during testing
- **Version Upgrade Testing**: Separate InfluxDB instance enables safe upgrade testing
- **Production Safety**: Explicit blocks prevent accidental data generation in production
- **Development Velocity**: Faster iteration with synthetic data vs waiting for real APIs
- **Reproducibility**: Test environment is consistent and reproducible
- **CI/CD Ready**: Test deployment can be used in automated pipelines

## Success Criteria

- ✅ Test deployment completely isolated from production
- ✅ Separate InfluxDB buckets (default) or instances (optional) for test and production
- ✅ Separate SQLite databases for metadata
- ✅ External API services disabled in test mode (saves ~500MB memory)
- ✅ AI services operational in both environments
- ✅ Production deployment blocks data generation services
- ✅ Clear deployment commands (`deploy to test`, `deploy to prod`)
- ✅ Environment detection and validation
- ✅ HA test container integrated into test deployment
- ✅ Resource limits configured for NUC constraints (memory/CPU)
- ✅ Documentation updated with deployment instructions
- ✅ Validation scripts prevent misconfiguration
- ✅ NUC resource constraints documented (8GB vs 16GB options)
- ✅ Mutually exclusive deployment pattern clarified (test/prod don't run simultaneously)

## Technical Architecture

### Single Home NUC Deployment Context

**Hardware Constraints (Per Context7 KB):**
- **Recommended**: Intel NUC i3/i5, 8-16GB RAM
- **Production Stack**: ~4-6GB RAM (all services)
- **InfluxDB Memory**: 1-2GB per instance
- **Constraint**: Running both test and production simultaneously would require ~8GB+ RAM

**Design Decision:**
- **Option A (8GB NUC)**: Separate buckets in same InfluxDB instance (lightweight, ~2GB total)
- **Option B (16GB NUC)**: Separate InfluxDB instances (enables version upgrade testing, ~4GB total)
- **Mutually Exclusive**: Test and production deployments should not run simultaneously on NUC
- **Resource Limits**: All services have memory/CPU limits to prevent NUC overload

### Deployment Architecture

**Test Deployment (DEPLOYMENT_MODE=test):**
```
┌─────────────────────────────────────────────────────────────┐
│ Test Deployment - NUC Optimized                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Option A: Shared InfluxDB Instance (Port 8086) ⭐          │
│   - Bucket: home_assistant_events_test (separate bucket)    │
│   - Memory: ~2GB (shared with production when switching)    │
│   - Lightweight, NUC-friendly                               │
│                                                             │
│ Option B: Separate InfluxDB Instance (Port 8087)           │
│   - Bucket: home_assistant_events_test                      │
│   - Memory: ~2GB (separate instance, 16GB NUC only)        │
│   - Enables version upgrade testing                         │
│                                                             │
│ SQLite Test Database                                        │
│   - Location: ./data/test/metadata.db                       │
│   - Memory: <50MB                                           │
│                                                             │
│ HA Test Container (Port 8124)                              │
│   └─> websocket-ingestion-test (Port 8002)                 │
│       └─> InfluxDB Test Bucket/Instance                     │
│                                                             │
│ External API Services: DISABLED ❌                          │
│   - Saves ~500MB memory (6 services disabled)              │
│                                                             │
│ AI Services: ENABLED ✅                                     │
│   - Memory: ~1-2GB (same as production)                    │
│                                                             │
│ Data Generation: ENABLED ✅                                 │
│   - Memory: ~200-500MB (synthetic generators)              │
│                                                             │
│ Network: homeiq-network-test                                │
│ Resource Limits: Memory <6GB, CPU <4 cores                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Production Deployment (DEPLOYMENT_MODE=production):
┌─────────────────────────────────────────────────────────────┐
│ Production Deployment - NUC Optimized                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ InfluxDB Production Instance (Port 8086)                    │
│   - Bucket: home_assistant_events                           │
│   - Memory: ~2GB                                            │
│                                                             │
│ SQLite Production Database                                  │
│   - Location: ./data/metadata.db                            │
│   - Memory: <50MB                                           │
│                                                             │
│ Production HA (192.168.1.86:8123)                          │
│   └─> websocket-ingestion (Port 8001)                      │
│       └─> InfluxDB Production Instance                      │
│                                                             │
│ External API Services: ENABLED ✅                           │
│   - Memory: ~500MB (6 services enabled)                    │
│                                                             │
│ AI Services: ENABLED ✅                                     │
│   - Memory: ~1-2GB                                          │
│                                                             │
│ Data Generation: BLOCKED ❌                                 │
│   - Validation prevents data generation services            │
│                                                             │
│ Network: homeiq-network                                     │
│ Resource Limits: Memory <6GB, CPU <4 cores                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

⚠️ IMPORTANT: Test and Production are MUTUALLY EXCLUSIVE on NUC
   - Switch between deployments (stop one, start other)
   - Cannot run both simultaneously on 8GB NUC
   - 16GB NUC: Can optionally run both (not recommended)
```

### Resource Usage Breakdown (Single Home NUC)

**Test Deployment (Option A - Separate Bucket):**
- InfluxDB: ~2GB (shared instance, test bucket)
- Services: ~2-3GB (AI services, websocket, etc.)
- Test containers: ~500MB (HA test, test ingestion)
- **Total**: ~4.5-5.5GB (fits 8GB NUC ✅)

**Production Deployment:**
- InfluxDB: ~2GB
- Services: ~3-4GB (all services including external APIs)
- **Total**: ~5-6GB (fits 8GB NUC ✅)

**Both Running Simultaneously (16GB NUC only):**
- **Total**: ~9-11GB (requires 16GB NUC, not recommended)

### File Structure

```
docker-compose.yml              # Main production (all services)
docker-compose.test.yml         # NEW: Complete test deployment
docker-compose.prod.yml         # Production overrides (existing, enhanced)
docker-compose.dev.yml          # Development (existing, unchanged)

infrastructure/
  env.example                   # Template (updated with DEPLOYMENT_MODE)
  env.production                # Production environment
  env.test                      # NEW: Test environment template

scripts/
  deploy.sh                     # Enhanced with test/prod commands
  deploy-test.sh                # NEW: Test deployment script
  deploy-prod.sh                # NEW: Production deployment script
  validate-deployment.sh        # NEW: Deployment validation

data/
  metadata.db                   # Production SQLite
  test/
    metadata.db                 # NEW: Test SQLite database
```

### Environment Variables

**Test Environment (`env.test`):**
```bash
DEPLOYMENT_MODE=test

# InfluxDB Test Configuration (Option A: Separate Bucket, Option B: Separate Instance)
# Option A (Default - 8GB NUC): Use shared instance with separate bucket
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_ORG=homeiq-test
INFLUXDB_BUCKET=home_assistant_events_test
INFLUXDB_TOKEN=homeiq-test-token

# Option B (Optional - 16GB NUC): Use separate instance for version upgrade testing
# INFLUXDB_URL=http://influxdb-test:8087
# INFLUXDB_ORG=homeiq-test
# INFLUXDB_BUCKET=home_assistant_events_test
# INFLUXDB_TOKEN=homeiq-test-token
# USE_SEPARATE_INFLUXDB_INSTANCE=true

# HA Test Container
HA_TEST_URL=http://home-assistant-test:8123
HA_TEST_WS_URL=ws://home-assistant-test:8123/api/websocket
HA_TEST_TOKEN=${HA_TEST_TOKEN}

# SQLite Test Database
DATABASE_URL=sqlite+aiosqlite:///./data/test/metadata.db

# External API Services - DISABLED
ENABLE_WEATHER_API=false
ENABLE_CARBON_INTENSITY=false
ENABLE_ELECTRICITY_PRICING=false
ENABLE_AIR_QUALITY=false
ENABLE_CALENDAR=false
ENABLE_SMART_METER=false
ENABLE_SPORTS_DATA=false

# AI Services - ENABLED
ENABLE_AI_AUTOMATION=true
ENABLE_OPENAI_SERVICE=true
ENABLE_DEVICE_INTELLIGENCE=true

# Data Generation - ENABLED
ENABLE_SYNTHETIC_DATA_GENERATION=true
ENABLE_MOCK_DATA_CREATION=true
```

**Production Environment (`env.production`):**
```bash
DEPLOYMENT_MODE=production

# InfluxDB Production Instance
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events
INFLUXDB_TOKEN=${INFLUXDB_TOKEN}

# Production HA
HA_HTTP_URL=${HA_HTTP_URL}
HA_WS_URL=${HA_WS_URL}
HA_TOKEN=${HA_TOKEN}

# SQLite Production Database
DATABASE_URL=sqlite+aiosqlite:///./data/metadata.db

# External API Services - ENABLED
ENABLE_WEATHER_API=true
ENABLE_CARBON_INTENSITY=true
ENABLE_ELECTRICITY_PRICING=true
ENABLE_AIR_QUALITY=true
ENABLE_CALENDAR=true
ENABLE_SMART_METER=true
ENABLE_SPORTS_DATA=true

# AI Services - ENABLED
ENABLE_AI_AUTOMATION=true
ENABLE_OPENAI_SERVICE=true
ENABLE_DEVICE_INTELLIGENCE=true

# Data Generation - DISABLED
ENABLE_SYNTHETIC_DATA_GENERATION=false
ENABLE_MOCK_DATA_CREATION=false
```

## Stories

### Story 40.1: Test Deployment Docker Compose Configuration
- **Story Points**: 8
- **Priority**: P0
- **Effort**: 6-8 hours
- **Description**: Create `docker-compose.test.yml` with complete test environment setup including separate InfluxDB instance, test HA container integration, disabled external API services, and enabled AI services
- **Acceptance Criteria**:
  - ✅ `docker-compose.test.yml` created with all test services
  - ✅ Separate InfluxDB test instance on port 8087
  - ✅ HA test container and websocket-ingestion-test integrated
  - ✅ External API services excluded or disabled
  - ✅ AI services included and configured
  - ✅ Separate Docker network (homeiq-network-test)
  - ✅ Separate volumes for test data isolation
  - ✅ Environment variable `DEPLOYMENT_MODE=test` set

### Story 40.2: Production Deployment Safeguards
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Enhance `docker-compose.prod.yml` with explicit blocks for data generation services and validation checks to prevent test services from starting in production
- **Acceptance Criteria**:
  - ✅ Production compose file explicitly excludes data generation services
  - ✅ Validation script prevents data generation services in production
  - ✅ Environment variable validation on startup
  - ✅ Clear error messages if misconfiguration detected
  - ✅ Production deployment blocks test profile services
  - ✅ Documentation of production safeguards

### Story 40.3: InfluxDB Test Configuration (Separate Bucket or Instance)
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 4-5 hours
- **Description**: Configure InfluxDB for test environment with two options: (A) Separate bucket in shared instance (8GB NUC-friendly) or (B) Separate instance on port 8087 (16GB NUC, enables version upgrade testing). Default to Option A for NUC compatibility.
- **Acceptance Criteria**:
  - ✅ Option A: Test bucket (`home_assistant_events_test`) in shared InfluxDB instance (default)
  - ✅ Option B: Separate InfluxDB test instance on port 8087 (configurable, 16GB NUC only)
  - ✅ Separate initialization with test org/bucket/token
  - ✅ Separate Docker volume for test InfluxDB data (Option B)
  - ✅ Version can be changed independently for upgrade testing (Option B)
  - ✅ Test services connect to test InfluxDB bucket/instance
  - ✅ Production services never connect to test bucket/instance
  - ✅ Resource limits configured for NUC constraints
  - ✅ Documentation explains both options and when to use each

### Story 40.4: Test Environment Configuration Files
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Create `infrastructure/env.test` template file with all test environment variables configured (disabled external APIs, enabled AI services, test database paths)
- **Acceptance Criteria**:
  - ✅ `infrastructure/env.test` template created
  - ✅ All external API services disabled via environment variables
  - ✅ AI services enabled and configured
  - ✅ Test database paths configured
  - ✅ Test HA container connection configured
  - ✅ Documentation for test environment setup

### Story 40.5: Deployment Script Enhancement
- **Story Points**: 8
- **Priority**: P0
- **Effort**: 6-8 hours
- **Description**: Enhance `scripts/deploy.sh` with test and production deployment commands, environment validation, and service orchestration logic
- **Acceptance Criteria**:
  - ✅ `./scripts/deploy.sh test` command works
  - ✅ `./scripts/deploy.sh production` or `./scripts/deploy.sh prod` works
  - ✅ Environment validation before deployment
  - ✅ Automatic environment file selection (.env.test vs .env.production)
  - ✅ Service health checks after deployment
  - ✅ Clear output showing which environment is deploying
  - ✅ Error handling and rollback on failure

### Story 40.6: Service Environment Detection
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 4-5 hours
- **Description**: Add environment detection logic to services to automatically configure behavior based on `DEPLOYMENT_MODE` environment variable (disable external APIs in test, block data generation in production)
- **Acceptance Criteria**:
  - ✅ Services read `DEPLOYMENT_MODE` environment variable
  - ✅ External API services skip initialization in test mode
  - ✅ Data generation services block startup in production mode
  - ✅ AI services work in both modes
  - ✅ Logging shows deployment mode on startup
  - ✅ Health checks reflect deployment mode

### Story 40.7: Test Deployment Integration Tests
- **Story Points**: 5
- **Priority**: P1
- **Effort**: 4-5 hours
- **Description**: Create integration tests that validate test deployment isolation, service configuration, and that external APIs are properly disabled
- **Acceptance Criteria**:
  - ✅ Integration test for test deployment startup
  - ✅ Test validates external API services are disabled
  - ✅ Test validates AI services are enabled
  - ✅ Test validates separate databases are used
  - ✅ Test validates test HA container connection
  - ✅ Test validates production deployment blocks data generation

### Story 40.8: Production Deployment Validation Scripts
- **Story Points**: 3
- **Priority**: P1
- **Effort**: 2-3 hours
- **Description**: Create validation scripts that run before production deployment to ensure no test services are included, data generation is blocked, and all required production services are present
- **Acceptance Criteria**:
  - ✅ `scripts/validate-deployment.sh` created
  - ✅ Validates no test services in production compose
  - ✅ Validates data generation services are blocked
  - ✅ Validates required production services present
  - ✅ Validates environment variables are correct
  - ✅ Clear error messages for validation failures

### Story 40.9: Documentation & Deployment Guide
- **Story Points**: 3
- **Priority**: P1
- **Effort**: 2-3 hours
- **Description**: Update deployment documentation with test vs production deployment instructions, environment configuration, and troubleshooting guide
- **Acceptance Criteria**:
  - ✅ `docs/DEPLOYMENT_GUIDE.md` updated with test/prod sections
  - ✅ Quick start guide for test deployment
  - ✅ Production deployment checklist
  - ✅ Environment variable reference updated
  - ✅ Troubleshooting section for common issues
  - ✅ Architecture diagram showing test vs production

### Story 40.10: CI/CD Integration (Optional)
- **Story Points**: 5
- **Priority**: P2
- **Effort**: 4-5 hours
- **Description**: Integrate test deployment into CI/CD pipeline for automated testing, validation, and smoke tests
- **Acceptance Criteria**:
  - ✅ GitHub Actions workflow uses test deployment
  - ✅ Automated smoke tests run in test environment
  - ✅ Test deployment validates before merge
  - ✅ Production deployment validates before release
  - ✅ CI/CD documentation updated

## Dependencies

**Must Complete Before This Epic:**
- Epic 33-35: Synthetic External Data Generation (user specified this epic should be LAST)

**Prerequisites:**
- HA test container already implemented (Story 40.1 can leverage existing setup)
- Docker Compose patterns established in existing files
- Environment variable patterns established

**Blocks:**
- None (this epic enables better testing but doesn't block other work)

## NUC Resource Constraints & Context7 Best Practices

### Single Home NUC Deployment Context

**Hardware Profile (Per Context7 KB - Edge ML Deployment):**
- **Recommended**: Intel NUC i3/i5, 8-16GB RAM
- **Production Stack**: ~4-6GB RAM (all services)
- **InfluxDB**: 1-2GB per instance
- **Test Stack**: ~4.5-5.5GB RAM (with test containers)

**Resource Optimization Strategies (Per Context7 KB):**
1. **Memory Limits**: All services have explicit memory limits via Docker Compose `deploy.resources.limits.memory`
2. **CPU Limits**: CPU constraints prevent NUC overload during batch processing
3. **Docker Compose Profiles**: Use profiles for conditional service activation (test vs production)
4. **Volume Management**: Efficient storage with named volumes, bind mounts only where needed
5. **Network Isolation**: Separate networks but leverage Docker Compose service discovery

**Context7 Docker Compose Patterns:**
- **Resource Limits**: `deploy.resources.limits.memory` and `cpus` for all services
- **Health Checks**: Prevent resource leaks with proper health monitoring
- **Volume Management**: Use named volumes for persistence, tmpfs for temporary data
- **Service Discovery**: Docker Compose service names for internal communication

### Resource Usage Breakdown

**Test Deployment (Option A - Separate Bucket, 8GB NUC):**
```
InfluxDB (shared instance):     ~2GB
AI Services:                    ~1.5GB
Core Services:                  ~1GB
Test Containers:                ~500MB
Total:                          ~5GB (fits 8GB NUC ✅)
```

**Production Deployment (8GB NUC):**
```
InfluxDB:                       ~2GB
AI Services:                    ~1.5GB
Core Services:                  ~1.5GB
External API Services:          ~500MB
Total:                          ~5.5GB (fits 8GB NUC ✅)
```

**Both Running (16GB NUC only, not recommended):**
```
Test Stack:                     ~5GB
Production Stack:               ~5.5GB
Total:                          ~10.5GB (requires 16GB NUC ⚠️)
```

### Context7 Configuration Patterns

**Environment Variable Management (Per Context7 KB - Simple Config Pattern):**
- Use Pydantic BaseSettings for type-safe configuration
- Environment file per deployment mode (.env.test, .env.production)
- Simple file-based configuration (no database needed)
- Default values with override capability

**Docker Compose Resource Limits (Per Context7 KB):**
```yaml
services:
  influxdb:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
```

## Risk Assessment

**High Risk Areas:**
1. **NUC Memory Overload**: Running both test and production simultaneously
   - **Mitigation**: Mutually exclusive deployments, resource limits, clear documentation
   - **Context7**: Use Docker Compose resource limits and monitoring

2. **Database Configuration Complexity**: Separate buckets vs instances
   - **Mitigation**: Default to separate buckets (lighter), document instance option for 16GB NUC
   - **Context7**: Follow Docker volume management patterns

3. **Service Configuration Conflicts**: Services may have hardcoded assumptions
   - **Mitigation**: Comprehensive testing and validation scripts
   - **Context7**: Use environment variable detection patterns

**Medium Risk Areas:**
1. **Network Isolation**: Separate networks need proper service discovery
   - **Mitigation**: Use Docker Compose service names for internal communication
   - **Context7**: Follow Docker network configuration patterns

2. **Data Synchronization**: Test data may need to match production patterns
   - **Mitigation**: Synthetic data generators provide realistic test data
   - **Context7**: Follow synthetic data generation patterns from Epic 33-35

3. **Resource Limits**: Too restrictive limits may cause service failures
   - **Mitigation**: Start with conservative limits, monitor and adjust
   - **Context7**: Monitor actual usage and adjust limits based on NUC capabilities

## Testing Strategy

### Unit Tests
- Environment detection logic
- Configuration validation functions
- Service startup behavior based on DEPLOYMENT_MODE

### Integration Tests
- Test deployment full startup
- Production deployment validation
- Service isolation verification
- Database separation validation

### End-to-End Tests
- Complete test deployment workflow
- Complete production deployment workflow
- Service health checks in both environments
- Data isolation verification

## Implementation Notes

**Key Design Decisions:**
1. **InfluxDB Configuration (NUC-Optimized)**:
   - **Default (8GB NUC)**: Separate buckets in shared instance (~2GB memory)
   - **Optional (16GB NUC)**: Separate instances for version upgrade testing (~4GB memory)
   - Allows flexibility based on hardware constraints
2. **Mutually Exclusive Deployments**: Test and production cannot run simultaneously on 8GB NUC
3. **Resource Limits**: All services have memory/CPU constraints for NUC safety
4. **Environment Variable Based**: Simple detection without complex configuration files
5. **Explicit Blocks**: Production explicitly blocks data generation (fail-safe)
6. **Command-Based Deployment**: Simple commands (`deploy to test`, `deploy to prod`) for clarity
7. **Separate Networks**: Complete network isolation between test and production

**Patterns to Follow:**
- Use existing Docker Compose patterns from `docker-compose.dev.yml`
- Follow environment variable patterns from `infrastructure/env.example`
- Leverage existing HA test container configuration
- Use validation scripts similar to existing deployment scripts
- **Context7 KB**: Docker Compose resource limits, volume management, profile-based conditional services
- **NUC Constraints**: Resource limits, memory optimization, single-home deployment patterns

**NUC-Specific Considerations:**
- Memory limits on all services (prevents NUC overload)
- CPU limits for resource-constrained environments
- Docker Compose profiles for conditional service activation
- Volume management for efficient storage use
- Network isolation without excessive resource overhead

---

**Created:** January 25, 2025  
**Author:** BMAD Master  
**Status:** Planning  
**Priority:** High (Enables safe testing and production safeguards)

