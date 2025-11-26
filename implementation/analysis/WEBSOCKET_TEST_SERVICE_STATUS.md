# WebSocket Test Service Status

**Date:** November 25, 2025  
**Service:** `websocket-ingestion-test` (container: `homeiq-websocket-test`)

---

## Service Overview

**Purpose:**
- Optional test service for WebSocket ingestion
- Connects to test Home Assistant instance (`home-assistant-test`)
- Uses separate InfluxDB bucket (`home_assistant_events_test`)
- Runs on port 8002 (vs production on 8001)

**Profile:** `test` (not started by default)

---

## Configuration

### Docker Compose
- **Service Name:** `websocket-ingestion-test`
- **Container Name:** `homeiq-websocket-test`
- **Profile:** `test` (requires `--profile test` to start)
- **Port:** `8002:8001` (external:internal)

### Environment
- **HA Test URL:** `http://home-assistant-test:8123`
- **InfluxDB Bucket:** `home_assistant_events_test` (separate from production)
- **Port:** 8001 (internal)

---

## Current Status

### Expected Behavior
- **Not Running by Default:** Service uses `test` profile
- **Only Starts When:** `docker-compose --profile test up` is used
- **Purpose:** Testing without affecting production

### If Container Shows in Dashboard
- May be stopped/created but not running
- Or may be running if test profile was activated
- Check actual status with: `docker ps -a --filter "name=websocket-test"`

---

## Usage

### Start Test Services
```bash
# Start test profile services
docker-compose --profile test up -d websocket-ingestion-test home-assistant-test

# Check status
docker-compose --profile test ps
```

### Stop Test Services
```bash
# Stop test services
docker-compose --profile test stop

# Remove test containers
docker-compose --profile test down
```

---

## Why It Might Show 0% Memory

1. **Container Created but Not Running:**
   - Container exists but is stopped
   - Shows in dashboard but not active

2. **Test Profile Not Active:**
   - Service requires `--profile test` to start
   - Won't run with normal `docker-compose up`

3. **Minimal Resource Usage:**
   - If running but idle, uses minimal memory
   - Test services are lightweight

---

## Recommendations

### If You Want to Use It
1. Start with test profile:
   ```bash
   docker-compose --profile test up -d websocket-ingestion-test
   ```

2. Verify it's running:
   ```bash
   docker-compose --profile test ps websocket-ingestion-test
   ```

### If You Don't Need It
1. **Leave it stopped** (default behavior)
2. **Remove container** if it exists:
   ```bash
   docker rm homeiq-websocket-test
   ```

---

## Production vs Test

| Aspect | Production | Test |
|--------|-----------|------|
| Service | `websocket-ingestion` | `websocket-ingestion-test` |
| Container | `homeiq-websocket` | `homeiq-websocket-test` |
| Port | 8001 | 8002 |
| HA Instance | Production (192.168.1.86:8123) | Test container |
| InfluxDB Bucket | `home_assistant_events` | `home_assistant_events_test` |
| Profile | default | test |

---

**Status:** ✅ **Service is Optional Test Service - Not Required for Production**

