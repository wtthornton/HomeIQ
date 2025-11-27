# Epic 40: Dual Deployment Configuration (Test & Production)

**Epic ID:** 40  
**Title:** Dual Deployment Configuration (Test & Production)  
**Status:** Planning  
**Priority:** High  
**Complexity:** Medium  
**Timeline:** 1-2 weeks  
**Story Points:** 15-20  
**Type:** Infrastructure & Deployment  
**Depends on:** Epic 33-35 (Synthetic External Data Generation) - Must be implemented LAST

---

## Epic Goal

Create simple test and production deployment separation using Docker Compose profiles with database separation. Test deployment uses only synthetic/mock data creation, disables external API feeds, but keeps all AI services operational. Production deployment explicitly blocks data generation services. Simplified approach optimized for single-home NUC deployment.

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

**Simplified Deployment Architecture (NUC-Optimized):**
1. **Test Deployment** (Docker Compose `test` profile):
   - Separate InfluxDB bucket in same instance (lighter, 8GB NUC-friendly)
   - Separate SQLite database
   - Same Docker network (simplified for single-home NUC)
   - HA test container integration (already exists with profile: test)
   - External API services disabled via `DEPLOYMENT_MODE=test` (weather, carbon, electricity, air-quality, calendar, smart-meter, sports-data)
   - OpenAI/AI services enabled (patterns, Ask AI, all downstream AI)
   - Synthetic data generators enabled
   - Mock data creation services enabled
   - Environment variable: `DEPLOYMENT_MODE=test`
   - Resource limits optimized for NUC (memory/CPU constraints)

2. **Production Deployment** (Default, no profile):
   - All external API services enabled
   - OpenAI/AI services enabled
   - Data generation services explicitly disabled/blocked
   - Production HA connection only
   - Environment variable: `DEPLOYMENT_MODE=production`
   - Simple validation to prevent test services from starting

**Important: NUC Resource Constraints:**
- **Test and Production are MUTUALLY EXCLUSIVE** - cannot run both simultaneously on 8GB NUC
- **Resource-efficient**: Separate bucket approach (single InfluxDB instance, different buckets)

**Deployment Commands:**
- `docker-compose --profile test up -d` - Start test environment
- `docker-compose down` - Stop current deployment
- `docker-compose up -d` - Start production environment (default)
- Services automatically read `DEPLOYMENT_MODE` environment variable

### Existing System Context

**Current Deployment Files:**
- `docker-compose.yml` - Main file (all services, supports profiles)
- `docker-compose.dev.yml` - Development with ha-simulator
- `docker-compose.prod.yml` - Production overrides (existing)
- `docker-compose.minimal.yml` - Minimal services
- Test profile already exists for HA test container and websocket-ingestion-test

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
- **Safe Testing**: Separate buckets enable safe testing without production risk
- **Production Safety**: Explicit blocks prevent accidental data generation in production
- **Development Velocity**: Faster iteration with synthetic data vs waiting for real APIs
- **Reproducibility**: Test environment is consistent and reproducible
- **Development Velocity**: Faster iteration with isolated test environment

## Success Criteria

- ✅ Test deployment isolated from production using separate buckets/databases
- ✅ Separate InfluxDB bucket (`home_assistant_events_test`) for test environment
- ✅ Separate SQLite databases for metadata
- ✅ External API services disabled in test mode (saves ~500MB memory)
- ✅ AI services operational in both environments
- ✅ Production deployment blocks data generation services
- ✅ Simple deployment commands using Docker Compose profiles
- ✅ Environment detection via `DEPLOYMENT_MODE` variable
- ✅ HA test container integrated into test deployment (existing profile)
- ✅ Resource limits configured for NUC constraints (memory/CPU)
- ✅ Basic documentation for deployment usage
- ✅ Simple validation to prevent misconfiguration
- ✅ Mutually exclusive deployment pattern documented

## Technical Architecture

### Single Home NUC Deployment Context

**Hardware Constraints (Per Context7 KB):**
- **Recommended**: Intel NUC i3/i5, 8-16GB RAM
- **Production Stack**: ~4-6GB RAM (all services)
- **InfluxDB Memory**: 1-2GB per instance
- **Constraint**: Running both test and production simultaneously would require ~8GB+ RAM

**Design Decision:**
- **Separate buckets in same InfluxDB instance** (lightweight, ~2GB total, NUC-optimized)
- **Mutually Exclusive**: Test and production deployments should not run simultaneously on NUC
- **Resource Limits**: All services have memory/CPU limits to prevent NUC overload
- **Simple Approach**: Use Docker Compose profiles instead of separate compose files

### Deployment Architecture

**Test Deployment (DEPLOYMENT_MODE=test):**
```
┌─────────────────────────────────────────────────────────────┐
│ Test Deployment - NUC Optimized (Docker Compose --profile test) │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Shared InfluxDB Instance (Port 8086)                        │
│   - Bucket: home_assistant_events_test (separate bucket)    │
│   - Memory: ~2GB (shared instance)                          │
│   - Lightweight, NUC-friendly                               │
│                                                             │
│ SQLite Test Database                                        │
│   - Location: ./data/test/metadata.db                       │
│   - Memory: <50MB                                           │
│                                                             │
│ HA Test Container (Port 8124) - Profile: test              │
│   └─> websocket-ingestion-test (Port 8002) - Profile: test │
│       └─> InfluxDB Test Bucket                              │
│                                                             │
│ External API Services: DISABLED ❌                          │
│   - Saves ~500MB memory (disabled via DEPLOYMENT_MODE)      │
│                                                             │
│ AI Services: ENABLED ✅                                     │
│   - Memory: ~1-2GB (same as production)                    │
│                                                             │
│ Data Generation: ENABLED ✅                                 │
│   - Memory: ~200-500MB (synthetic generators)              │
│                                                             │
│ Network: homeiq-network (shared with production)            │
│ Resource Limits: Memory <6GB, CPU <4 cores                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Production Deployment (DEPLOYMENT_MODE=production):
┌─────────────────────────────────────────────────────────────┐
│ Production Deployment - NUC Optimized (Default, no profile) │
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
│   - Simple validation prevents data generation services      │
│                                                             │
│ Network: homeiq-network                                     │
│ Resource Limits: Memory <6GB, CPU <4 cores                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

⚠️ IMPORTANT: Test and Production are MUTUALLY EXCLUSIVE on NUC
   - Switch between deployments: `docker-compose down` then `docker-compose --profile test up`
   - Cannot run both simultaneously on 8GB NUC
```

### Resource Usage Breakdown (Single Home NUC)

**Test Deployment (Separate Bucket):**
- InfluxDB: ~2GB (shared instance, test bucket)
- Services: ~2-3GB (AI services, websocket, etc.)
- Test containers: ~500MB (HA test, test ingestion)
- **Total**: ~4.5-5.5GB (fits 8GB NUC ✅)

**Production Deployment:**
- InfluxDB: ~2GB
- Services: ~3-4GB (all services including external APIs)
- **Total**: ~5-6GB (fits 8GB NUC ✅)

**Note:** Test and production are mutually exclusive - cannot run both simultaneously on 8GB NUC

### File Structure

```
docker-compose.yml              # Main file (supports profiles: test, dev, etc.)
docker-compose.prod.yml         # Production overrides (existing)
docker-compose.dev.yml          # Development (existing, unchanged)

infrastructure/
  env.example                   # Template (updated with DEPLOYMENT_MODE)
  env.production                # Production environment
  env.test                      # NEW: Test environment template

data/
  metadata.db                   # Production SQLite
  test/
    metadata.db                 # NEW: Test SQLite database
```

**Deployment Approach:**
- Use Docker Compose profiles: `docker-compose --profile test up -d` for test mode
- Production: `docker-compose up -d` (default, no profile needed)
- Services read `DEPLOYMENT_MODE` environment variable from `.env` file

### Environment Variables

**Test Environment (`env.test`):**
```bash
DEPLOYMENT_MODE=test

# InfluxDB Test Configuration (Separate Bucket in Shared Instance)
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_ORG=homeiq-test
INFLUXDB_BUCKET=home_assistant_events_test
INFLUXDB_TOKEN=homeiq-test-token

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

### Story 40.1: Test Deployment Using Docker Compose Profiles
- **Story Points**: 5
- **Priority**: P0
- **Effort**: 4-5 hours
- **Description**: Configure test deployment using Docker Compose profiles (leveraging existing `test` profile for HA container). Add profile support for test services, configure separate InfluxDB bucket, and integrate with existing test HA container setup.
- **Acceptance Criteria**:
  - ✅ Test services configured with `profiles: ["test"]` in docker-compose.yml
  - ✅ Separate InfluxDB bucket (`home_assistant_events_test`) configured for test
  - ✅ HA test container (existing) and websocket-ingestion-test (existing) integrated
  - ✅ External API services excluded or disabled when DEPLOYMENT_MODE=test
  - ✅ AI services included and configured
  - ✅ Environment variable `DEPLOYMENT_MODE=test` set for test profile
  - ✅ Test can be started with `docker-compose --profile test up -d`

### Story 40.2: Production Deployment Safeguards
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Enhance production deployment with explicit blocks for data generation services and simple validation to prevent test services from starting in production
- **Acceptance Criteria**:
  - ✅ Production compose file explicitly excludes data generation services
  - ✅ Simple validation prevents data generation services in production mode
  - ✅ Environment variable `DEPLOYMENT_MODE=production` validated on startup
  - ✅ Clear error messages if misconfiguration detected
  - ✅ Production deployment blocks test profile services
  - ✅ Basic documentation of production safeguards

### Story 40.3: InfluxDB Test Bucket Configuration
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 2-3 hours
- **Description**: Configure InfluxDB test bucket in shared instance for test environment. Separate bucket provides isolation without separate instance overhead.
- **Acceptance Criteria**:
  - ✅ Test bucket (`home_assistant_events_test`) in shared InfluxDB instance
  - ✅ Separate initialization with test org/bucket/token
  - ✅ Test services connect to test InfluxDB bucket
  - ✅ Production services never connect to test bucket
  - ✅ Resource limits configured for NUC constraints
  - ✅ Documentation explains bucket separation approach

### Story 40.4: Test Environment Configuration Files
- **Story Points**: 2
- **Priority**: P0
- **Effort**: 1-2 hours
- **Description**: Create `infrastructure/env.test` template file with all test environment variables configured (disabled external APIs, enabled AI services, test database paths)
- **Acceptance Criteria**:
  - ✅ `infrastructure/env.test` template created
  - ✅ All external API services disabled via environment variables
  - ✅ AI services enabled and configured
  - ✅ Test database paths configured
  - ✅ Test HA container connection configured

### Story 40.5: Service Environment Detection
- **Story Points**: 3
- **Priority**: P0
- **Effort**: 3-4 hours
- **Description**: Add environment detection logic to services to automatically configure behavior based on `DEPLOYMENT_MODE` environment variable (disable external APIs in test, block data generation in production)
- **Acceptance Criteria**:
  - ✅ Services read `DEPLOYMENT_MODE` environment variable
  - ✅ External API services skip initialization in test mode
  - ✅ Data generation services block startup in production mode
  - ✅ AI services work in both modes
  - ✅ Logging shows deployment mode on startup
  - ✅ Health checks reflect deployment mode

### Story 40.6: Basic Documentation
- **Story Points**: 2
- **Priority**: P1
- **Effort**: 1-2 hours
- **Description**: Create basic documentation for test vs production deployment usage, environment configuration, and simple deployment commands
- **Acceptance Criteria**:
  - ✅ Basic deployment guide with test/prod commands
  - ✅ Environment variable reference
  - ✅ Simple troubleshooting notes
  - ✅ Deployment command examples

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

2. **Service Configuration Conflicts**: Services may have hardcoded assumptions
   - **Mitigation**: Environment variable detection, simple validation checks
   - **Context7**: Use environment variable detection patterns

**Medium Risk Areas:**
1. **Data Synchronization**: Test data may need to match production patterns
   - **Mitigation**: Synthetic data generators provide realistic test data
   - **Context7**: Follow synthetic data generation patterns from Epic 33-35

2. **Resource Limits**: Too restrictive limits may cause service failures
   - **Mitigation**: Start with conservative limits, monitor and adjust
   - **Context7**: Monitor actual usage and adjust limits based on NUC capabilities

3. **Profile Configuration**: Ensuring profiles work correctly with existing services
   - **Mitigation**: Test profile activation, validate service isolation
   - **Context7**: Follow Docker Compose profile patterns

## Testing Strategy

### Unit Tests
- Environment detection logic
- Configuration validation functions
- Service startup behavior based on DEPLOYMENT_MODE

### Integration Tests
- Basic smoke tests for test deployment startup
- Basic smoke tests for production deployment
- Service isolation verification
- Database separation validation

## Implementation Notes

**Key Design Decisions:**
1. **InfluxDB Configuration (NUC-Optimized)**: Separate buckets in shared instance (~2GB memory) - simple and efficient
2. **Mutually Exclusive Deployments**: Test and production cannot run simultaneously on 8GB NUC
3. **Resource Limits**: All services have memory/CPU constraints for NUC safety
4. **Environment Variable Based**: Simple detection without complex configuration files
5. **Explicit Blocks**: Production explicitly blocks data generation (fail-safe)
6. **Docker Compose Profiles**: Use profiles instead of separate compose files for simplicity
7. **Shared Network**: Same Docker network for both test and production (simplified for single-home NUC)

**Patterns to Follow:**
- Use existing Docker Compose patterns and profiles from `docker-compose.yml`
- Follow environment variable patterns from `infrastructure/env.example`
- Leverage existing HA test container configuration (already has `profile: test`)
- **Context7 KB**: Docker Compose resource limits, volume management, profile-based conditional services
- **NUC Constraints**: Resource limits, memory optimization, single-home deployment patterns

**NUC-Specific Considerations:**
- Memory limits on all services (prevents NUC overload)
- CPU limits for resource-constrained environments
- Docker Compose profiles for conditional service activation (simpler than separate files)
- Volume management for efficient storage use
- Shared network approach (single-home deployment doesn't need network isolation)

---

**Created:** January 25, 2025  
**Author:** BMAD Master  
**Status:** Planning  
**Priority:** High (Enables safe testing and production safeguards)

