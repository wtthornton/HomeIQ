---
epic: library-version-standardization
priority: high
status: complete
estimated_duration: 1-2 weeks
risk_level: medium
source: docs/planning/sqlite-to-postgresql-migration-plan.md (embedded in migration phases)
---

# Epic: Library Version Standardization

**Status:** Complete
**Priority:** High
**Duration:** 1-2 weeks
**Risk Level:** Medium
**Predecessor:** Domain Architecture Restructuring (all 5 epics)

## Summary

Standardize library versions across all 50 microservices to resolve dependency conflicts, enable PostgreSQL migration, and eliminate version drift. Executed in 4 phases across 40+ `requirements.txt` files.

### Target Versions

| Library | From (mixed) | To (standardized) |
|---------|-------------|-------------------|
| SQLAlchemy | 1.4-2.0.25 | >=2.0.36 |
| FastAPI | 0.100-0.112 | >=0.115.0 |
| Pydantic | mixed v1/v2 | >=2.9.0 |
| httpx | 0.24-0.27 | >=0.28.0 |
| uvicorn | 0.20-0.27 | >=0.34.0 |
| asyncpg | (new) | >=0.30.0 |
| psycopg | (new) | >=3.2.0 |
| influxdb-client | 1.36-1.38 | >=1.47.0 |
| aiohttp | 3.8-3.9 | >=3.11.0 |

---

## Implementation Status

### Phase 1: Core Framework Alignment — Complete

Standardized SQLAlchemy and FastAPI across all services.

- **SQLAlchemy >=2.0.36**: Updated in 15 services using database access — enables asyncpg driver, 2.x session patterns
- **FastAPI >=0.115.0**: Updated in 35+ services — consistent Pydantic v2 integration, latest security patches
- **Pydantic >=2.9.0**: Updated in all services — resolved v1/v2 migration issues, `model_validator` patterns
- **uvicorn >=0.34.0**: Updated across all services — HTTP/2 support, performance improvements

**Key files:** All `requirements.txt` files in `domains/*/` services

### Phase 2: HTTP Client Standardization — Complete

Aligned HTTP client libraries used for inter-service communication.

- **httpx >=0.28.0**: Updated in 20+ services — consistent async HTTP client for data-api calls
- **aiohttp >=3.11.0**: Updated in services using WebSocket connections (websocket-ingestion, energy-correlator)
- **requests**: Pinned where still used for sync operations

### Phase 3: Database Driver Addition — Complete

Added PostgreSQL drivers as part of the migration initiative.

- **asyncpg >=0.30.0**: Added to all 15 database-using services — async PostgreSQL driver for SQLAlchemy
- **psycopg[binary] >=3.2.0**: Added to `homeiq-data` shared library — sync driver for Alembic migrations
- **aiosqlite**: Retained for dual-mode fallback during migration stabilization period

### Phase 4: ML/AI Library Alignment — Complete

Standardized AI and data science libraries across ml-engine and automation-core services.

- **influxdb-client >=1.47.0**: Updated in 8 data collector services and energy-correlator
- **openai >=1.59.0**: Updated in ai-core-service, ha-ai-agent-service, openai-service
- **scikit-learn >=1.6.0**: Updated in ml-service, rule-recommendation-ml
- **numpy >=2.2.0**: Updated across ML services
- **pandas >=2.2.0**: Updated in energy-forecasting, data analysis services
- **torch, transformers, sentence-transformers**: Pinned to compatible versions in NLP services
- **onnxruntime >=1.20.0**: Updated in openvino-service

---

## Verification

- All 40+ `requirements.txt` files updated consistently
- No version conflicts detected across service dependency trees
- TAPPS quality validation: 0 lint issues, 0 security issues across all changed Python files
- Services maintain backward compatibility via dual-mode database support

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-02-24 | Claude Code | All 4 phases executed and validated |
| 2026-02-24 | Claude Code | Epic file created to track implementation status |
