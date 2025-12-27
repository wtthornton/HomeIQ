# Docker Compose Variants Guide

**Last Updated:** November 11, 2025
**Purpose:** Guide to selecting the appropriate Docker Compose configuration for your use case

---

## Overview

HomeIQ provides 6 different Docker Compose configurations optimized for different deployment scenarios and development workflows. This guide helps you select the right configuration for your needs.

## Quick Selection Guide

| Use Case | File | Services | Startup Time | Memory |
|----------|------|----------|--------------|--------|
| **Production (Full)** | `docker-compose.yml` | All 22 services | ~60s | ~4-6GB |
| **Production (Core)** | `docker-compose.prod.yml` | Essential only | ~30s | ~2-3GB |
| **Development** | `docker-compose.dev.yml` | Dev + debugging | ~45s | ~3-4GB |
| **Testing** | `docker-compose.simple.yml` | Bare minimum | ~10s | ~512MB |
| **Minimal** | `docker-compose.minimal.yml` | Data pipeline only | ~15s | ~1GB |
| **Complete (Legacy)** | `docker-compose.complete.yml` | Core + enrichment | ~25s | ~2GB |

---

## Detailed Configurations

### 1. `docker-compose.yml` - Full Production Stack
**Size:** 33KB | **Services:** 22 | **Recommended For:** Production deployments

#### What's Included
- **Core Infrastructure**: InfluxDB, MQTT Mosquitto
- **Data Pipeline**: WebSocket ingestion, Data API, Admin API
- **Enrichment Services (6)**: Weather, Energy, Air Quality, Sports, Calendar, Carbon
- **AI/ML Services (8)**: AI Automation, Device Intelligence, AI Core, OpenVINO, ML, NER, OpenAI, Automation Miner
- **Frontend**: Health Dashboard, AI Automation UI
- **Utilities**: Log Aggregator, Data Retention

#### Use When
✅ Running in production with all features enabled
✅ Need complete AI/ML capabilities
✅ Want all data enrichment sources
✅ Have sufficient hardware (4GB+ RAM)

#### Quick Start
```bash
docker-compose up -d
```

#### Access Points
- Health Dashboard: http://localhost:3000
- AI Automation UI: http://localhost:3001
- Admin API: http://localhost:8003
- Data API: http://localhost:8006

---

### 2. `docker-compose.prod.yml` - Production Core
**Size:** 8.9KB | **Services:** ~12 | **Recommended For:** Resource-constrained production

#### What's Included
- **Core Infrastructure**: InfluxDB
- **Data Pipeline**: WebSocket ingestion, Data API, Admin API
- **Essential Services**: Device Intelligence, Data Retention
- **Frontend**: Health Dashboard

#### What's Excluded
- AI/ML services (use AI Automation Service only if needed)
- Most enrichment services (enable selectively)
- Development tools

#### Use When
✅ Limited hardware (2-3GB RAM)
✅ Don't need AI features immediately
✅ Want faster startup times
✅ Production environment with core features only

#### Quick Start
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

### 3. `docker-compose.dev.yml` - Development Environment
**Size:** 6.8KB | **Services:** ~15 | **Recommended For:** Local development

#### What's Included
- All core services
- Selected enrichment services for testing
- AI services for development
- Development tools and debugging
- Port mappings for direct service access

#### Special Features
- **Hot Reload**: Source code mounted for live updates
- **Debug Ports**: Exposed for IDE debugging
- **Development Logging**: Verbose logging enabled
- **Local Volumes**: Persistent data for development

#### Use When
✅ Developing new features
✅ Testing service integrations
✅ Debugging issues
✅ Need source code hot reload

#### Quick Start
```bash
docker-compose -f docker-compose.dev.yml up
```

---

### 4. `docker-compose.simple.yml` - Basic Testing
**Size:** 1.5KB | **Services:** 3-4 | **Recommended For:** Quick tests, CI/CD

#### What's Included
- InfluxDB (database)
- WebSocket Ingestion (core pipeline)
- Health Dashboard (minimal UI)

#### What's Excluded
- All enrichment services
- AI/ML services
- Most APIs

#### Use When
✅ Testing core data pipeline only
✅ CI/CD integration tests
✅ Minimal resource environment
✅ Quick startup needed (<15s)

#### Quick Start
```bash
docker-compose -f docker-compose.simple.yml up -d
```

---

### 5. `docker-compose.minimal.yml` - Data Pipeline Only
**Size:** 1.4KB | **Services:** 4-5 | **Recommended For:** Data collection only

#### What's Included
- InfluxDB (time-series database)
- WebSocket Ingestion (HA events)
- Data Retention (cleanup)
- Basic monitoring

#### What's Excluded
- All enrichment services
- AI/ML services
- Frontend dashboards
- Most APIs

#### Use When
✅ Only need event collection from Home Assistant
✅ Using external systems for analysis
✅ Embedded/IoT deployment
✅ Minimum memory footprint required

#### Quick Start
```bash
docker-compose -f docker-compose.minimal.yml up -d
```

---

### 6. `docker-compose.complete.yml` - Complete Stack (Legacy)
**Size:** 3.7KB | **Services:** ~10 | **Recommended For:** Transitional deployments

#### What's Included
- Core infrastructure
- Data pipeline
- Some enrichment services
- Basic AI services

#### Status
⚠️ **Legacy Configuration** - Use `docker-compose.yml` or `docker-compose.prod.yml` instead

#### Use When
✅ Migrating from older versions
✅ Need compatibility with legacy deployments
✅ Specific service subset required

---

## Customization Guide

### Adding/Removing Services

#### Method 1: Override File
Create `docker-compose.override.yml`:
```yaml
services:
  # Add new service
  my-custom-service:
    image: my-image:latest

  # Remove service (set to null)
  sports-api: null
```

#### Method 2: Selective Startup
Start only specific services:
```bash
docker-compose up influxdb websocket-ingestion data-api
```

### Environment-Specific Configurations

#### Production
```bash
# Use production config with environment override
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

#### Staging
```bash
# Use full stack with staging environment
docker-compose --env-file .env.staging up -d
```

#### Development
```bash
# Use dev config with local overrides
docker-compose -f docker-compose.dev.yml -f docker-compose.override.yml up
```

---

## Resource Requirements

### Minimum Requirements by Configuration

| Configuration | CPU | RAM | Disk | Network |
|--------------|-----|-----|------|---------|
| **Full (docker-compose.yml)** | 4 cores | 4GB | 20GB | 100Mbps |
| **Prod (docker-compose.prod.yml)** | 2 cores | 2GB | 10GB | 50Mbps |
| **Dev (docker-compose.dev.yml)** | 2 cores | 3GB | 15GB | 50Mbps |
| **Simple (docker-compose.simple.yml)** | 1 core | 512MB | 5GB | 10Mbps |
| **Minimal (docker-compose.minimal.yml)** | 1 core | 1GB | 5GB | 10Mbps |

### Recommended Requirements

| Configuration | CPU | RAM | Disk | Network |
|--------------|-----|-----|------|---------|
| **Full** | 8 cores | 8GB | 50GB | 1Gbps |
| **Prod** | 4 cores | 4GB | 30GB | 100Mbps |
| **Dev** | 4 cores | 6GB | 40GB | 100Mbps |

---

## Troubleshooting

### Configuration Won't Start

**Check resource availability:**
```bash
docker system df
docker stats
```

**Verify port conflicts:**
```bash
netstat -tuln | grep -E ':(3000|3001|8001|8003|8006|8086)'
```

**Check logs:**
```bash
docker-compose -f <config-file> logs --tail=50
```

### Services Keep Restarting

**Check service health:**
```bash
docker-compose -f <config-file> ps
```

**View specific service logs:**
```bash
docker-compose -f <config-file> logs <service-name>
```

**Restart individual service:**
```bash
docker-compose -f <config-file> restart <service-name>
```

### Out of Memory Errors

**Reduce services:**
- Switch from `docker-compose.yml` to `docker-compose.prod.yml`
- Use `docker-compose.minimal.yml` for lowest memory

**Increase Docker memory limit:**
```bash
# Docker Desktop: Preferences → Resources → Memory
# Linux: Adjust cgroup limits
```

---

## Migration Guide

### From Simple → Production

1. **Export data:**
   ```bash
   docker exec homeiq-influxdb influx backup /backup
   ```

2. **Stop simple stack:**
   ```bash
   docker-compose -f docker-compose.simple.yml down
   ```

3. **Start production stack:**
   ```bash
   docker-compose up -d
   ```

4. **Restore data (if needed):**
   ```bash
   docker exec homeiq-influxdb influx restore /backup
   ```

### From Full → Minimal (Downgrade)

1. **Backup InfluxDB data**
2. **Stop full stack:**
   ```bash
   docker-compose down
   ```

3. **Start minimal stack:**
   ```bash
   docker-compose -f docker-compose.minimal.yml up -d
   ```

**Note:** AI/ML features and enrichment data will not be available in minimal mode.

---

## Best Practices

### 1. Use Environment Files
```bash
# Don't hardcode secrets in docker-compose files
# Use .env files:
.env              # Default/development
.env.production   # Production secrets
.env.staging      # Staging environment
```

### 2. Version Control
```bash
# Track compose files in git
git add docker-compose*.yml

# Don't track environment files with secrets
echo ".env.production" >> .gitignore
```

### 3. Health Checks
```bash
# Monitor service health
docker-compose ps
docker inspect --format='{{.State.Health.Status}}' <container>
```

### 4. Logging
```bash
# Configure log rotation in compose files
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 5. Backup Strategy
```bash
# Regular backups
docker-compose exec influxdb influx backup /backup/$(date +%Y%m%d)

# Export SQLite databases
docker cp <container>:/app/data/device_intelligence.db ./backup/
```

---

## Related Documentation

- [Installation Guide](INSTALLATION.md) - Initial setup instructions
- [Environment Configuration](ENVIRONMENT_VARIABLES.md) - Environment variable reference
- [Service Documentation](docs/services/README.md) - Individual service details
- [Performance Tuning](CLAUDE.md) - Performance optimization guide
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

---

## Quick Reference

```bash
# Start full production stack
docker-compose up -d

# Start production core only
docker-compose -f docker-compose.prod.yml up -d

# Start development environment
docker-compose -f docker-compose.dev.yml up

# Start minimal testing stack
docker-compose -f docker-compose.simple.yml up -d

# Stop all services
docker-compose down

# Stop and remove volumes (DESTRUCTIVE)
docker-compose down -v

# View logs
docker-compose logs -f <service-name>

# Restart specific service
docker-compose restart <service-name>

# Scale service (if supported)
docker-compose up -d --scale <service-name>=3
```

---

**Document Metadata:**
- **Created:** November 11, 2025
- **Purpose:** Docker Compose variant selection guide
- **Audience:** Developers, DevOps, System Administrators
- **Review Schedule:** Quarterly or after major infrastructure changes
