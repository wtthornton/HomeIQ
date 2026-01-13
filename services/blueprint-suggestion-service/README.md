# Blueprint Suggestion Service

Matches Home Assistant Blueprints from the database against available devices, scores them using a 2025 scoring pattern, and provides multiple suggestions per blueprint.

## Features

- Matches blueprints to available devices
- Generates 3-5 suggestions per blueprint (different device combinations)
- Scores suggestions using 2025 pattern (DeviceMatcher + enhancements)
- Provides filtered suggestions API
- Tracks suggestion acceptance/decline status
- Integrates with Agent tab for blueprint-based conversations

## API Endpoints

- `GET /api/blueprint-suggestions/suggestions` - Get all suggestions with filters
- `POST /api/blueprint-suggestions/{id}/accept` - Accept a suggestion
- `POST /api/blueprint-suggestions/{id}/decline` - Decline a suggestion
- `GET /api/blueprint-suggestions/stats` - Get statistics

## Configuration

Environment variables:
- `BLUEPRINT_INDEX_URL` - URL of blueprint-index service (default: http://blueprint-index:8031)
- `DATA_API_URL` - URL of data-api service (default: http://data-api:8006)
- `AI_PATTERN_SERVICE_URL` - URL of ai-pattern-service (default: http://ai-pattern-service:8029)
- `DATABASE_URL` - Database connection string (default: sqlite+aiosqlite:///data/blueprint_suggestions.db)

## Running

```bash
# Development
uvicorn src.main:app --reload --port 8032

# Docker
docker-compose up blueprint-suggestion-service
```
