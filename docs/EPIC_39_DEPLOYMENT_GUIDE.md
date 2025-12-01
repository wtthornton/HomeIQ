# Epic 39: Microservices Deployment Guide

**Epic 39, Story 39.16: Documentation & Deployment Guide**  
**Last Updated:** January 2025

## Overview

This guide covers deployment of the modularized AI Automation microservices created in Epic 39.

## Architecture Overview

The AI Automation Service has been split into 4 focused microservices:

1. **ai-training-service** (Port 8017) - Model training and synthetic data
2. **ai-pattern-service** (Port 8016) - Pattern detection and daily analysis
3. **ai-query-service** (Port 8018) - Low-latency query processing
4. **ai-automation-service-new** (Port 8021) - Suggestion generation and deployment

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended for all services)
- 50GB storage minimum
- Home Assistant instance accessible
- OpenAI API key (for query and training services)

## Docker Compose Configuration

### Service Definitions

All new services are configured in `docker-compose.yml`:

```yaml
ai-training-service:
  build:
    context: .
    dockerfile: services/ai-training-service/Dockerfile
  container_name: homeiq-ai-training
  ports:
    - "8017:8017"
  environment:
    - DATABASE_URL=sqlite+aiosqlite:////app/data/shared.db
    - DATA_API_URL=http://data-api:8006
    - OPENAI_API_KEY=${OPENAI_API_KEY}
  volumes:
    - ai_automation_data:/app/data
  networks:
    - homeiq-network

ai-pattern-service:
  build:
    context: .
    dockerfile: services/ai-pattern-service/Dockerfile
  container_name: homeiq-ai-pattern
  ports:
    - "8016:8016"
  environment:
    - DATABASE_URL=sqlite+aiosqlite:////app/data/shared.db
    - DATA_API_URL=http://data-api:8006
    - MQTT_BROKER=${MQTT_BROKER:-192.168.1.86}
    - MQTT_PORT=${MQTT_PORT:-1883}
  volumes:
    - ai_automation_data:/app/data
  networks:
    - homeiq-network

ai-query-service:
  build:
    context: .
    dockerfile: services/ai-query-service/Dockerfile
  container_name: homeiq-ai-query
  ports:
    - "8018:8018"
  environment:
    - DATABASE_URL=sqlite+aiosqlite:////app/data/shared.db
    - DATA_API_URL=http://data-api:8006
    - OPENAI_API_KEY=${OPENAI_API_KEY}
  volumes:
    - ai_automation_data:/app/data
  networks:
    - homeiq-network

ai-automation-service-new:
  build:
    context: .
    dockerfile: services/ai-automation-service-new/Dockerfile
  container_name: homeiq-ai-automation-new
  ports:
    - "8021:8021"
  environment:
    - DATABASE_URL=sqlite+aiosqlite:////app/data/shared.db
    - HA_URL=${HA_URL:-http://192.168.1.86:8123}
    - HA_TOKEN=${HA_TOKEN}
  volumes:
    - ai_automation_data:/app/data
  networks:
    - homeiq-network
```

## Deployment Steps

### 1. Environment Configuration

Update `.env` file with required variables:

```bash
# Shared Database
DATABASE_URL=sqlite+aiosqlite:////app/data/shared.db
DATABASE_PATH=/app/data/shared.db

# Cache
CORRELATION_CACHE_DB=/app/data/correlation_cache.db

# Service URLs (for inter-service communication)
DATA_API_URL=http://data-api:8006
AI_QUERY_SERVICE_URL=http://ai-query-service:8018
AI_AUTOMATION_SERVICE_URL=http://ai-automation-service-new:8021
AI_TRAINING_SERVICE_URL=http://ai-training-service:8017
AI_PATTERN_SERVICE_URL=http://ai-pattern-service:8016

# OpenAI (for query and training services)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.1  # Default model (GPT-5.1-mini for low-risk tasks: 80% cost savings)

# Home Assistant (for automation service)
HA_URL=http://192.168.1.86:8123
HA_TOKEN=your-ha-long-lived-access-token

# MQTT (for pattern service)
MQTT_BROKER=192.168.1.86
MQTT_PORT=1883
MQTT_USERNAME=your-mqtt-username
MQTT_PASSWORD=your-mqtt-password
```

### 2. Build Services

```bash
# Build all new services
docker compose build ai-training-service ai-pattern-service ai-query-service ai-automation-service-new
```

### 3. Start Services

```bash
# Start all new services
docker compose up -d ai-training-service ai-pattern-service ai-query-service ai-automation-service-new

# Or start all services
docker compose up -d
```

### 4. Verify Deployment

```bash
# Check service status
docker compose ps

# Check service health
curl http://localhost:8017/health/health  # Training service
curl http://localhost:8016/health/health  # Pattern service
curl http://localhost:8018/health/health  # Query service
curl http://localhost:8021/health/health  # Automation service

# Check service logs
docker compose logs -f ai-training-service
docker compose logs -f ai-pattern-service
docker compose logs -f ai-query-service
docker compose logs -f ai-automation-service-new
```

## Service Startup Order

### Required Order

1. **Data API** - Required by all services
2. **InfluxDB** - Required by Data API
3. **Shared Infrastructure Services** (training, pattern, query)
4. **Automation Service** - Depends on query service

### Health Checks

All services include health check endpoints:
- `/health/health` - Basic health check
- `/health/ready` - Readiness check (database connectivity)
- `/health/live` - Liveness check

## Shared Infrastructure

### Shared Database

All services share the same SQLite database:
- **Path**: `/app/data/shared.db` (in container)
- **Volume**: `ai_automation_data:/app/data`
- **Tables**: patterns, synergies, suggestions, training_runs, etc.

### Shared Cache

Correlation cache is shared across services:
- **Path**: `/app/data/correlation_cache.db`
- **Type**: SQLite-backed, two-tier (in-memory LRU + SQLite)
- **TTL**: 1 hour (configurable)

### Shared Network

All services use `homeiq-network` for inter-service communication:
- Services can communicate using Docker service names
- Example: `http://ai-query-service:8018`

## Inter-Service Communication

### Service-to-Service HTTP

Services use `shared/service_client.py` for reliable communication:

```python
from shared.service_client import get_service_client

client = get_service_client("data-api")
events = await client.get("/api/v1/events", params={"limit": 100})
```

### Default Service URLs

- `data-api`: http://data-api:8006
- `ai-query-service`: http://ai-query-service:8018
- `ai-automation-service-new`: http://ai-automation-service-new:8021
- `ai-training-service`: http://ai-training-service:8017
- `ai-pattern-service`: http://ai-pattern-service:8016

## Monitoring

### Health Checks

Monitor service health:

```bash
# All services
for port in 8017 8016 8018 8021; do
  echo "Checking port $port..."
  curl -s http://localhost:$port/health/health | jq
done
```

### Service Logs

```bash
# Follow all AI service logs
docker compose logs -f ai-training-service ai-pattern-service ai-query-service ai-automation-service-new

# Follow specific service
docker compose logs -f ai-query-service
```

### Resource Usage

```bash
# Check resource usage
docker stats homeiq-ai-training homeiq-ai-pattern homeiq-ai-query homeiq-ai-automation-new
```

## Troubleshooting

### Service Won't Start

1. **Check logs**: `docker compose logs <service-name>`
2. **Check database**: Ensure shared database volume is accessible
3. **Check dependencies**: Ensure Data API is running
4. **Check ports**: Ensure ports are not already in use

### Database Connection Issues

1. **Verify database path**: Check `DATABASE_URL` environment variable
2. **Check volume mounts**: Ensure `ai_automation_data` volume exists
3. **Check permissions**: Ensure services can write to `/app/data`

### Inter-Service Communication Issues

1. **Verify network**: Check services are on `homeiq-network`
2. **Check service names**: Use Docker service names, not localhost
3. **Test connectivity**: `docker compose exec <service> curl http://<other-service>:<port>/health`

### Performance Issues

1. **Check cache hit rates**: Monitor correlation cache statistics
2. **Check database pool**: Monitor connection pool usage
3. **Check service resources**: Monitor memory and CPU usage

## Migration from Monolithic Service

### Gradual Migration

The monolithic `ai-automation-service` (Port 8018) can coexist with new services:

1. **Phase 1**: Deploy new services alongside monolithic service
2. **Phase 2**: Route new traffic to microservices
3. **Phase 3**: Migrate remaining functionality
4. **Phase 4**: Decommission monolithic service

### Backward Compatibility

- Existing endpoints remain in monolithic service
- New endpoints added to microservices
- Shared database ensures data consistency
- No breaking changes during migration

## Rollback Plan

If issues occur:

1. **Stop new services**: `docker compose stop ai-training-service ai-pattern-service ai-query-service ai-automation-service-new`
2. **Restore monolithic service**: Use existing `ai-automation-service`
3. **Fix issues**: Address problems in new services
4. **Redeploy**: Start services again after fixes

## Related Documentation

- [Microservices Architecture](architecture/epic-39-microservices-architecture.md)
- [API Reference](api/API_REFERENCE.md)
- [Performance Optimization Guide](../services/ai-automation-service/PERFORMANCE_OPTIMIZATION_GUIDE.md)
- [Shared Infrastructure Documentation](../shared/STORY_39_11_SHARED_INFRASTRUCTURE.md)

