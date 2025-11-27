# Epic 40: Dual Deployment Configuration Guide

**Epic ID:** 40  
**Status:** ✅ Complete  
**Created:** January 2025

---

## Overview

Epic 40 implements dual deployment configuration for test and production environments using Docker Compose profiles. This enables safe testing without affecting production data or consuming external API quotas.

### Key Features

- ✅ **Test Deployment**: Separate InfluxDB bucket and SQLite database
- ✅ **Production Safeguards**: Blocks data generation services in production
- ✅ **Resource Optimization**: External API services disabled in test mode
- ✅ **Simple Commands**: Easy switching between test and production
- ✅ **NUC-Optimized**: Designed for single-home 8GB NUC deployment

---

## Quick Start

### Test Deployment

```bash
# 1. Copy test environment file
cp infrastructure/env.test .env

# 2. Update .env with your test configuration (HA_TEST_TOKEN, etc.)

# 3. Setup test environment (creates directories and InfluxDB bucket)
bash scripts/setup_test_environment.sh

# 4. Start test deployment
docker-compose --profile test up -d
```

### Production Deployment

```bash
# 1. Copy production environment file (or use existing .env)
cp infrastructure/env.production .env

# 2. Update .env with your production configuration

# 3. Start production deployment (default, no profile)
docker-compose up -d
```

### Switching Between Deployments

```bash
# Stop current deployment
docker-compose down

# Start test deployment
docker-compose --profile test up -d

# OR start production deployment
docker-compose up -d
```

**⚠️ Important:** Test and production deployments are **mutually exclusive** on 8GB NUC. Do not run both simultaneously.

---

## Architecture

### Test Deployment

```
┌─────────────────────────────────────────────────────────────┐
│ Test Deployment (docker-compose --profile test)             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ InfluxDB (Shared Instance)                                  │
│   - Bucket: home_assistant_events_test                      │
│   - Org: homeiq-test                                        │
│                                                             │
│ SQLite Test Database                                        │
│   - Location: ./data/test/metadata.db                      │
│                                                             │
│ HA Test Container (Port 8124)                               │
│   └─> websocket-ingestion-test (Port 8002)                  │
│                                                             │
│ External API Services: DISABLED ❌                          │
│   - weather-api, carbon-intensity, electricity-pricing      │
│   - air-quality, smart-meter, sports-data                   │
│                                                             │
│ AI Services: ENABLED ✅                                     │
│   - ai-automation-service, openai-service                   │
│   - device-intelligence-service, automation-miner           │
│                                                             │
│ Data Generation: ENABLED ✅                                 │
│   - Synthetic data generators (Epic 33-35)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Production Deployment

```
┌─────────────────────────────────────────────────────────────┐
│ Production Deployment (docker-compose up -d)                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ InfluxDB Production Instance                                │
│   - Bucket: home_assistant_events                           │
│   - Org: homeiq                                             │
│                                                             │
│ SQLite Production Database                                  │
│   - Location: ./data/metadata.db                            │
│                                                             │
│ Production HA (192.168.1.86:8123)                          │
│   └─> websocket-ingestion (Port 8001)                      │
│                                                             │
│ External API Services: ENABLED ✅                           │
│   - weather-api, carbon-intensity, electricity-pricing     │
│   - air-quality, smart-meter, sports-data                   │
│                                                             │
│ AI Services: ENABLED ✅                                     │
│   - ai-automation-service, openai-service                  │
│   - device-intelligence-service, automation-miner          │
│                                                             │
│ Data Generation: BLOCKED ❌                                 │
│   - Validation prevents data generation services            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Environment Variables

### Test Environment (`infrastructure/env.test`)

```bash
# Deployment Mode
DEPLOYMENT_MODE=test

# InfluxDB Test Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_ORG=homeiq-test
INFLUXDB_BUCKET=home_assistant_events_test
INFLUXDB_TOKEN=homeiq-test-token

# SQLite Test Database
DATABASE_URL=sqlite+aiosqlite:///./data/test/metadata.db

# External API Services - DISABLED
ENABLE_WEATHER_API=false
ENABLE_CARBON_INTENSITY=false
ENABLE_ELECTRICITY_PRICING=false
ENABLE_AIR_QUALITY=false
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

### Production Environment (`infrastructure/env.production`)

```bash
# Deployment Mode
DEPLOYMENT_MODE=production

# InfluxDB Production Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events
INFLUXDB_TOKEN=${INFLUXDB_TOKEN}

# SQLite Production Database
DATABASE_URL=sqlite+aiosqlite:///./data/metadata.db

# External API Services - ENABLED
ENABLE_WEATHER_API=true
ENABLE_CARBON_INTENSITY=true
ENABLE_ELECTRICITY_PRICING=true
ENABLE_AIR_QUALITY=true
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

---

## Docker Compose Profiles

### Test Profile Services

Services with `profiles: ["test"]`:
- `home-assistant-test` - Test HA container (Port 8124)
- `websocket-ingestion-test` - Test ingestion service (Port 8002)

### Production Profile Services

Services with `profiles: ["production"]`:
- `weather-api` - Weather data service
- `carbon-intensity` - Carbon intensity service
- `electricity-pricing` - Electricity pricing service
- `air-quality` - Air quality service
- `smart-meter` - Smart meter service

**Note:** Services without profiles run in both test and production modes.

---

## Service Environment Detection

Services can detect deployment mode using the `DEPLOYMENT_MODE` environment variable:

```python
from shared.deployment_validation import (
    get_deployment_mode,
    log_deployment_info,
    check_data_generation_allowed,
    check_test_service_allowed,
)

# Log deployment info on startup
log_deployment_info("my-service")

# Check if data generation is allowed (only in test mode)
check_data_generation_allowed("my-service")  # Exits if production

# Check if test service is allowed (only in test mode)
check_test_service_allowed("my-service")  # Exits if production
```

### Example: Adding Validation to a Service

```python
# In service main.py
from shared.deployment_validation import (
    log_deployment_info,
    check_data_generation_allowed,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log deployment mode
    log_deployment_info("my-data-generation-service")
    
    # Validate deployment mode (exits if production)
    check_data_generation_allowed("my-data-generation-service")
    
    # Service initialization...
    yield
    
    # Shutdown...
```

---

## InfluxDB Test Bucket

The test environment uses a separate bucket in the same InfluxDB instance:

- **Test Bucket**: `home_assistant_events_test`
- **Test Org**: `homeiq-test`
- **Test Token**: `homeiq-test-token`
- **Retention**: 7 days (vs 30 days for production)

### Initialization

The test bucket is automatically created by:
1. `scripts/setup_test_environment.sh` (manual setup)
2. `infrastructure/influxdb/init-influxdb.sh` (automatic on InfluxDB startup)

---

## Resource Usage

### Test Deployment (8GB NUC)

```
InfluxDB (shared instance):     ~2GB
AI Services:                    ~1.5GB
Core Services:                  ~1GB
Test Containers:                ~500MB
Total:                          ~5GB ✅
```

### Production Deployment (8GB NUC)

```
InfluxDB:                       ~2GB
AI Services:                    ~1.5GB
Core Services:                  ~1.5GB
External API Services:          ~500MB
Total:                          ~5.5GB ✅
```

**Note:** Both deployments fit comfortably on 8GB NUC, but cannot run simultaneously.

---

## Troubleshooting

### Test Services Not Starting

**Issue:** Test services don't start with `docker-compose --profile test up -d`

**Solution:**
1. Verify profile is set: `docker-compose --profile test config | grep -A 5 "home-assistant-test"`
2. Check environment file: Ensure `.env` has `DEPLOYMENT_MODE=test`
3. Verify test bucket exists: `influx bucket list --org homeiq-test`

### Production Services Blocked

**Issue:** Data generation service exits with "cannot run in production mode"

**Solution:**
- This is expected behavior. Data generation services are blocked in production for safety.
- Use test deployment for data generation testing.

### InfluxDB Test Bucket Not Found

**Issue:** Services can't connect to test bucket

**Solution:**
1. Run setup script: `bash scripts/setup_test_environment.sh`
2. Or manually create bucket:
   ```bash
   influx org create --name homeiq-test --token homeiq-test-token
   influx bucket create --name home_assistant_events_test --org homeiq-test --retention 7d
   ```

### Both Deployments Running Simultaneously

**Issue:** Both test and production services are running

**Solution:**
- Stop one deployment: `docker-compose down`
- They are mutually exclusive on 8GB NUC by design

---

## Validation and Safeguards

### Production Safeguards

1. **Data Generation Blocking**: Services that generate synthetic data exit if `DEPLOYMENT_MODE=production`
2. **Test Service Blocking**: Test-only services exit if `DEPLOYMENT_MODE=production`
3. **Profile Isolation**: External API services excluded from test profile

### Validation Functions

- `check_data_generation_allowed()` - Validates data generation services (test only)
- `check_test_service_allowed()` - Validates test services (test only)
- `validate_deployment_mode()` - Generic validation function

---

## Best Practices

1. **Always use profiles**: Use `--profile test` for test, no profile for production
2. **Environment files**: Use `infrastructure/env.test` and `infrastructure/env.production` as templates
3. **Separate databases**: Never mix test and production data
4. **Resource limits**: Monitor memory usage on NUC (both deployments ~5GB)
5. **Validation**: Add deployment validation to new services that generate data

---

## Related Documentation

- **Epic 40 PRD**: `docs/prd/epic-40-dual-deployment-configuration.md`
- **Docker Compose Reference**: `docker-compose.yml`
- **Environment Templates**: `infrastructure/env.test`, `infrastructure/env.production`
- **Setup Script**: `scripts/setup_test_environment.sh`

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review Epic 40 PRD for architecture details
3. Check service logs: `docker-compose logs <service-name>`

---

**Last Updated:** January 2025  
**Epic Status:** ✅ Complete

