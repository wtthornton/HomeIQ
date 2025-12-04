# Deploy YAML Validation Changes to Local Docker

## Quick Deployment Commands

### Option 1: Use PowerShell Script (Recommended)

```powershell
.\scripts\deploy-yaml-validation-changes.ps1
```

### Option 2: Manual Deployment

Run these commands in sequence:

```powershell
# 1. Stop the services
docker-compose stop ai-automation-service ha-ai-agent-service ai-automation-ui

# 2. Rebuild the services with new changes
docker-compose build --no-cache ai-automation-service
docker-compose build --no-cache ha-ai-agent-service  
docker-compose build --no-cache ai-automation-ui

# 3. Start the services
docker-compose up -d ai-automation-service ha-ai-agent-service ai-automation-ui

# 4. Check status
docker-compose ps | Select-String -Pattern "(ai-automation-service|ha-ai-agent-service|ai-automation-ui)"

# 5. Watch logs
docker-compose logs -f ai-automation-service
```

## What's Being Deployed

### Services Updated:
1. **ai-automation-service** - New validation router endpoint
2. **ha-ai-agent-service** - New AI automation client and consolidated validation
3. **ai-automation-ui** - Updated self-correct button with validation

### Key Files Changed:
- `services/ai-automation-service/src/api/yaml_validation_router.py` (NEW)
- `services/ai-automation-service/src/main.py` (router registration)
- `services/ha-ai-agent-service/src/clients/ai_automation_client.py` (NEW)
- `services/ha-ai-agent-service/src/tools/ha_tools.py` (validation update)
- `services/ha-ai-agent-service/src/config.py` (new config)
- `services/ai-automation-ui/src/services/api.ts` (new validation method)
- `services/ai-automation-ui/src/pages/Deployed.tsx` (self-correct update)

## Verification

After deployment, verify everything works:

### Test Validation Endpoint
```powershell
curl -X POST http://localhost:8024/api/v1/yaml/validate `
  -H "Content-Type: application/json" `
  -d '{\"yaml\": \"alias: Test\ntrigger:\n  - platform: state\n    entity_id: light.test\naction:\n  - service: light.turn_on\", \"validate_entities\": false, \"validate_safety\": false}'
```

### Check Service Health
```powershell
# AI Automation Service
curl http://localhost:8024/health

# HA AI Agent Service  
curl http://localhost:8030/health

# Check UI
Start-Process "http://localhost:3001"
```

### View Logs
```powershell
# Watch all three services
docker-compose logs -f ai-automation-service ha-ai-agent-service ai-automation-ui

# Or individually
docker-compose logs -f ai-automation-service
docker-compose logs -f ha-ai-agent-service
docker-compose logs -f ai-automation-ui
```

## Troubleshooting

If services fail to start:
1. Check logs: `docker-compose logs <service-name>`
2. Verify dependencies are running: `docker-compose ps`
3. Check environment variables in `.env` file
4. Ensure ports 8024, 8030, and 3001 are not in use

For more details, see: `implementation/YAML_VALIDATION_DEPLOYMENT_GUIDE.md`

