# Deployment Scripts Guide

This guide covers the deployment scripts available for HomeIQ services.

## Quick Start

### Deploy a Single Service

```powershell
# Full redeploy (stop, rebuild, start)
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service"

# Rebuild only (keep running)
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service" -Action rebuild

# Restart only (no rebuild)
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service" -Action restart
```

### Deploy Multiple Services

```powershell
# Deploy multiple services at once
.\scripts\deploy-service.ps1 -ServiceName @("ai-pattern-service", "ha-ai-agent-service", "api-automation-edge")
```

### Advanced Options

```powershell
# Wait for services to be healthy
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service" -WaitForHealthy

# Check logs after deployment
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service" -CheckLogs

# Rebuild without cache (clean build)
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service" -NoCache

# Verbose output
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service" -Verbose

# Combine options
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service" -WaitForHealthy -CheckLogs -Verbose
```

## Script: deploy-service.ps1

### Purpose

General-purpose deployment script that can rebuild, restart, or redeploy any service or set of services.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ServiceName` | `string[]` | Yes | Service name(s) to deploy (can be multiple) |
| `Action` | `string` | No | Action to perform: `rebuild`, `restart`, or `redeploy` (default: `redeploy`) |
| `WaitForHealthy` | `switch` | No | Wait for service health check to pass |
| `CheckLogs` | `switch` | No | Show service logs after deployment |
| `NoCache` | `switch` | No | Build without using Docker cache |
| `Verbose` | `switch` | No | Show detailed output |

### Actions

1. **redeploy** (default)
   - Stops the service
   - Rebuilds the Docker image
   - Starts the service
   - Best for deploying code changes

2. **rebuild**
   - Rebuilds the Docker image
   - Service keeps running (uses existing container)
   - Best for testing builds without downtime

3. **restart**
   - Restarts the service without rebuilding
   - Best for configuration changes or quick restarts

### Examples

#### Example 1: Deploy Single Service

```powershell
# Deploy ai-pattern-service with full redeploy
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service"
```

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HomeIQ Service Deployment Script
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Configuration:
  Services:    ai-pattern-service
  Action:      redeploy
  Wait Healthy: False
  Check Logs:  False

[Stops service, rebuilds, starts, shows status]
```

#### Example 2: Deploy Multiple Services with Health Checks

```powershell
.\scripts\deploy-service.ps1 -ServiceName @(
    "ai-pattern-service",
    "ha-ai-agent-service",
    "api-automation-edge"
) -WaitForHealthy -CheckLogs
```

#### Example 3: Quick Restart (No Rebuild)

```powershell
# Restart without rebuilding (faster)
.\scripts\deploy-service.ps1 -ServiceName "data-api" -Action restart
```

#### Example 4: Clean Build

```powershell
# Build without cache (ensures clean build)
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service" -NoCache
```

## Other Deployment Scripts

### Service-Specific Scripts

- **`deploy-yaml-validation-changes.ps1`** - Deploys YAML validation changes
  - Updates: `ai-automation-service`, `ha-ai-agent-service`, `ai-automation-ui`

- **`deploy-device-database-services.ps1`** - Deploys device database services

- **`deploy-device-suggestions.ps1`** - Deploys device suggestion services

### Utility Scripts

- **`rebuild-all.ps1`** - Rebuilds all services (use with caution)
- **`restart-ai-services.ps1`** - Restarts all AI-related services
- **`deploy.ps1`** - General deployment script with profiles

## Common Workflows

### Workflow 1: Deploy Code Changes

```powershell
# 1. Make code changes
# 2. Deploy with health check
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service" -WaitForHealthy

# 3. Verify
Invoke-RestMethod -Uri "http://localhost:8020/health"
```

### Workflow 2: Update Multiple Related Services

```powershell
# Deploy all related services at once
.\scripts\deploy-service.ps1 -ServiceName @(
    "ai-pattern-service",
    "ha-ai-agent-service"
) -WaitForHealthy
```

### Workflow 3: Emergency Restart

```powershell
# Quick restart without rebuild (fastest)
.\scripts\deploy-service.ps1 -ServiceName "data-api" -Action restart
```

### Workflow 4: Clean Rebuild

```powershell
# Clean rebuild (no cache)
.\scripts\deploy-service.ps1 -ServiceName "ai-pattern-service" -NoCache -WaitForHealthy
```

## Troubleshooting

### Service Not Found

**Error:** `❌ The following services were not found in docker-compose.yml`

**Solution:**
```powershell
# List available services
docker-compose config --services
```

### Build Fails

**Error:** `❌ Failed to build <service>`

**Solution:**
```powershell
# Check build logs
docker-compose build <service> --no-cache

# Check for syntax errors in Dockerfile
docker-compose config
```

### Service Not Healthy

**Error:** `⚠ Service did not become healthy within 120 seconds`

**Solution:**
```powershell
# Check service logs
docker-compose logs <service>

# Check service status
docker-compose ps <service>

# Check health endpoint manually
Invoke-RestMethod -Uri "http://localhost:<port>/health"
```

### Service Won't Start

**Error:** `❌ Failed to start <service>`

**Solution:**
```powershell
# Check logs for errors
docker-compose logs <service>

# Check if port is already in use
netstat -ano | findstr :<port>

# Check docker-compose configuration
docker-compose config <service>
```

## Best Practices

1. **Always use `-WaitForHealthy`** for production deployments
2. **Use `-CheckLogs`** to verify deployment success
3. **Use `-NoCache`** if you suspect build cache issues
4. **Deploy services in dependency order** (services that depend on others should be deployed after their dependencies)
5. **Test in development** before deploying to production

## Service Dependencies

Some services depend on others. Deploy in this order:

1. **Infrastructure services first:**
   - `influxdb`
   - `jaeger`

2. **Core services:**
   - `data-api`
   - `websocket-ingestion`

3. **Application services:**
   - `ai-pattern-service`
   - `ha-ai-agent-service`
   - `api-automation-edge`

4. **UI services:**
   - `health-dashboard`
   - `ai-automation-ui`

## Quick Reference

```powershell
# Deploy single service
.\scripts\deploy-service.ps1 -ServiceName "service-name"

# Deploy with health check
.\scripts\deploy-service.ps1 -ServiceName "service-name" -WaitForHealthy

# Quick restart
.\scripts\deploy-service.ps1 -ServiceName "service-name" -Action restart

# Clean rebuild
.\scripts\deploy-service.ps1 -ServiceName "service-name" -NoCache

# Deploy multiple
.\scripts\deploy-service.ps1 -ServiceName @("service1", "service2")

# Check status
docker-compose ps

# View logs
docker-compose logs -f service-name
```

---

**Last Updated:** January 16, 2026