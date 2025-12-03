# Proactive Agent Service

**Epic:** AI-21 - Proactive Conversational Agent Service  
**Port:** 8031  
**Status:** ✅ Production Ready (Completed December 2025)

## Overview

The Proactive Agent Service generates context-aware automation suggestions by analyzing weather, sports, energy, and historical patterns. It communicates with the HA AI Agent Service to create intelligent, proactive automation recommendations.

## Features

- **Context Analysis:** Weather, sports, energy, and historical pattern analysis
- **Smart Prompt Generation:** Context-aware prompt building for HA AI Agent
- **Agent-to-Agent Communication:** HTTP calls to HA AI Agent Service
- **Scheduled Jobs:** 3 AM daily batch job for proactive suggestions
- **Suggestion Management:** Storage and tracking of generated suggestions

## API Endpoints

### Health Check
- `GET /health` - Health check endpoint

### Suggestions Management
- `GET /api/v1/suggestions` - List suggestions (filters: status, context_type, limit, offset)
- `GET /api/v1/suggestions/{id}` - Get suggestion by ID
- `PATCH /api/v1/suggestions/{id}` - Update suggestion status
- `DELETE /api/v1/suggestions/{id}` - Delete suggestion
- `GET /api/v1/suggestions/stats/summary` - Get suggestion statistics
- `POST /api/v1/suggestions/trigger` - Manually trigger suggestion generation

## Configuration

Environment variables:
- `PROACTIVE_AGENT_ALLOWED_ORIGINS` - Comma-delimited CORS origins
- `HA_AI_AGENT_URL` - HA AI Agent Service URL (default: http://ha-ai-agent-service:8030)
- `WEATHER_API_URL` - Weather API service URL (default: http://weather-api:8009)
- `SPORTS_DATA_URL` - Sports Data service URL (default: http://sports-data:8005)
- `CARBON_INTENSITY_URL` - Carbon Intensity service URL (default: http://carbon-intensity:8010)
- `DATA_API_URL` - Data API service URL (default: http://data-api:8006)
- `DATABASE_URL` - SQLite database URL
- `SCHEDULER_ENABLED` - Enable scheduler (default: true)
- `SCHEDULER_TIME` - Daily batch job time (default: 03:00)
- `OPENAI_API_KEY` - OpenAI API key for prompt generation

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run service
uvicorn src.main:app --host 0.0.0.0 --port 8031
```

## Docker

```bash
# Build image
docker build -f services/proactive-agent-service/Dockerfile -t proactive-agent-service .

# Run container
docker run -p 8031:8031 proactive-agent-service
```

