# blueprints

Blueprint discovery, indexing, suggestion, and ML-powered recommendations. Crawls community automations and suggests relevant blueprints based on user devices.

## Services

| Service | Port | Role |
|---------|------|------|
| blueprint-index | 8038 | Blueprint metadata indexing and search |
| blueprint-suggestion-service | 8039 | Automation suggestions based on user devices |
| rule-recommendation-ml | 8040 | ML-powered automation recommendations |
| automation-miner | 8029 | Community automation crawler (Discourse/GitHub) |

## Depends On

core-platform (data-api), ml-engine (ai-core-service for ML inference)

## Depended On By

automation-core (blueprint suggestions feed into automation generation)

## Compose

```bash
docker compose -f domains/blueprints/compose.yml up -d
```
