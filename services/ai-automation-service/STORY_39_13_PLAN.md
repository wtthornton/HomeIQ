# Story 39.13: Router Modularization Plan

**Epic 39, Story 39.13**  
**Status:** In Progress

## Overview

Split large routers into focused modules, extract common router logic, and improve code organization without changing functionality.

## Analysis

### Large Routers Identified

1. **`ask_ai_router.py`** - 8,674 lines ⚠️ CRITICAL
   - Query processing endpoints
   - Clarification endpoints
   - Model comparison endpoints
   - YAML reverse engineering
   - Suggestion approval
   - Metrics tracking

2. **`suggestion_router.py`** - 1,479 lines
   - Suggestion CRUD operations
   - Could benefit from split

3. **`conversational_router.py`** - 1,440 lines
   - Conversational suggestion generation
   - YAML refinement
   - Could benefit from split

## Modularization Strategy

### Phase 1: Extract Common Router Utilities

Create `api/common/` module with:
- `dependencies.py` - Shared dependency injection functions
- `error_handlers.py` - Common error handling utilities
- `validators.py` - Common request/response validators
- `middleware.py` - Common middleware (if needed)

### Phase 2: Split `ask_ai_router.py`

Split into focused routers:

```
api/ask_ai/
├── __init__.py
├── query_router.py          # POST /query, GET /query/{id}
├── clarification_router.py  # POST /clarify, GET /clarify/{session_id}
├── suggestion_router.py     # GET /query/{id}/suggestions, POST /approve
├── model_comparison_router.py  # GET /model-comparison/*
├── yaml_router.py           # POST /reverse-engineer-yaml
├── models.py                # Shared Pydantic models
└── dependencies.py          # Router-specific dependencies
```

### Phase 3: Review Other Routers

After `ask_ai_router` is split, review:
- `suggestion_router.py` - May need split
- `conversational_router.py` - May need split

## Acceptance Criteria

- ✅ Large routers split into modules
- ✅ Code organization improved
- ✅ No functionality changes
- ✅ Tests passing
- ✅ All endpoints still accessible

## Implementation Steps

1. Create common router utilities module
2. Extract shared dependencies and error handlers
3. Split `ask_ai_router.py` into focused modules
4. Update main.py to include new routers
5. Verify all endpoints still work
6. Run tests

