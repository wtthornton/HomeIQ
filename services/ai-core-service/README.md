# AI Core Service

**Port:** 8018
**Technology:** Python 3.11+, FastAPI 0.121, aiohttp 3.13
**Purpose:** Orchestrator for containerized AI models
**Status:** Production Ready

## Overview

The AI Core Service acts as the central orchestrator for all AI/ML capabilities in the HomeIQ platform. It coordinates requests across multiple specialized AI services and provides circuit breaker patterns, fallback mechanisms, and unified business logic.

## Key Features

- **Service Orchestration**: Routes requests to appropriate AI services (OpenVINO, ML, NER, OpenAI)
- **Circuit Breaker Patterns**: Prevents cascading failures across AI services
- **Fallback Mechanisms**: Graceful degradation when AI services are unavailable
- **Unified API**: Single endpoint for all AI operations
- **Request Routing**: Intelligent routing based on analysis type and requirements

## Managed Services

The AI Core Service orchestrates the following containerized AI services:

1. **OpenVINO Service** (Port 8019) - Optimized model inference
2. **ML Service** (Port 8020) - Classical machine learning
3. **NER Service** (Port 8031) - Named entity recognition
4. **OpenAI Service** - GPT-based operations

## API Endpoints

### Health Check
```
GET /health
```

### Analysis (Authenticated)
```
POST /analyze
Headers:
  X-API-Key: <AI_CORE_API_KEY>
Body: {
  "data": [...],
  "analysis_type": "pattern_detection|clustering|anomaly|...",
  "options": {}
}
```

### Pattern Detection (Authenticated)
```
POST /patterns
Headers:
  X-API-Key: <AI_CORE_API_KEY>
Body: {
  "patterns": [...],
  "detection_type": "full|partial|..."
}
```

### Suggestion Generation (Authenticated)
```
POST /suggestions
Headers:
  X-API-Key: <AI_CORE_API_KEY>
Body: {
  "context": {...},
  "suggestion_type": "automation|optimization|..."
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENVINO_SERVICE_URL` | `http://openvino-service:8019` | OpenVINO service endpoint |
| `ML_SERVICE_URL` | `http://ml-service:8020` | ML service endpoint |
| `NER_SERVICE_URL` | `http://ner-service:8031` | NER service endpoint |
| `AI_CORE_API_KEY` | _(required)_ | API key used for all non-health requests |
| `AI_CORE_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Comma-separated CORS allow-list |
| `AI_CORE_RATE_LIMIT` | `60` | Requests per window allowed per API key + client |
| `AI_CORE_RATE_LIMIT_WINDOW` | `60` | Rate-limit window in seconds |
| `OPENAI_SERVICE_URL` | `http://openai-service:8020` | OpenAI service endpoint |

## Architecture

```
┌─────────────────────┐
│   AI Core Service   │ ← Single orchestration layer
│     (Port 8018)     │
└──────────┬──────────┘
           │
     ┌─────┼──────┬──────┬──────┐
     │     │      │      │      │
     ▼     ▼      ▼      ▼      ▼
  OpenVINO ML   NER  OpenAI  [Others]
  Service Service      Service
```

## Development

### Running Locally
```bash
cd services/ai-core-service

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AI_CORE_API_KEY=<your-key>

# Start service
uvicorn src.main:app --reload --port 8018
```

### Testing
```bash
# Health check
  curl http://localhost:8018/health

# Run analysis
  curl -X POST http://localhost:8018/analyze \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $AI_CORE_API_KEY" \
  -d '{"data": [...], "analysis_type": "pattern_detection"}'
```

## Dependencies

### Core
- FastAPI 0.121+ (web framework)
- uvicorn[standard] 0.38+ (ASGI server)
- aiohttp 3.13+ (async HTTP client)
- pydantic 2.12+ (data validation)
- pydantic-settings 2.12+ (settings management)

## Related Services

- [OpenVINO Service](../openvino-service/README.md) - Model inference
- [ML Service](../ml-service/README.md) - Classical ML
- [AI Automation Service](../ai-automation-service/README.md) - Consumer of AI Core

## Performance

- **Latency**: 50-200ms (depending on underlying AI service)
- **Throughput**: Varies based on AI operation complexity
- **Circuit Breaker**: 5 failures → open circuit for 30s

## Monitoring

Metrics exposed for:
- Service orchestration latency
- AI service availability
- Circuit breaker state
- Request routing decisions

## Troubleshooting

### Service Orchestration Issues

**Symptoms:**
- Requests timing out
- Circuit breaker open

**Solutions:**
- Check managed service health: `curl http://openvino-service:8019/health`
- Review circuit breaker state
- Check service logs for routing decisions

## Related Documentation

- [OpenVINO Service](../openvino-service/README.md) - Model inference
- [ML Service](../ml-service/README.md) - Classical ML
- [AI Automation Service](../ai-automation-service/README.md) - Consumer
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Version History

### 2.2 (November 15, 2025)
- Added API key authentication and rate limiting
- Hardened CORS defaults and sanitized error responses
- NER service port moved to 8031 to prevent conflicts
- Added graceful HTTP client shutdown

### 2.1 (November 15, 2025)
- Documentation verified for 2025 standards
- Service orchestration patterns documented
- Circuit breaker configuration reference
- Managed services comprehensive guide

### 2.0 (October 2025)
- AI service orchestration
- Circuit breaker patterns
- Fallback mechanisms
- Unified API for all AI operations

### 1.0 (Initial Release)
- Basic AI service routing
- Request coordination

---

**Last Updated:** November 15, 2025
**Version:** 2.2
**Status:** Production Ready ✅
**Port:** 8018
**Managed Services:** OpenVINO (8019), ML (8020), NER (8031), OpenAI (8020)
