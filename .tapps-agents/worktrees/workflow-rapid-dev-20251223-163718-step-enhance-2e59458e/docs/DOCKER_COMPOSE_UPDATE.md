# Docker Compose Update for MCP Code Execution

## Add this service to docker-compose.yml

Insert this block **after** the `ai-core-service` section (around line 850) and **before** the `ai-automation-service` section:

```yaml
  # AI Code Executor - MCP Code Execution Pattern (NEW)
  ai-code-executor:
    build:
      context: .
      dockerfile: services/ai-code-executor/Dockerfile
    container_name: homeiq-code-executor
    restart: unless-stopped
    ports:
      - "8030:8030"
    environment:
      - EXECUTION_TIMEOUT=30
      - MAX_MEMORY_MB=128
      - MAX_CPU_PERCENT=50.0
      - MCP_WORKSPACE_DIR=/tmp/mcp_workspace
      - LOG_LEVEL=INFO
    networks:
      - homeiq-network
    deploy:
      resources:
        limits:
          memory: 256M  # Sandbox + overhead
          cpus: '0.5'   # Max 50% of one core
        reservations:
          memory: 128M
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8030/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=ai-code-executor,environment=production"
```

## Update ai-automation-service

Add this environment variable to the `ai-automation-service` section (around line 861):

```yaml
      - MCP_CODE_EXECUTOR_URL=http://ai-code-executor:8030
```

And add this dependency:

```yaml
    depends_on:
      data-api:
        condition: service_healthy
      ner-service:
        condition: service_healthy
      openai-service:
        condition: service_healthy
      ai-code-executor:  # ADD THIS
        condition: service_healthy
```

## Full Manual Update Instructions

1. Open `/home/user/HomeIQ/docker-compose.yml`
2. Find line 850 (end of `ai-core-service` section)
3. Insert the `ai-code-executor` service block above
4. Find the `ai-automation-service` section (around line 861)
5. Add `MCP_CODE_EXECUTOR_URL` to environment
6. Add `ai-code-executor` to depends_on

## Testing

After updating docker-compose.yml:

```bash
# Build new service
docker compose build ai-code-executor

# Start all services
docker compose up -d

# Check ai-code-executor health
curl http://localhost:8030/health

# Check logs
docker compose logs ai-code-executor
```
