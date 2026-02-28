# Environment Variables

**Service:** HA AI Agent Service  
**Last Updated:** February 2026

This document describes all environment variables used by the HA AI Agent Service. All variables are optional and have defaults unless marked as **Required**.

## Configuration

The service uses Pydantic Settings to load configuration from environment variables. Variables can be set in:
- Environment variables
- `.env` file in the service directory
- Docker environment variables
- docker-compose environment section

## Service Configuration

### `SERVICE_NAME`
- **Type:** String
- **Default:** `ha-ai-agent-service`
- **Description:** Service name for identification
- **Required:** No

### `SERVICE_PORT`
- **Type:** Integer
- **Default:** `8030`
- **Description:** Port number for the service
- **Required:** No

## Home Assistant Configuration

### `HA_URL` ⚠️ **Required for Production**
- **Type:** String (URL)
- **Default:** `http://homeassistant:8123`
- **Description:** Home Assistant base URL
- **Example:** `http://192.168.1.86:8123` or `http://homeassistant:8123` (Docker network)
- **Required:** Yes (for production)

### `HA_TOKEN` ⚠️ **Required**
- **Type:** String
- **Default:** `""` (empty)
- **Description:** Home Assistant long-lived access token
- **Example:** `eyJ0eXAiOiJKV1QiLCJhbGc...`
- **Required:** Yes
- **Security:** Store securely, never commit to git

### `HA_TIMEOUT`
- **Type:** Integer (seconds)
- **Default:** `10`
- **Description:** Request timeout for Home Assistant API calls
- **Required:** No

### `HA_MAX_RETRIES`
- **Type:** Integer
- **Default:** `3`
- **Description:** Maximum retry attempts for Home Assistant API calls
- **Required:** No

## Data API Configuration

### `DATA_API_URL`
- **Type:** String (URL)
- **Default:** `http://data-api:8006`
- **Description:** Data API service URL for entity queries
- **Example:** `http://data-api:8006` (Docker network) or `http://localhost:8006` (local)
- **Required:** No (if Data API is available)

### `DATA_API_KEY`
- **Type:** String (SecretStr)
- **Default:** `None`
- **Description:** Bearer token for Data API authentication. When set, all requests to Data API include `Authorization: Bearer <key>` header.
- **Example:** Uses shared `API_KEY` from `.env` via `DATA_API_KEY=${API_KEY:-}`
- **Required:** Yes (if Data API requires authentication)
- **Security:** Store securely, never commit to git

## AI Automation Service Configuration

### `AI_AUTOMATION_SERVICE_URL`
- **Type:** String (URL)
- **Default:** `http://ai-automation-service-new:8036`
- **Description:** AI Automation Service URL for Hybrid Flow automation generation
- **Required:** No

### `AI_AUTOMATION_API_KEY`
- **Type:** String (SecretStr)
- **Default:** `None`
- **Description:** API key for AI Automation Service (required for patterns/synergies endpoints)
- **Required:** No
- **Security:** Store securely, never commit to git

### `USE_HYBRID_FLOW`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Use Hybrid Flow (template-based) for automation generation. Preferred path for better YAML quality.
- **Required:** No

## YAML Validation Service Configuration

### `YAML_VALIDATION_SERVICE_URL`
- **Type:** String (URL)
- **Default:** `http://yaml-validation-service:8037`
- **Description:** YAML Validation Service URL for comprehensive YAML validation (Epic 51)
- **Required:** No

### `YAML_VALIDATION_API_KEY`
- **Type:** String (SecretStr)
- **Default:** `None`
- **Description:** API key for YAML Validation Service
- **Required:** No

## Device Intelligence Service Configuration

### `DEVICE_INTELLIGENCE_URL`
- **Type:** String (URL)
- **Default:** `http://device-intelligence-service:8028`
- **Description:** Device Intelligence Service URL for capability patterns
- **Example:** `http://device-intelligence-service:8028` (Docker network)
- **Required:** No (service can operate without it)

### `DEVICE_INTELLIGENCE_ENABLED`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable/disable Device Intelligence Service integration
- **Required:** No

## OpenAI Configuration

### `OPENAI_API_KEY` ⚠️ **Required for Chat Features**
- **Type:** String
- **Default:** `None`
- **Description:** OpenAI API key for GPT-5.2-Codex / GPT-5.2
- **Example:** `sk-proj-...`
- **Required:** Yes (for chat functionality)
- **Security:** Store securely, never commit to git

### `OPENAI_MODEL`
- **Type:** String
- **Default:** `gpt-5.2-codex`
- **Description:** OpenAI model for chat and YAML generation (reasoning model)
- **Options:** `gpt-5.2-codex` (recommended), `gpt-5.2`, `gpt-5-mini` (cost)
- **Required:** No
- **Recommendation:** Use `gpt-5.2-codex` for best quality; `gpt-5-mini` for lower cost

### `OPENAI_MAX_TOKENS`
- **Type:** Integer
- **Default:** `16384`
- **Description:** Maximum completion tokens (includes reasoning tokens — GPT-5.2-Codex needs headroom for thinking + output)
- **Range:** 1-65536 (model-dependent)
- **Required:** No

### `OPENAI_TEMPERATURE`
- **Type:** Float
- **Default:** `1.0`
- **Description:** Temperature for OpenAI responses. Reasoning models work best at 1.0; reasoning handles consistency.
- **Range:** 0.0-2.0
- **Required:** No
- **Note:** Reasoning models (GPT-5.2-Codex) should use 1.0; non-reasoning models use 0.0-0.7

### `OPENAI_REASONING_EFFORT`
- **Type:** String
- **Default:** `high`
- **Description:** Reasoning effort for GPT-5.2-Codex. Higher = better quality, more tokens.
- **Options:** `low`, `medium`, `high`, `xhigh`
- **Required:** No

### `OPENAI_TIMEOUT`
- **Type:** Integer (seconds)
- **Default:** `90`
- **Description:** OpenAI API timeout (reasoning models need more time than standard models)
- **Required:** No

### `OPENAI_MAX_RETRIES`
- **Type:** Integer
- **Default:** `3`
- **Description:** Maximum retry attempts for OpenAI API calls
- **Required:** No

## Database Configuration

### `DATABASE_URL`
- **Type:** String (SQLAlchemy URL)
- **Default:** `postgresql+asyncpg:///./data/ha_ai_agent.db`
- **Description:** PostgreSQL database URL for context cache and conversations
- **Example:** `postgresql+asyncpg:///./data/ha_ai_agent.db`
- **Required:** No
- **Note:** Database directory will be created automatically

### `CONVERSATION_TTL_DAYS`
- **Type:** Integer (days)
- **Default:** `30`
- **Description:** Time-to-live for conversations (auto-deleted after this period)
- **Required:** No

## Context Cache Configuration

### `ENTITY_SUMMARY_CACHE_TTL`
- **Type:** Integer (seconds)
- **Default:** `300` (5 minutes)
- **Description:** TTL for entity summary cache
- **Required:** No

### `AREAS_CACHE_TTL`
- **Type:** Integer (seconds)
- **Default:** `600` (10 minutes)
- **Description:** TTL for areas list cache
- **Required:** No

### `SERVICES_CACHE_TTL`
- **Type:** Integer (seconds)
- **Default:** `600` (10 minutes)
- **Description:** TTL for services summary cache
- **Required:** No

### `CAPABILITY_PATTERNS_CACHE_TTL`
- **Type:** Integer (seconds)
- **Default:** `900` (15 minutes)
- **Description:** TTL for capability patterns cache
- **Required:** No

### `SUN_INFO_CACHE_TTL`
- **Type:** Integer (seconds)
- **Default:** `3600` (1 hour)
- **Description:** TTL for sun information cache
- **Required:** No

## Token Budget Configuration

### `MAX_CONTEXT_TOKENS`
- **Type:** Integer
- **Default:** `1500`
- **Description:** Maximum tokens for initial context injection
- **Required:** No
- **Note:** Used to limit context size for token budget management

## Logging Configuration

### `LOG_LEVEL`
- **Type:** String
- **Default:** `INFO`
- **Description:** Logging level
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Required:** No

## CORS Configuration

### `HA_AI_AGENT_ALLOWED_ORIGINS`
- **Type:** String (comma-separated)
- **Default:** `http://localhost:3000,http://localhost:3001`
- **Description:** Allowed CORS origins for API requests
- **Example:** `http://localhost:3000,http://localhost:3001,https://example.com`
- **Required:** No
- **Note:** In production, set to your actual frontend URLs

## Example .env File

```bash
# Home Assistant Configuration
HA_URL=http://homeassistant:8123
HA_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGc...

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-5.2-codex

# Data API Authentication
API_KEY=your-shared-api-key  # Used by DATA_API_KEY

# Service Configuration
LOG_LEVEL=INFO
SERVICE_PORT=8030

# Database Configuration
DATABASE_URL=postgresql+asyncpg:///./data/ha_ai_agent.db
CONVERSATION_TTL_DAYS=30

# CORS Configuration
HA_AI_AGENT_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

## Docker Compose Example

```yaml
services:
  ha-ai-agent-service:
    environment:
      - HA_URL=http://homeassistant:8123
      - HA_TOKEN=${HA_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=gpt-5.2-codex
      - DATA_API_URL=http://data-api:8006
      - DATA_API_KEY=${API_KEY:-}
      - AI_AUTOMATION_SERVICE_URL=http://ai-automation-service-new:8036
      - YAML_VALIDATION_SERVICE_URL=http://yaml-validation-service:8037
      - DEVICE_INTELLIGENCE_URL=http://device-intelligence-service:8028
      - LOG_LEVEL=INFO
      - DATABASE_URL=postgresql+asyncpg:///./data/ha_ai_agent.db
```

## Security Notes

⚠️ **Never commit sensitive values to git:**
- `HA_TOKEN` - Home Assistant access token
- `OPENAI_API_KEY` - OpenAI API key
- `DATA_API_KEY` / `API_KEY` - Data API Bearer token
- `AI_AUTOMATION_API_KEY` - AI Automation Service key
- `YAML_VALIDATION_API_KEY` - YAML Validation Service key

✅ **Best Practices:**
- Use environment variables or secrets management
- Use `.env` file with `.gitignore`
- Use Docker secrets for production
- Rotate keys periodically

## Related Documentation

- [Deployment Guide](./DEPLOYMENT.md)
- [Security Documentation](./SECURITY.md)
- [Configuration Source](../src/config.py)

