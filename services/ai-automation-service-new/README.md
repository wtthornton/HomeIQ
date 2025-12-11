# AI Automation Service

**Epic 39, Story 39.10: Automation Service Foundation**

The AI Automation Service is a microservice extracted from `ai-automation-service` for independent scaling and maintainability. It handles suggestion generation, YAML generation, and deployment of automations to Home Assistant.

## Status

🚧 **Foundation Ready** - Service structure created, full implementation in progress

## Features

- **Suggestion Generation**: Generate automation suggestions from patterns
- **YAML Generation**: Generate Home Assistant automation YAML from suggestions
- **Deployment**: Deploy automations to Home Assistant with safety validation
- **Version Management**: Track automation versions and enable rollback

## Service Configuration

- **Port**: 8025 (Note: 8021 is used by device-setup-assistant)
- **Database**: Shared SQLite database at `/app/data/ai_automation.db`
- **Dependencies**: 
  - Data API (Port 8006)
  - Query Service (Port 8018)
  - Pattern Service (Port 8020)
  - Home Assistant (via HA_URL and HA_TOKEN)

## API Endpoints

### Health
- `GET /health` - Health check

### Suggestions
- `POST /api/suggestions/generate` - Generate suggestions
- `GET /api/suggestions/list` - List suggestions
- `GET /api/suggestions/usage/stats` - Usage statistics
- `POST /api/suggestions/refresh` - Manual refresh
- `GET /api/suggestions/refresh/status` - Refresh status

### Deployment
- `POST /api/deploy/{suggestion_id}` - Deploy suggestion
- `POST /api/deploy/batch` - Batch deploy
- `GET /api/deploy/automations` - List deployed automations
- `GET /api/deploy/automations/{automation_id}` - Get automation status
- `POST /api/deploy/automations/{automation_id}/enable` - Enable automation
- `POST /api/deploy/automations/{automation_id}/disable` - Disable automation
- `GET /api/deploy/test-connection` - Test HA connection
- `POST /api/deploy/{automation_id}/rollback` - Rollback automation
- `GET /api/deploy/{automation_id}/versions` - Version history

## Implementation Status

**Current**: Foundation service structure created with stub endpoints

**TODO (Story 39.10 completion)**:
- Migrate full suggestion generation logic from `ai-automation-service`
- Migrate YAML generation service
- Migrate deployment logic with safety validation
- Add authentication middleware
- Add rate limiting middleware
- Complete integration tests

## Development

```bash
# Run locally
cd services/ai-automation-service-new
uvicorn src.main:app --reload --port 8025

# Run tests
pytest tests/
```

## Docker

```bash
# Build
docker build -f services/ai-automation-service-new/Dockerfile -t ai-automation-service .

# Run
docker run -p 8025:8025 ai-automation-service
```

## Notes

- This service uses port 8025 instead of 8021 (which is used by device-setup-assistant)
- Full implementation migration is planned for Story 39.10 completion phase
- Service shares database with other AI services (training, pattern, query)
- Connection pooling is configured for optimal performance (max 20 connections per service)

