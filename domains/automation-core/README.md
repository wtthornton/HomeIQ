# automation-core

Core automation engine — NL-to-YAML generation, validation, and deployment. Both the CLI path (ai-automation-service-new) and GUI path (ha-ai-agent-service).

## Services

| Service | Port | Role |
|---------|------|------|
| ha-ai-agent-service | 8030 | HA AI agent — context building, entity resolution, GUI automation |
| ai-automation-service-new | 8036 | Core automation engine — NL to YAML (CLI path) |
| ai-query-service | 8035 | Natural language query interface |
| automation-linter | 8016 | YAML validation and linting |
| yaml-validation-service | 8037 | Unified schema/entity/service validation |
| ai-code-executor | — | Safe code execution sandbox |
| automation-trace-service | 8044 | HA automation trace + logbook ingestion |

## Depends On

core-platform (data-api), ml-engine (AI inference via ai-core-service)

## Depended On By

frontends (display automation results)

## Compose

```bash
docker compose -f domains/automation-core/compose.yml up -d
```
