# Review and Deploy: Code Not Deployed to Local Docker

**Date:** 2026-02-09  
**Scope:** Identify services/code not in docker-compose, review, and ensure local Docker stack is deployed.

## Review Summary

### Services in `docker-compose.yml`

All **45** service directories that have a `Dockerfile` under `services/` are already defined in the root `docker-compose.yml`:

- **Infrastructure:** influxdb, jaeger  
- **Core:** observability-dashboard, websocket-ingestion, admin-api, data-api, data-retention  
- **External data:** carbon-intensity, electricity-pricing, air-quality, weather-api, sports-api, calendar, smart-meter, energy-correlator  
- **UI:** health-dashboard, ai-automation-ui  
- **AI/ML:** ner-service, openai-service (from archive), openvino-service, rag-service, ml-service, ai-core-service, ha-ai-agent-service, proactive-agent-service, ai-code-executor, ai-training-service, ai-pattern-service, ai-query-service  
- **Automation:** yaml-validation-service, api-automation-edge, ai-automation-service-new, blueprint-index, blueprint-suggestion-service, rule-recommendation-ml, automation-miner, ha-setup-service  
- **Device:** device-intelligence-service, device-health-monitor, device-context-classifier, device-setup-assistant, device-database-client, device-recommender  
- **Test/Dev:** home-assistant-test, websocket-ingestion-test, automation-linter, activity-recognition, energy-forecasting, ha-simulator, model-prep  
- **Other:** log-aggregator  

Some services use **profiles** and only start when that profile is used:

- `production`: carbon-intensity, electricity-pricing, air-quality, calendar, smart-meter  
- `test`: home-assistant-test, websocket-ingestion-test  
- `development`: ha-simulator, model-prep  

### Code Not in Docker: `nlp-fine-tuning`

| Item | Details |
|------|---------|
| **Path** | `services/nlp-fine-tuning/` |
| **Purpose** | CLI/tooling for fine-tuning language models (OpenAI and PEFT/LoRA) on the Home Assistant Requests dataset. |
| **Why not in Docker** | No `Dockerfile`; intended as a run-on-demand or local training workflow, not a long-running API service. |
| **Recommendation** | No change required. To run in Docker later, add a Dockerfile and optional compose service (e.g. for batch jobs or a small API). |

No other service code under `services/` is missing from docker-compose.

## Deployment

- **Action:** Build and start the default local Docker stack (all services without a profile).
- **Command:** `docker-compose up -d --build` (from project root).
- **Optional:** Include production-tier services with  
  `docker-compose --profile production up -d --build`.

## Fix: Missing openai-service Dockerfile

The build failed initially because `services/archive/2025-q4/ai-automation-service/docker/openai-service.Dockerfile` was missing. Added:

- **docker/openai-service.Dockerfile** – Python 3.12-slim image with FastAPI, uvicorn, httpx.
- **docker/openai_service.py** – Minimal service: `GET /health` and `POST /chat/completions`. If `OPENAI_API_KEY` is set (e.g. from `infrastructure/env.ai-automation`), it proxies to OpenAI; otherwise returns stub `{"response": "[]"}` so ai-core-service can start and use its fallback suggestions.

## Status

- [x] Review: all deployable services are in docker-compose; only `nlp-fine-tuning` is not (by design).
- [x] Deploy: `docker-compose up -d` completed; all default-profile services are running (openai-service recreated and healthy).
