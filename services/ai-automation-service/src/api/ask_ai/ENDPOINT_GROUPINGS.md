# Ask AI Router Endpoint Groupings

**Epic 39, Story 39.13: Router Modularization**

## Current Endpoints in ask_ai_router.py (8,674 lines)

### 1. Query Processing (3 endpoints)
- `POST /query` - Main query processing endpoint
- `POST /query/{query_id}/refine` - Refine query results
- `GET /query/{query_id}/suggestions` - Get suggestions for query

### 2. Clarification (1 endpoint)
- `POST /clarify` - Provide clarification answers

### 3. Suggestion Actions (2 endpoints)
- `POST /query/{query_id}/suggestions/{suggestion_id}/test` - Test suggestion
- `POST /query/{query_id}/suggestions/{suggestion_id}/approve` - Approve suggestion

### 4. Model Comparison (2 endpoints)
- `GET /model-comparison/metrics` - Get model comparison metrics
- `GET /model-comparison/summary` - Get model comparison summary

### 5. Analytics & Metrics (3 endpoints)
- `GET /analytics/reverse-engineering` - Reverse engineering analytics
- `GET /pattern-synergy/metrics` - Pattern synergy metrics
- `GET /failure-stats` - Failure statistics

### 6. YAML Processing (1 endpoint)
- `POST /reverse-engineer-yaml` - Reverse engineer and self-correct YAML

### 7. Entity Search (1 endpoint)
- `GET /entities/search` - Search entities

### 8. Alias Management (3 endpoints)
- `POST /aliases` - Create alias
- `DELETE /aliases/{alias}` - Delete alias
- `GET /aliases` - Get all aliases

## Modularization Strategy

Given the complexity and size, we'll use an incremental approach:

### Phase 1: Extract Low-Hanging Fruit (Low Coupling)
1. Model Comparison Router (independent)
2. Alias Management Router (independent)
3. Analytics/Metrics Router (mostly independent)

### Phase 2: Extract Medium Complexity
4. Entity Search Router (simple dependency)
5. YAML Processing Router (moderate dependency)

### Phase 3: Extract Core Functionality (High Coupling)
6. Query Processing Router (core, many dependencies)
7. Clarification Router (core, many dependencies)
8. Suggestion Actions Router (core, many dependencies)

## Implementation Order

1. ✅ Create common dependencies module
2. Extract Model Comparison Router (simplest)
3. Extract Alias Management Router
4. Extract Analytics/Metrics Router
5. Extract Entity Search Router
6. Extract YAML Processing Router
7. Extract Query/Clarification/Suggestion routers (complex, requires careful refactoring)

