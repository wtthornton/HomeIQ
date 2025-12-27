# Epic 39: AI Automation Service Modularization Architecture

**Epic:** 39  
**Status:** ✅ **COMPLETE**  
**Date:** December 2025

## Overview

Epic 39 refactored the monolithic AI Automation Service into a modular microservices architecture, enabling independent scaling, improved maintainability, and optimized performance.

## Architecture

### Service Structure

The monolithic service has been split into four specialized services:

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                     │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ ai-query-    │  │ ai-pattern-  │  │ ai-training- │
│ service      │  │ service       │  │ service      │
│ (Port 8018)  │  │ (Port 8020)  │  │ (Port 8022)  │
│              │  │              │  │              │
│ - Ask AI     │  │ - Pattern    │  │ - Synthetic  │
│ - Conversa-  │  │   Detection   │  │   Data Gen   │
│   tional     │  │ - Synergy     │  │ - Model      │
│ - Entity     │  │ - Analysis    │  │   Training   │
│   Extraction │  │ - Scheduler   │  │ - Evaluation │
│ - Low        │  │ - Background  │  │ - Batch      │
│   Latency    │  │   Processing  │  │   Processing │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ ai-automation│  │ Shared       │  │ SQLite-based │
│ -service     │  │ SQLite DB    │  │ Cache        │
│ (Port 8025)  │  │ (Connection  │  │ (Correlation │
│              │  │ Pooling)     │  │ Cache)       │
│ - Suggestion │  │              │  │              │
│   Generation │  │              │  │              │
│ - YAML Gen   │  │              │  │              │
│ - Deployment │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Service Details

#### AI Query Service (Port 8018)
- **Purpose**: Low-latency query processing
- **Responsibilities**:
  - Natural language query processing
  - Entity extraction
  - Conversational flow
  - Clarification handling
- **Performance Target**: <500ms P95 latency
- **Status**: ✅ Operational

#### AI Pattern Service (Port 8020)
- **Purpose**: Pattern detection and analysis
- **Responsibilities**:
  - Pattern detection
  - Synergy analysis
  - Community pattern mining
  - Daily scheduled analysis
- **Status**: ✅ Operational

#### AI Training Service (Port 8022)
- **Purpose**: Model training and data generation
- **Responsibilities**:
  - Synthetic data generation
  - Model training (home type, soft prompts, GNN)
  - Model evaluation
  - Batch processing
- **Status**: ✅ Operational

#### AI Automation Service (Port 8025)
- **Purpose**: Automation generation and deployment
- **Responsibilities**:
  - Suggestion generation
  - YAML generation
  - Deployment to Home Assistant
  - Version management and rollback
- **Status**: 🚧 Foundation Ready (full implementation in progress)

## Shared Infrastructure

### Database

**Shared SQLite Database:**
- **Path**: `/app/data/ai_automation.db`
- **Connection Pooling**: 
  - Pool size: 10 per service
  - Max overflow: 5 per service
  - Total max: 15 per service (under 20 target)
- **Optimizations**:
  - WAL mode (Write-Ahead Logging)
  - 64MB cache size
  - 30s busy timeout
  - Foreign keys enabled

### Caching

**CorrelationCache (SQLite-based):**
- **Location**: `shared/correlation_cache.py`
- **Type**: Two-tier cache (in-memory LRU + SQLite persistence)
- **Shared**: Yes - accessible to all services
- **Target Hit Rate**: >80%
- **Memory Footprint**: <20MB

### Service Communication

**Pattern:**
- HTTP/REST communication
- Docker Compose service discovery
- Service URLs configured via environment variables

**Service URLs:**
- Data API: `http://data-api:8006`
- Query Service: `http://ai-query-service:8018`
- Pattern Service: `http://ai-pattern-service:8020`
- Training Service: `http://ai-training-service:8022`

## Performance Targets

- **Query Latency**: <500ms P95
- **Database Connections**: <20 per service
- **Cache Hit Rate**: >80%
- **Memory per Service**: <500MB
- **Test Coverage**: >80%

## Deployment

### Docker Compose

All services are orchestrated via Docker Compose:

```yaml
services:
  ai-query-service:
    ports:
      - "8018:8018"
    # ... configuration
  
  ai-pattern-service:
    ports:
      - "8020:8020"
    # ... configuration
  
  ai-training-service:
    ports:
      - "8022:8022"
    # ... configuration
  
  ai-automation-service:
    ports:
      - "8025:8025"
    # ... configuration
```

### Environment Variables

Each service requires:
- `DATABASE_URL`: SQLite database path
- `DATA_API_URL`: Data API service URL
- Service-specific configuration (HA_URL, OPENAI_API_KEY, etc.)

## Migration Path

### Phase 1: Training Service ✅
- Extracted training functionality
- Moved synthetic data generators
- Migrated model training scripts

### Phase 2: Pattern Service ✅
- Extracted pattern detection
- Migrated scheduler
- Moved learning services

### Phase 3: Query & Automation Split 🚧
- Query service foundation created
- Automation service foundation created
- Full implementation in progress

### Phase 4: Code Organization ✅
- Router modularization complete
- Service layer reorganization (foundation ready)
- Performance optimizations in place

## Benefits

1. **Independent Scaling**: Scale services based on load
2. **Improved Maintainability**: Smaller, focused codebases
3. **Performance Optimization**: Specialized optimization per service
4. **Reduced Complexity**: Break down large monolithic router
5. **Resource Efficiency**: Better resource allocation
6. **Development Velocity**: Faster development cycles
7. **Deployment Flexibility**: Deploy services independently

## Future Enhancements

- Complete automation service full implementation
- Add cache hit rate monitoring
- Profile and optimize hot paths
- Service layer reorganization (optional)
- Additional performance optimizations

---

**Last Updated:** December 2025  
**Related Documents:**
- Epic Document: `docs/prd/epic-39-ai-automation-service-modularization.md`
- Implementation Status: `implementation/EPIC_39_STATUS_ASSESSMENT.md`

