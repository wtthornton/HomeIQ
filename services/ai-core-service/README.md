# AI Core Service

**Port:** 8021
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
3. **NER Service** - Named entity recognition
4. **OpenAI Service** - GPT-based operations

## API Endpoints

### Health Check
```
GET /health
```

### Analysis
```
POST /analyze
Body: {
  "data": [...],
  "analysis_type": "pattern_detection|clustering|anomaly|...",
  "options": {}
}
```

### Pattern Detection
```
POST /detect-patterns
Body: {
  "patterns": [...],
  "detection_type": "full|partial|..."
}
```

### Suggestion Generation
```
POST /suggestions
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
| `NER_SERVICE_URL` | `http://ner-service:8019` | NER service endpoint |
| `OPENAI_SERVICE_URL` | `http://openai-service:8020` | OpenAI service endpoint |

## Architecture

```
┌─────────────────────┐
│   AI Core Service   │ ← Single orchestration layer
│     (Port 8021)     │
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
docker-compose up --build
```

### Testing
```bash
# Health check
curl http://localhost:8021/health

# Run analysis
curl -X POST http://localhost:8021/analyze \
  -H "Content-Type: application/json" \
  -d '{"data": [...], "analysis_type": "pattern_detection"}'
```

## Dependencies

- FastAPI (web framework)
- aiohttp (async HTTP client)
- pydantic (data validation)

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
