# AI Core Service

**Port:** 8018
**Technology:** Python 3.12+, FastAPI 0.123.x, httpx 0.28.x
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
- **Rate Limiting**: Sliding-window rate limiting per client and API key
- **Request ID Tracing**: Distributed tracing via X-Request-ID header

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
  "analysis_type": "pattern_detection|clustering|anomaly_detection|basic",
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
  "detection_type": "full|basic|quick"
}
```

### Suggestion Generation (Authenticated)
```
POST /suggestions
Headers:
  X-API-Key: <AI_CORE_API_KEY>
Body: {
  "context": {...},
  "suggestion_type": "automation_improvements|energy_optimization|comfort|security|convenience"
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENVINO_SERVICE_URL` | `http://openvino-service:8019` | OpenVINO service endpoint |
| `ML_SERVICE_URL` | `http://ml-service:8020` | ML service endpoint |
| `NER_SERVICE_URL` | `http://ner-service:8031` | NER service endpoint |
| `OPENAI_SERVICE_URL` | `http://openai-service:8020` | OpenAI service endpoint |
| `AI_CORE_API_KEY` | _(required)_ | API key used for all non-health requests |
| `AI_CORE_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | Comma-separated CORS allow-list |
| `AI_CORE_RATE_LIMIT` | `60` | Requests per window allowed per API key + client |
| `AI_CORE_RATE_LIMIT_WINDOW` | `60` | Rate-limit window in seconds |
| `AI_CORE_LLM_TIMEOUT` | `60` | Timeout in seconds for OpenAI/LLM calls |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Architecture

```
+---------------------+
|   AI Core Service   | <- Single orchestration layer
|     (Port 8018)     |
+----------+----------+
           |
     +-----+------+------+------+
     |     |      |      |      |
     v     v      v      v      v
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
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

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
- FastAPI 0.123.x (web framework)
- uvicorn[standard] 0.32.x (ASGI server)
- httpx 0.28.x (async HTTP client)
- pydantic 2.12.x (data validation)
- tenacity 9.x (retry/circuit breaker)

### Development
- pytest 9.x (testing framework)
- pytest-asyncio 0.25.x (async test support)

## Related Services

- [OpenVINO Service](../openvino-service/README.md) - Model inference
- [ML Service](../ml-service/README.md) - Classical ML
- [AI Automation Service](../ai-automation-service/README.md) - Consumer of AI Core

## Performance

- **Latency**: 50-200ms (depending on underlying AI service)
- **Throughput**: Varies based on AI operation complexity
- **Circuit Breaker**: 5 failures -> open circuit for 30s
- **Connection Pool**: 50 max connections, 20 max keepalive

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
- Check managed service health: `curl http://localhost:8018/health`
- Review circuit breaker state via `/services/status`
- Check service logs for routing decisions

## Related Documentation

- [OpenVINO Service](../openvino-service/README.md) - Model inference
- [ML Service](../ml-service/README.md) - Classical ML
- [AI Automation Service](../ai-automation-service/README.md) - Consumer
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Version History

### 2.3 (February 2026)
- Fixed prompt injection vulnerability in suggestion generation
- Implemented circuit breaker pattern (previously only retry logic)
- Parallelized pattern detection calls with asyncio.gather
- Added analysis_type routing logic
- Added degraded mode startup (no longer fails if some services are down)
- Removed internal service URLs from status endpoint
- Added request ID tracing middleware
- Added request body size limit middleware
- Migrated global state to app.state
- Added structured JSON logging
- Fixed rate limiter memory leak with stale entry eviction
- Separated test dependencies from production requirements
- Added comprehensive unit tests with mocking

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

**Last Updated:** February 6, 2026
**Version:** 2.3
**Status:** Production Ready
**Port:** 8018
**Managed Services:** OpenVINO (8019), ML (8020), NER (8031), OpenAI
