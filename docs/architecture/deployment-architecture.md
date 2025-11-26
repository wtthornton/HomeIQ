# Deployment Architecture

**Last Updated:** January 2025  
**Target Platform:** Home Assistant single-home deployment on NUC (Next Unit of Computing)  
**Context7 Patterns:** Integrated throughout

## Deployment Strategy

**Frontend Deployment:**
- **Platform:** Docker container with nginx (Alpine-based)
- **Build Command:** `npm run build` (multi-stage build)
- **Output Directory:** `dist/`
- **CDN/Edge:** Local nginx serving static files
- **Image Size:** ~80MB (optimized from ~300MB)

**Backend Deployment:**
- **Platform:** Docker containers orchestrated by Docker Compose
- **Build Command:** Docker multi-stage builds with Alpine Linux
- **Deployment Method:** Docker Compose with health checks and restart policies
- **Security:** Non-root users, read-only filesystems, security options
- **Optimization:** 71% size reduction with Alpine-based images

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      influxdb:
        image: influxdb:2.7
        ports:
          - 8086:8086

    steps:
    - uses: actions/checkout@v4
    - name: Run tests
      run: |
        docker-compose -f docker-compose.yml build
        docker-compose -f docker-compose.yml up -d
        sleep 30
        docker-compose -f docker-compose.yml run --rm test-integration
        docker-compose -f docker-compose.yml down
```

### Environments

| Environment | Frontend URL | Backend URL | Purpose | Docker Compose File |
|-------------|--------------|-------------|---------|-------------------|
| Development | http://localhost:3000 | http://localhost:8000 | Local development | docker-compose.dev.yml |
| Production | http://localhost:3000 | http://localhost:8003 | Live environment | docker-compose.prod.yml |

### Docker Image Optimizations

| Service | Before | After | Reduction |
|---------|--------|-------|-----------|
| WebSocket Ingestion | ~200MB | ~60MB | 70% |
| Admin API | ~180MB | ~50MB | 72% |
| ~~Enrichment Pipeline~~ | ~~~220MB~~ | **REMOVED** | **100%** |
| Weather API | ~150MB | ~40MB | 73% |
| Data Retention | ~200MB | ~60MB | 70% |
| Health Dashboard | ~300MB | ~80MB | 73% |
| **Total** | **~1.25GB** | **~290MB** | **77%** |

**Note:** Enrichment Pipeline removed October 2025 - external services now consume directly from InfluxDB

### Security Enhancements
- **Non-root users:** All services run as uid=1001, gid=1001
- **Read-only filesystems:** Where applicable for enhanced security
- **Security options:** `no-new-privileges:true` for all services
- **Tmpfs mounts:** For temporary files and caches
- **Multi-stage builds:** Eliminate build tools from production images

### Persistent Storage (Epic 22)

**Docker Volumes:**
```yaml
volumes:
  influxdb_data:         # InfluxDB time-series data
  influxdb_config:       # InfluxDB configuration
  sqlite-data:           # SQLite metadata databases (Epic 22)
  data_retention_backups:# Retention service backups
  ha_ingestor_logs:      # Centralized logs
```

**Hybrid Database Architecture:**
- **InfluxDB** (`influxdb_data` volume):
  - Home Assistant events (time-series)
  - Sports scores and game data
  - System metrics
  - **External services consume from InfluxDB** (weather, energy, etc.)
  
- **SQLite** (`sqlite-data` volume):
  - `metadata.db` (data-api) - Devices and entities registry
  - `webhooks.db` (sports-data) - Webhook subscriptions
  - WAL mode enabled for concurrent access
  - File-based backups (simple `cp` command)

**Architecture Change (October 2025):**
- Enrichment Pipeline removed - external services now consume directly from InfluxDB
- Clean microservices pattern with InfluxDB as data hub
- Weather data provided by external weather-api service (Port 8009)

**Backup Strategy:**
```bash
# InfluxDB backup
docker exec homeiq-data-api influx backup /backup/

# SQLite backup (simple file copy - safe with WAL mode)
docker cp homeiq-data-api:/app/data/metadata.db ./backups/sqlite/
docker cp homeiq-sports-data:/app/data/webhooks.db ./backups/sqlite/
```

## NUC Deployment Considerations

### Hardware Requirements

**Minimum NUC Specifications:**
- **CPU:** Intel NUC with 2-4 cores (e.g., NUC8i3, NUC10i3)
- **Memory:** 8GB RAM minimum, 16GB recommended
- **Storage:** 128GB SSD minimum, 256GB+ recommended
- **Network:** Gigabit Ethernet (WiFi optional)

**Resource Allocation:**
- **HomeIQ Services:** 1GB RAM maximum
- **Home Assistant:** 512MB-1GB RAM (reserve)
- **OS & System:** 512MB-1GB RAM (reserve)
- **Total:** 2-4GB RAM for HomeIQ + Home Assistant

### NUC-Optimized Resource Limits

**Service Memory Limits (docker-compose.yml):**
```yaml
services:
  websocket-ingestion:
    deploy:
      resources:
        limits:
          memory: 256M  # Reduced from 512MB for NUC
          cpus: '0.5'   # Limit CPU usage
  
  data-api:
    deploy:
      resources:
        limits:
          memory: 128M  # Reduced from 256MB for NUC
          cpus: '0.3'
  
  admin-api:
    deploy:
      resources:
        limits:
          memory: 128M  # Reduced from 256MB for NUC
          cpus: '0.3'
  
  health-dashboard:
    deploy:
      resources:
        limits:
          memory: 64M   # Reduced from 128MB for NUC
          cpus: '0.2'
  
  influxdb:
    deploy:
      resources:
        limits:
          memory: 256M  # Reduced from 400MB for NUC
          cpus: '0.5'
```

**SQLite Configuration (NUC-Optimized):**
```python
# Connection Pragmas (NUC-optimized)
PRAGMA journal_mode=WAL          # Writers don't block readers
PRAGMA synchronous=NORMAL        # Fast writes, survives OS crash
PRAGMA cache_size=-32000         # 32MB cache (vs 64MB for larger systems)
PRAGMA temp_store=MEMORY         # Fast temp tables
PRAGMA foreign_keys=ON           # Referential integrity
PRAGMA busy_timeout=30000        # 30s lock wait
```

**InfluxDB Configuration (NUC-Optimized):**
```python
# Batch Writer (NUC-optimized)
batch_size = 500          # Smaller batches (vs 1000)
batch_timeout = 3.0      # Faster flush (vs 5.0)
max_retries = 3          # Retry on network errors
```

### Single-Home Event Volume

**Typical Event Rates:**
- **Normal:** 50-200 events/sec
- **Peak:** 400-500 events/sec (device discovery, bulk updates)
- **Sustained:** 150 events/sec average

**Batch Processing (NUC-Optimized):**
- **Batch Size:** 50-100 events (vs 100-200 for multi-home)
- **Batch Timeout:** 3-5 seconds (faster response for single user)
- **WebSocket Connections:** 1 (single Home Assistant instance)

### Storage Considerations

**Disk Space Requirements (Single-Home):**
- **InfluxDB:** ~10-50GB per year (depends on event volume)
- **SQLite:** <100MB (metadata databases)
- **Docker Images:** ~500MB (Alpine-based)
- **Logs:** ~1-5GB (with rotation)
- **Total:** 20-60GB for first year

**Retention Policies (NUC-Optimized):**
- **InfluxDB:** 1-2 years retention (vs 3+ years for larger systems)
- **SQLite:** No retention needed (small size)
- **Logs:** 30 days rotation (3 files × 10MB)

### Network Configuration

**Port Allocation:**
- **Home Assistant:** 8123 (default)
- **WebSocket Ingestion:** 8001
- **Data API:** 8006
- **Admin API:** 8004
- **Health Dashboard:** 3000
- **InfluxDB:** 8086

**Single-Home Network:**
- **Local Network:** 192.168.x.x (typical)
- **No External Access Required:** All services local
- **Bandwidth:** Minimal (single user, local network)

### Performance Tuning for NUC

**CPU Optimization:**
- **Service Limits:** <30% CPU per service (normal), <60% (peak)
- **Total System:** <80% CPU (reserve for Home Assistant)
- **Background Tasks:** <15% CPU

**Memory Optimization:**
- **Service Limits:** 128MB-256MB per service
- **Total Services:** <1GB (reserve 512MB+ for Home Assistant)
- **Cache Sizes:** Reduced (SQLite 32MB, InfluxDB 256MB)

**I/O Optimization:**
- **SSD Recommended:** Faster SQLite and InfluxDB performance
- **WAL Mode:** SQLite WAL for concurrent access
- **Batch Writes:** InfluxDB batch writer (500 events)

### Deployment Checklist for NUC

- [ ] **Hardware:** Verify NUC meets minimum specs (8GB RAM, SSD)
- [ ] **Resource Limits:** Configure docker-compose.yml with NUC limits
- [ ] **SQLite Cache:** Set to 32MB (PRAGMA cache_size=-32000)
- [ ] **InfluxDB Memory:** Limit to 256MB
- [ ] **Batch Sizes:** Configure 50-100 events per batch
- [ ] **Retention Policies:** Set 1-2 year retention
- [ ] **Health Checks:** Verify all services have health endpoints
- [ ] **Monitoring:** Enable resource monitoring (CPU, memory, disk)
- [ ] **Backup Strategy:** Configure automated backups
- [ ] **Log Rotation:** Enable log rotation (10MB files, 3 max)

### Troubleshooting NUC Deployment

**High CPU Usage:**
- Check for blocking operations in async code
- Verify batch sizes are appropriate (50-100 events)
- Monitor service CPU limits

**High Memory Usage:**
- Verify service memory limits are set correctly
- Check SQLite cache size (should be 32MB)
- Review InfluxDB memory usage (should be <256MB)

**Slow Performance:**
- Verify SSD is being used (not HDD)
- Check SQLite WAL mode is enabled
- Review batch processing configuration
- Monitor disk I/O usage

**Service Failures:**
- Check resource limits (may be too restrictive)
- Verify health check endpoints are responding
- Review logs for correlation IDs and errors
- Check Home Assistant connection status

