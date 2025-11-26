# Home Assistant Test Container Plan

## Overview

Add an optional Home Assistant container to HomeIQ for testing dataset integration, pattern detection, and automation generation without affecting the production Home Assistant instance.

## Objectives

1. **Isolation**: Test against a dedicated Home Assistant instance
2. **Reproducibility**: Consistent test environment with known state
3. **Safety**: No risk to production Home Assistant
4. **Flexibility**: Easy to enable/disable for testing
5. **Dataset Integration**: Support synthetic home datasets for testing

## Architecture

### Current State
```
Production HA (192.168.1.86:8123) → websocket-ingestion → InfluxDB
```

### Proposed State
```
┌─────────────────────────────────────────────────────────────┐
│ Production Mode (Default)                                   │
│ Production HA (192.168.1.86:8123) → websocket-ingestion    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Test Mode (Optional)                                         │
│ HA Test Container → websocket-ingestion-test → InfluxDB     │
│   (localhost:8124)            (localhost:8002)              │
└─────────────────────────────────────────────────────────────┘
```

## Design Decisions

### 1. Container Strategy
- **Option A**: Full Home Assistant Core (Recommended)
  - Pros: Complete functionality, realistic testing
  - Cons: Larger image, slower startup
  - Image: `ghcr.io/home-assistant/home-assistant:stable`

- **Option B**: Home Assistant Supervised
  - Pros: More features, add-ons support
  - Cons: Complex setup, requires privileged mode
  - Not recommended for testing

- **Option C**: Minimal Home Assistant
  - Pros: Fast startup, minimal resources
  - Cons: Limited functionality
  - Not recommended

**Recommendation**: Option A - Full Home Assistant Core

### 2. Port Configuration
- **Test HA**: `8124` (avoid conflict with production `8123`)
- **Test WebSocket**: `8002` (separate from production `8001`)
- **Isolation**: Separate network or same network with different ports

### 3. Data Persistence
- **Config Directory**: `./data/ha-test/config/` (Docker volume)
- **Database**: SQLite in config directory
- **Add-ons**: Not needed for testing
- **Snapshots**: Optional, for test state management

### 4. Service Integration
- **websocket-ingestion-test**: Separate service instance for test HA
- **InfluxDB**: Shared bucket or separate test bucket
- **data-api**: Can query both production and test data

## Implementation Plan

### Phase 1: Container Setup (2-3 hours)

#### 1.1 Add Home Assistant Service
```yaml
home-assistant-test:
  image: ghcr.io/home-assistant/home-assistant:stable
  container_name: homeiq-ha-test
  restart: unless-stopped
  ports:
    - "8124:8123"  # Web UI
  volumes:
    - ha_test_config:/config
    - ha_test_data:/data
  environment:
    - TZ=America/Los_Angeles
  networks:
    - homeiq-network
  profiles:
    - test  # Only start with --profile test
```

#### 1.2 Create Test WebSocket Ingestion Service
```yaml
websocket-ingestion-test:
  build:
    context: .
    dockerfile: services/websocket-ingestion/Dockerfile
  container_name: homeiq-websocket-test
  restart: unless-stopped
  ports:
    - "8002:8001"
  environment:
    - HA_WS_URL=http://home-assistant-test:8123
    - HA_HTTP_URL=http://home-assistant-test:8123
    - HA_TOKEN=${HA_TEST_TOKEN}
    - INFLUXDB_BUCKET=home_assistant_events_test
  depends_on:
    - home-assistant-test
    - influxdb
  networks:
    - homeiq-network
  profiles:
    - test
```

#### 1.3 Docker Compose Profiles
- Use Docker Compose profiles to enable/disable test services
- Command: `docker-compose --profile test up -d`

### Phase 2: Configuration (1-2 hours)

#### 2.1 Home Assistant Configuration
- **Basic Setup**: Minimal configuration.yaml
- **Test Entities**: Use synthetic home datasets to create entities
- **Automations**: Load test automations from datasets
- **No External Integrations**: Keep it simple for testing

#### 2.2 Environment Variables
```bash
# .env.test
HA_TEST_URL=http://localhost:8124
HA_TEST_TOKEN=<generated_token>
HA_TEST_WS_URL=ws://localhost:8124/api/websocket
INFLUXDB_TEST_BUCKET=home_assistant_events_test
```

#### 2.3 Test Data Setup
- Script to load synthetic home configuration
- Create entities from dataset definitions
- Generate test events from datasets

### Phase 3: Dataset Integration (2-3 hours)

#### 3.1 Dataset Loader Integration
- Load synthetic home YAML into Home Assistant
- Create entities programmatically via API
- Set up areas and device relationships

#### 3.2 Event Generation
- Generate synthetic events from datasets
- Inject via Home Assistant API or direct state changes
- Verify events flow through websocket-ingestion-test

#### 3.3 Test Automation
- Script to set up test environment
- Load dataset → Create entities → Generate events → Run tests

### Phase 4: Testing Infrastructure (1-2 hours)

#### 4.1 Test Scripts
- `scripts/setup_ha_test.sh` - Initialize test HA
- `scripts/load_dataset_to_ha.py` - Load dataset entities
- `scripts/generate_test_events.py` - Create test events
- `scripts/teardown_ha_test.sh` - Clean up test environment

#### 4.2 Pytest Integration
- Fixtures for test HA connection
- Automatic setup/teardown
- Skip tests if test HA not available

#### 4.3 CI/CD Integration
- Optional test profile in CI
- Separate test pipeline
- Resource limits for test containers

## Configuration Details

### Docker Compose Service Definition

```yaml
services:
  home-assistant-test:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeiq-ha-test
    restart: unless-stopped
    ports:
      - "8124:8123"
    volumes:
      - ha_test_config:/config
      - ha_test_data:/data
    environment:
      - TZ=${TZ:-America/Los_Angeles}
    networks:
      - homeiq-network
    profiles:
      - test
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8123/api/"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  websocket-ingestion-test:
    build:
      context: .
      dockerfile: services/websocket-ingestion/Dockerfile
    container_name: homeiq-websocket-test
    restart: unless-stopped
    ports:
      - "8002:8001"
    env_file:
      - .env.test
    environment:
      - HA_WS_URL=http://home-assistant-test:8123/api/websocket
      - HA_HTTP_URL=http://home-assistant-test:8123
      - DATA_API_URL=http://data-api:8006
      - INFLUXDB_URL=http://influxdb:8086
      - INFLUXDB_BUCKET=home_assistant_events_test
      - LOG_LEVEL=DEBUG
    depends_on:
      home-assistant-test:
        condition: service_healthy
      influxdb:
        condition: service_healthy
      data-api:
        condition: service_healthy
    networks:
      - homeiq-network
    profiles:
      - test
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  ha_test_config:
    driver: local
  ha_test_data:
    driver: local
```

## Usage

### Starting Test Environment
```bash
# Start test containers
docker-compose --profile test up -d home-assistant-test websocket-ingestion-test

# Wait for HA to initialize (first time takes 2-3 minutes)
docker-compose logs -f home-assistant-test

# Setup test data
python scripts/setup_ha_test.py --dataset assist-mini

# Run tests
pytest tests/datasets/ -v
```

### Stopping Test Environment
```bash
# Stop test containers
docker-compose --profile test stop

# Clean up (optional)
docker-compose --profile test down -v
```

## Resource Requirements

### Memory
- Home Assistant: ~256-512MB
- WebSocket Ingestion Test: ~128MB
- **Total**: ~400-640MB additional

### Disk Space
- Home Assistant Config: ~100-500MB
- Test Data: ~50-200MB
- **Total**: ~150-700MB additional

### CPU
- Minimal during idle
- Spikes during test execution
- **Impact**: Low (test containers only run when needed)

## Benefits

1. **Isolation**: No risk to production system
2. **Reproducibility**: Consistent test environment
3. **Speed**: Faster than connecting to remote HA
4. **Control**: Full control over test data and state
5. **CI/CD**: Can run in automated pipelines
6. **Dataset Testing**: Perfect for synthetic home datasets

## Considerations

### Pros
- ✅ Complete isolation from production
- ✅ Reproducible test environment
- ✅ No network dependencies
- ✅ Can test destructive operations safely
- ✅ Supports dataset integration

### Cons
- ⚠️ Additional resource usage (memory/disk)
- ⚠️ Slower initial startup (first time)
- ⚠️ Requires maintenance (HA updates)
- ⚠️ May not match production exactly

### Alternatives Considered
1. **Mock Home Assistant**: Not realistic enough
2. **Remote Test Instance**: Network dependency, slower
3. **Docker-in-Docker**: Complex, resource intensive
4. **Separate VM**: Overkill for testing

## Security Considerations

1. **Network Isolation**: Test HA on separate network segment
2. **No External Access**: Test HA not exposed externally
3. **Token Management**: Separate test tokens
4. **Data Isolation**: Separate InfluxDB bucket
5. **Cleanup**: Automatic cleanup of test data

## Testing Strategy

### Unit Tests
- Test dataset loading
- Test event generation
- Test pattern detection (with mock data)

### Integration Tests
- Test HA connection
- Test event flow (HA → websocket → InfluxDB)
- Test pattern detection (with real HA events)

### End-to-End Tests
- Load dataset → Create entities → Generate events → Detect patterns → Validate results

## Implementation Timeline

- **Phase 1**: Container Setup (2-3 hours)
- **Phase 2**: Configuration (1-2 hours)
- **Phase 3**: Dataset Integration (2-3 hours)
- **Phase 4**: Testing Infrastructure (1-2 hours)
- **Total**: 6-10 hours

## Success Criteria

1. ✅ Test HA starts successfully
2. ✅ Can connect to test HA via API
3. ✅ Can create entities from datasets
4. ✅ Events flow through websocket-ingestion-test
5. ✅ Pattern detection works with test data
6. ✅ Tests can run independently of production
7. ✅ Easy to enable/disable test environment

## Next Steps

1. **Review this plan** - Get approval for approach
2. **Create test branch** - `feature/ha-test-container`
3. **Implement Phase 1** - Add containers to docker-compose.yml
4. **Test basic setup** - Verify containers start
5. **Implement Phase 2-4** - Complete integration
6. **Documentation** - Update README with test setup instructions

## Questions for Review

1. Should test HA be on a separate Docker network?
2. Should we use a separate InfluxDB bucket or database?
3. Do we need to support multiple test HA instances?
4. Should test HA persist data between runs?
5. What's the preferred way to load test data (API, YAML, scripts)?

---

**Status**: Draft for Review  
**Created**: 2025-11-24  
**Author**: AI Assistant  
**Review Required**: Architecture, Resource Usage, Implementation Approach

