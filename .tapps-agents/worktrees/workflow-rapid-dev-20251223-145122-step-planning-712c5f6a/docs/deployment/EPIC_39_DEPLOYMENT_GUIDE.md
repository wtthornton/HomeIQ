# Epic 39 Deployment Guide

**Epic:** 39 - AI Automation Service Modularization  
**Status:** ✅ **COMPLETE**  
**Date:** December 2025

## Overview

This guide covers deployment of the modularized AI services architecture created in Epic 39.

## Prerequisites

- Docker and Docker Compose installed
- SQLite database file at `/app/data/ai_automation.db` (shared across services)
- Environment variables configured (see Configuration section)

## Service Architecture

The modularized architecture consists of four services:

1. **AI Query Service** (Port 8018) - Query processing
2. **AI Pattern Service** (Port 8020) - Pattern detection
3. **AI Training Service** (Port 8022) - Model training
4. **AI Automation Service** (Port 8025) - Automation generation and deployment

## Docker Compose Configuration

All services are configured in `docker-compose.yml`:

```yaml
services:
  ai-query-service:
    build:
      context: .
      dockerfile: services/ai-query-service/Dockerfile
    ports:
      - "8018:8018"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////app/data/ai_automation.db
      - DATA_API_URL=http://data-api:8006
    volumes:
      - ai_automation_data:/app/data
    networks:
      - homeiq-network

  ai-pattern-service:
    build:
      context: .
      dockerfile: services/ai-pattern-service/Dockerfile
    ports:
      - "8020:8020"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////app/data/ai_automation.db
      - DATA_API_URL=http://data-api:8006
    volumes:
      - ai_automation_data:/app/data
    networks:
      - homeiq-network

  ai-training-service:
    build:
      context: .
      dockerfile: services/ai-training-service/Dockerfile
    ports:
      - "8022:8022"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////app/data/ai_automation.db
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ai_automation_data:/app/data
      - ai_automation_models:/app/models
    networks:
      - homeiq-network

  ai-automation-service:
    build:
      context: .
      dockerfile: services/ai-automation-service-new/Dockerfile
    ports:
      - "8025:8025"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:////app/data/ai_automation.db
      - DATA_API_URL=http://data-api:8006
      - QUERY_SERVICE_URL=http://ai-query-service:8018
      - PATTERN_SERVICE_URL=http://ai-pattern-service:8020
      - HA_URL=${HA_URL}
      - HA_TOKEN=${HA_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ai_automation_data:/app/data
    networks:
      - homeiq-network
```

## Configuration

### Environment Variables

**Required for all services:**
- `DATABASE_URL`: SQLite database path (shared)
- `DATA_API_URL`: Data API service URL

**Service-specific:**
- **Query Service**: None additional
- **Pattern Service**: MQTT configuration (optional)
- **Training Service**: `OPENAI_API_KEY` (for synthetic data generation)
- **Automation Service**: 
  - `HA_URL`: Home Assistant URL
  - `HA_TOKEN`: Home Assistant token
  - `OPENAI_API_KEY`: OpenAI API key
  - `QUERY_SERVICE_URL`: Query service URL
  - `PATTERN_SERVICE_URL`: Pattern service URL

### Database Configuration

**Shared Database:**
- **Path**: `/app/data/ai_automation.db`
- **Volume**: `ai_automation_data` (shared across services)
- **Connection Pooling**: 
  - Pool size: 10 per service
  - Max overflow: 5 per service
  - Total max: 15 per service

### Cache Configuration

**CorrelationCache:**
- **Path**: `/app/data/correlation_cache.db` (optional, can be in-memory)
- **Shared**: Yes - accessible to all services
- **Memory Cache Size**: 1000 entries (configurable)

## Deployment Steps

### 1. Build Services

```bash
# Build all services
docker-compose build ai-query-service ai-pattern-service ai-training-service ai-automation-service

# Or build individually
docker-compose build ai-query-service
docker-compose build ai-pattern-service
docker-compose build ai-training-service
docker-compose build ai-automation-service
```

### 2. Start Services

```bash
# Start all services
docker-compose up -d ai-query-service ai-pattern-service ai-training-service ai-automation-service

# Or start individually
docker-compose up -d ai-query-service
docker-compose up -d ai-pattern-service
docker-compose up -d ai-training-service
docker-compose up -d ai-automation-service
```

### 3. Verify Health

```bash
# Check health endpoints
curl http://localhost:8018/health  # Query service
curl http://localhost:8020/health  # Pattern service
curl http://localhost:8022/health  # Training service
curl http://localhost:8025/health  # Automation service
```

### 4. Check Logs

```bash
# View logs for all services
docker-compose logs -f ai-query-service ai-pattern-service ai-training-service ai-automation-service

# View logs for individual service
docker-compose logs -f ai-query-service
```

## Service Communication

### Internal Communication

Services communicate via HTTP using Docker Compose service names:

- Query Service → Data API: `http://data-api:8006`
- Pattern Service → Data API: `http://data-api:8006`
- Automation Service → Query Service: `http://ai-query-service:8018`
- Automation Service → Pattern Service: `http://ai-pattern-service:8020`

### External Communication

- **Query Service**: Exposed on port 8018
- **Pattern Service**: Exposed on port 8020
- **Training Service**: Exposed on port 8022
- **Automation Service**: Exposed on port 8025

## Monitoring

### Health Checks

All services have health check endpoints:
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check (with database)
- `GET /health/live` - Liveness check

### Performance Monitoring

- **Query Latency**: Target <500ms P95
- **Database Connections**: Monitor pool usage
- **Cache Hit Rate**: Target >80%
- **Memory Usage**: Target <500MB per service

## Troubleshooting

### Service Won't Start

1. Check logs: `docker-compose logs <service-name>`
2. Verify database path exists and is accessible
3. Check environment variables are set correctly
4. Verify network connectivity between services

### Database Connection Issues

1. Verify database file exists at `/app/data/ai_automation.db`
2. Check database file permissions
3. Verify connection pool settings
4. Check for database locks (SQLite WAL mode helps)

### Service Communication Issues

1. Verify Docker Compose network: `docker network inspect homeiq-network`
2. Check service names resolve: `docker-compose exec <service> ping <other-service>`
3. Verify service URLs in environment variables
4. Check firewall rules

### Performance Issues

1. Monitor database connection pool usage
2. Check cache hit rates
3. Profile query latency
4. Review service logs for slow operations

## Rollback

If issues occur, you can rollback to the monolithic service:

```bash
# Stop modular services
docker-compose stop ai-query-service ai-pattern-service ai-training-service ai-automation-service

# Start monolithic service (if still available)
docker-compose up -d ai-automation-service  # Original monolithic service
```

## Upgrades

### Updating Services

1. Pull latest code
2. Rebuild services: `docker-compose build <service-name>`
3. Restart service: `docker-compose up -d <service-name>`
4. Verify health: `curl http://localhost:<port>/health`

### Database Migrations

Database migrations are handled automatically via Alembic (if configured) or manual SQL scripts.

## Best Practices

1. **Start Services in Order**: Start data-api first, then AI services
2. **Monitor Health**: Regularly check health endpoints
3. **Resource Limits**: Set appropriate memory/CPU limits per service
4. **Logging**: Use structured logging for better observability
5. **Backup Database**: Regularly backup shared SQLite database

## Support

For issues or questions:
- Check service logs: `docker-compose logs <service-name>`
- Review architecture docs: `docs/architecture/epic-39-service-modularization.md`
- Check epic document: `docs/prd/epic-39-ai-automation-service-modularization.md`

---

**Last Updated:** December 2025  
**Related Documents:**
- Architecture: `docs/architecture/epic-39-service-modularization.md`
- Epic Document: `docs/prd/epic-39-ai-automation-service-modularization.md`

