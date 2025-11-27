# Story 39.10: Automation Service Foundation

## Overview

This is the foundation for a NEW `ai-automation-service` that will contain only automation-specific functionality:
- Suggestion generation
- YAML generation  
- Deployment endpoints
- Testing endpoints

## Current State

The existing `ai-automation-service` is monolithic and contains:
- Query processing (being moved to `ai-query-service`)
- Training (moved to `ai-training-service`)
- Pattern analysis (moved to `ai-pattern-service`)
- Suggestion generation (to be extracted here)
- YAML generation (to be extracted here)
- Deployment (to be extracted here)

## Endpoints to Extract

### Suggestion Generation
- **Router**: `services/ai-automation-service/src/api/suggestion_router.py`
- **Endpoints**:
  - `POST /api/suggestions/generate` - Generate suggestions from patterns
  - `GET /api/suggestions/list` - List suggestions
  - `GET /api/suggestions/usage/stats` - Usage statistics
  - `GET /api/suggestions/models/compare` - Model comparison
  - `POST /api/suggestions/refresh` - Manual refresh
  - `GET /api/suggestions/refresh/status` - Refresh status

### YAML Generation
- **Service**: `services/ai-automation-service/src/services/automation/yaml_generation_service.py`
- **Functions**:
  - `generate_automation_yaml()` - Main YAML generation
  - `pre_validate_suggestion_for_yaml()` - Pre-validation
  - `build_suggestion_specific_entity_mapping()` - Entity mapping

### Deployment
- **Router**: `services/ai-automation-service/src/api/deployment_router.py`
- **Endpoints**:
  - `POST /api/deploy/{suggestion_id}` - Deploy suggestion
  - `POST /api/deploy/batch` - Batch deploy
  - `GET /api/deploy/automations` - List deployed automations
  - `GET /api/deploy/automations/{automation_id}` - Get automation status
  - `POST /api/deploy/automations/{automation_id}/enable` - Enable automation
  - `POST /api/deploy/automations/{automation_id}/disable` - Disable automation
  - `POST /api/deploy/automations/{automation_id}/trigger` - Trigger automation
  - `GET /api/deploy/test-connection` - Test HA connection
  - `POST /api/deploy/{automation_id}/rollback` - Rollback automation
  - `GET /api/deploy/{automation_id}/versions` - Version history

## Dependencies

### Services
- `yaml_generation_service.py` - YAML generation logic
- `yaml_validator.py` - YAML validation
- `yaml_corrector.py` - YAML correction
- `deployer.py` - Deployment logic
- `safety_validator.py` - Safety validation

### Clients
- `HomeAssistantClient` - HA API integration
- `DataAPIClient` - Data API for device/entity info
- `OpenAIClient` - OpenAI API for YAML generation

### Database Models
- `Suggestion` - Suggestion model
- `AutomationVersion` - Version history for rollback

## Next Steps

1. Create service structure (config, database, main.py)
2. Extract suggestion router endpoints
3. Extract YAML generation service
4. Extract deployment router endpoints
5. Set up Docker configuration
6. Update docker-compose.yml
7. Create health router
8. Add tests

## Notes

- This service will run on Port 8021 (per PRD)
- Uses shared database (SQLite)
- Will communicate with other services via HTTP
- Full extraction will happen in subsequent stories

