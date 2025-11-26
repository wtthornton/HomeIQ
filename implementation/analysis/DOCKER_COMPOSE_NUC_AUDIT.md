# Docker Compose NUC Resource Limits Audit

**Date:** January 2025  
**Purpose:** Audit docker-compose.yml for NUC-optimized resource limits  
**Target:** Single-home Home Assistant deployment on NUC

## Current Resource Limits vs NUC Recommendations

### Core Services (Critical for NUC Optimization)

| Service | Current Limit | Current Reservation | NUC Recommended Limit | NUC Recommended Reservation | Status |
|---------|--------------|---------------------|----------------------|----------------------------|--------|
| **influxdb** | 512M | 256M | **256M** | 128M | ⚠️ Needs Update |
| **websocket-ingestion** | 512M | 256M | **256M** | 128M | ⚠️ Needs Update |
| **data-api** | 1G | 512M | **128M** | 64M | ⚠️ Needs Update |
| **admin-api** | 256M | 128M | **128M** | 64M | ✅ OK |
| **health-dashboard** | 128M | 64M | **64M** | 32M | ✅ OK |

### External Data Services (Lower Priority)

| Service | Current Limit | Current Reservation | NUC Recommended Limit | NUC Recommended Reservation | Status |
|---------|--------------|---------------------|----------------------|----------------------------|--------|
| **weather-api** | 192M | 96M | **128M** | 64M | ⚠️ Can Optimize |
| **sports-data** | 192M | 96M | **128M** | 64M | ⚠️ Can Optimize |
| **carbon-intensity** | 192M | 96M | **128M** | 64M | ⚠️ Can Optimize |
| **electricity-pricing** | 192M | 96M | **128M** | 64M | ⚠️ Can Optimize |
| **air-quality** | 192M | 96M | **128M** | 64M | ⚠️ Can Optimize |

### AI Services (High Memory - May Need Adjustment)

| Service | Current Limit | Current Reservation | NUC Recommended Limit | NUC Recommended Reservation | Status |
|---------|--------------|---------------------|----------------------|----------------------------|--------|
| **ai-automation-service** | 512M | 256M | **256M** | 128M | ⚠️ Needs Update |
| **ner-service** | 1G | 512M | **512M** | 256M | ⚠️ Needs Update |
| **openai-service** | 256M | 128M | **128M** | 64M | ✅ OK |
| **openvino-service** | 1.5G | 1G | **1G** | 512M | ⚠️ Needs Update |
| **ml-service** | 512M | 256M | **256M** | 128M | ⚠️ Needs Update |
| **ai-training-service** | 2G | 512M | **1G** | 256M | ⚠️ Needs Update |

## Recommended Changes

### Priority 1: Core Services (Must Update)

```yaml
# InfluxDB - Reduce from 512M to 256M
influxdb:
  deploy:
    resources:
      limits:
        memory: 256M  # Reduced from 512M for NUC
      reservations:
        memory: 128M  # Reduced from 256M for NUC

# WebSocket Ingestion - Reduce from 512M to 256M
websocket-ingestion:
  deploy:
    resources:
      limits:
        memory: 256M  # Reduced from 512M for NUC
      reservations:
        memory: 128M  # Reduced from 256M for NUC

# Data API - Reduce from 1G to 128M
data-api:
  deploy:
    resources:
      limits:
        memory: 128M  # Reduced from 1G for NUC
      reservations:
        memory: 64M   # Reduced from 512M for NUC
```

### Priority 2: External Data Services (Can Optimize)

```yaml
# Weather API - Reduce from 192M to 128M
weather-api:
  deploy:
    resources:
      limits:
        memory: 128M  # Reduced from 192M for NUC
      reservations:
        memory: 64M   # Reduced from 96M for NUC

# Sports Data - Reduce from 192M to 128M
sports-data:
  deploy:
    resources:
      limits:
        memory: 128M  # Reduced from 192M for NUC
      reservations:
        memory: 64M   # Reduced from 96M for NUC

# Carbon Intensity - Reduce from 192M to 128M
carbon-intensity:
  deploy:
    resources:
      limits:
        memory: 128M  # Reduced from 192M for NUC
      reservations:
        memory: 64M   # Reduced from 96M for NUC
```

### Priority 3: AI Services (Conditional - Only if Running)

```yaml
# AI Automation Service - Reduce from 512M to 256M
ai-automation-service:
  deploy:
    resources:
      limits:
        memory: 256M  # Reduced from 512M for NUC
      reservations:
        memory: 128M  # Reduced from 256M for NUC

# NER Service - Reduce from 1G to 512M
ner-service:
  deploy:
    resources:
      limits:
        memory: 512M  # Reduced from 1G for NUC
      reservations:
        memory: 256M  # Reduced from 512M for NUC

# OpenVINO Service - Reduce from 1.5G to 1G
openvino-service:
  deploy:
    resources:
      limits:
        memory: 1G    # Reduced from 1.5G for NUC
      reservations:
        memory: 512M  # Reduced from 1G for NUC

# ML Service - Reduce from 512M to 256M
ml-service:
  deploy:
    resources:
      limits:
        memory: 256M  # Reduced from 512M for NUC
      reservations:
        memory: 128M  # Reduced from 256M for NUC

# AI Training Service - Reduce from 2G to 1G
ai-training-service:
  deploy:
    resources:
      limits:
        memory: 1G    # Reduced from 2G for NUC
      reservations:
        memory: 256M  # Reduced from 512M for NUC
```

## CPU Limits (Optional but Recommended)

Add CPU limits to prevent services from consuming all CPU:

```yaml
services:
  websocket-ingestion:
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'  # Limit to 50% of one CPU core
        reservations:
          memory: 128M
          cpus: '0.3'  # Reserve 30% of one CPU core

  data-api:
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.3'  # Limit to 30% of one CPU core
        reservations:
          memory: 64M
          cpus: '0.2'  # Reserve 20% of one CPU core

  admin-api:
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.3'  # Limit to 30% of one CPU core
        reservations:
          memory: 64M
          cpus: '0.2'  # Reserve 20% of one CPU core

  influxdb:
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'  # Limit to 50% of one CPU core
        reservations:
          memory: 128M
          cpus: '0.3'  # Reserve 30% of one CPU core
```

## Total Memory Budget

### Current Total (All Services)
- **Estimated:** ~12-15GB (if all services running)
- **Too High for NUC:** Most NUCs have 8-16GB total RAM

### NUC-Optimized Total (Core Services Only)
- **Core Services:** ~1GB (influxdb 256M + websocket 256M + data-api 128M + admin-api 128M + dashboard 64M + others ~200M)
- **AI Services (if enabled):** ~2-3GB additional
- **Reserve for Home Assistant:** 512MB-1GB
- **Reserve for OS:** 512MB-1GB
- **Total:** ~2-4GB for HomeIQ + 1-2GB reserve = **3-6GB total**

## Implementation Recommendations

### Phase 1: Core Services (Immediate)
1. Update InfluxDB: 512M → 256M
2. Update WebSocket Ingestion: 512M → 256M
3. Update Data API: 1G → 128M
4. Add CPU limits to core services

### Phase 2: External Services (Optional)
1. Update Weather API: 192M → 128M
2. Update Sports Data: 192M → 128M
3. Update Carbon Intensity: 192M → 128M
4. Update other external services similarly

### Phase 3: AI Services (Conditional)
1. Only update if AI services are actively used
2. Consider disabling AI services if NUC has <8GB RAM
3. Update AI service limits if needed

## Testing Recommendations

1. **Monitor Memory Usage:** Use `docker stats` to monitor actual usage
2. **Test Under Load:** Verify services handle typical single-home event volume
3. **Check Health Endpoints:** Ensure all services remain healthy with reduced limits
4. **Monitor for OOM Kills:** Watch for out-of-memory kills in logs
5. **Gradual Reduction:** Reduce limits gradually, not all at once

## Notes

- **NUC Constraints:** Most NUCs have 8-16GB RAM total
- **Home Assistant Reserve:** Need to reserve 512MB-1GB for Home Assistant
- **OS Reserve:** Need to reserve 512MB-1GB for OS
- **Single-Home Context:** Lower event volumes allow for reduced memory
- **SSD Recommended:** Faster I/O helps with reduced memory limits

## References

- Performance Targets: `docs/architecture/performance-targets.md`
- Performance Patterns: `docs/architecture/performance-patterns.md`
- Deployment Architecture: `docs/architecture/deployment-architecture.md`

