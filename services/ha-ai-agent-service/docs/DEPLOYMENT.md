# Deployment Guide

**Service:** HA AI Agent Service  
**Last Updated:** January 2025

This guide covers deployment of the HA AI Agent Service using Docker and docker-compose.

## Prerequisites

- Docker 24+ and Docker Compose 2.20+
- Home Assistant instance accessible via network
- OpenAI API key (for chat functionality)
- Home Assistant long-lived access token

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd HomeIQ
```

### 2. Configure Environment Variables

Create `.env` file in project root (if not exists):

```bash
# Home Assistant Configuration
HA_HTTP_URL=http://192.168.1.86:8123  # Or your HA URL
HA_TOKEN=your-home-assistant-token

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Logging
LOG_LEVEL=INFO
```

### 3. Start Service

```bash
docker-compose up -d ha-ai-agent-service
```

### 4. Verify Deployment

```bash
# Check service logs
docker-compose logs -f ha-ai-agent-service

# Check health
curl http://localhost:8030/health
```

## Docker Deployment

### Standalone Docker

```bash
# Build image
docker build -t ha-ai-agent-service -f services/ha-ai-agent-service/Dockerfile .

# Run container
docker run -d \
  --name ha-ai-agent-service \
  -p 8030:8030 \
  -e HA_URL=http://homeassistant:8123 \
  -e HA_TOKEN=your-token \
  -e OPENAI_API_KEY=your-key \
  -v ha_ai_agent_data:/app/data \
  ha-ai-agent-service
```

### Docker Compose Integration

The service is already integrated into the main `docker-compose.yml`:

```yaml
ha-ai-agent-service:
  build:
    context: .
    dockerfile: services/ha-ai-agent-service/Dockerfile
  container_name: homeiq-ha-ai-agent-service
  restart: unless-stopped
  ports:
    - "8030:8030"
  env_file:
    - .env
  environment:
    - HA_URL=${HA_HTTP_URL:-http://homeassistant:8123}
    - HA_TOKEN=${HA_TOKEN:-}
    - DATA_API_URL=http://data-api:8006
    - DEVICE_INTELLIGENCE_URL=http://device-intelligence-service:8028
    - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    - LOG_LEVEL=${LOG_LEVEL:-INFO}
  depends_on:
    data-api:
      condition: service_healthy
    device-intelligence-service:
      condition: service_healthy
  networks:
    - homeiq-network
  volumes:
    - ha_ai_agent_data:/app/data
  deploy:
    resources:
      limits:
        memory: 256M
      reservations:
        memory: 128M
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8030/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
```

## Production Deployment

### Environment Setup

1. **Create `.env` file:**
```bash
# Required
HA_HTTP_URL=http://your-ha-instance:8123
HA_TOKEN=your-long-lived-access-token
OPENAI_API_KEY=your-openai-api-key

# Optional
OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
CONVERSATION_TTL_DAYS=30
```

2. **Set CORS Origins:**
```bash
HA_AI_AGENT_ALLOWED_ORIGINS=https://your-frontend.com,https://app.your-domain.com
```

### Volume Configuration

The service uses a persistent volume for SQLite database:

```yaml
volumes:
  ha_ai_agent_data:
    driver: local
```

Database location: `/app/data/ha_ai_agent.db` (inside container)

### Resource Limits

**Recommended Production Limits:**
- **Memory:** 256MB limit, 128MB reservation
- **CPU:** No explicit limit (shares available CPU)

### Health Checks

Health check is configured in docker-compose:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8030/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

Health endpoint: `GET /health`

### Logging

Logs are configured with rotation:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

View logs:
```bash
docker-compose logs -f ha-ai-agent-service
```

## Service Dependencies

### Required Services

1. **data-api** (Port 8006)
   - Used for entity queries
   - Must be healthy before starting

2. **device-intelligence-service** (Port 8028)
   - Used for capability patterns
   - Optional (service can operate without it)

### Network Configuration

Service runs on `homeiq-network` Docker network:

```yaml
networks:
  - homeiq-network
```

Internal service URLs:
- `http://data-api:8006`
- `http://device-intelligence-service:8028`
- `http://homeassistant:8123` (external or via network)

## Database Setup

### SQLite Database

Database is created automatically on first run:

- **Location:** `/app/data/ha_ai_agent.db` (container)
- **Volume:** `ha_ai_agent_data` (persistent)
- **Schema:** Created automatically via SQLAlchemy

### Database Backup

```bash
# Backup database
docker exec homeiq-ha-ai-agent-service sqlite3 /app/data/ha_ai_agent.db ".backup /app/data/backup.db"

# Copy backup out
docker cp homeiq-ha-ai-agent-service:/app/data/backup.db ./backup.db
```

### Database Reset

```bash
# Stop service
docker-compose stop ha-ai-agent-service

# Remove volume (⚠️ deletes all data)
docker volume rm homeiq_ha_ai_agent_data

# Restart service (creates new database)
docker-compose up -d ha-ai-agent-service
```

## Updating the Service

### Update Code

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build ha-ai-agent-service
```

### Update Configuration

1. Update `.env` file
2. Restart service:
```bash
docker-compose restart ha-ai-agent-service
```

## Troubleshooting

### Service Won't Start

1. **Check logs:**
```bash
docker-compose logs ha-ai-agent-service
```

2. **Check dependencies:**
```bash
# Verify data-api is healthy
curl http://localhost:8006/health

# Verify device-intelligence-service is healthy
curl http://localhost:8028/health
```

3. **Check environment variables:**
```bash
docker exec homeiq-ha-ai-agent-service env | grep -E "HA_|OPENAI_|DATA_API"
```

### Service Unhealthy

1. **Check health endpoint:**
```bash
curl http://localhost:8030/health
```

2. **Check service logs:**
```bash
docker-compose logs --tail=50 ha-ai-agent-service
```

3. **Check database:**
```bash
docker exec homeiq-ha-ai-agent-service ls -la /app/data/
```

### Connection Issues

1. **Home Assistant:**
   - Verify `HA_URL` is correct
   - Verify `HA_TOKEN` is valid
   - Check network connectivity

2. **OpenAI API:**
   - Verify `OPENAI_API_KEY` is set
   - Check API key validity
   - Verify network access to OpenAI

3. **Internal Services:**
   - Verify services are on same Docker network
   - Check service URLs match docker-compose names

## Monitoring

### Health Check

```bash
# Manual health check
curl http://localhost:8030/health
```

Response:
```json
{
  "status": "healthy",
  "service": "ha-ai-agent-service",
  "version": "1.0.0"
}
```

### Service Status

```bash
# Check container status
docker-compose ps ha-ai-agent-service

# Check resource usage
docker stats homeiq-ha-ai-agent-service
```

## Scaling

The service is designed for single-instance deployment. For high availability:

1. **Use load balancer** in front of multiple instances
2. **Shared database** (consider PostgreSQL for multi-instance)
3. **Session affinity** (conversations tied to instance)

**Note:** Current SQLite database limits to single instance.

## Related Documentation

- [Environment Variables](./ENVIRONMENT_VARIABLES.md)
- [Error Handling](./ERROR_HANDLING.md)
- [Monitoring](./MONITORING.md)
- [Security](./SECURITY.md)

