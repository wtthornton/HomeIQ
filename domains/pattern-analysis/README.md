# pattern-analysis

Behavioral pattern detection and edge automation. Analyzes device usage patterns and synergies for automation opportunities.

## Services

| Service | Port | Role |
|---------|------|------|
| ai-pattern-service | 8034 | Pattern detection, synergy analysis |
| api-automation-edge | 8041 | Edge computing for API-driven automations |

## Depends On

core-platform (data-api), ml-engine (for pattern ML models)

## Depended On By

blueprints (patterns feed blueprint suggestions), automation-core (pattern-based automation)

## Compose

```bash
docker compose -f domains/pattern-analysis/compose.yml up -d
```
