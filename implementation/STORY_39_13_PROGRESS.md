# Story 39.13: Router Modularization - Progress

**Epic 39, Story 39.13**  
**Status:** In Progress

## Completed

### ✅ Phase 1: Common Router Utilities
- Created `api/common/` module
- Created `api/common/dependencies.py` with shared dependency injection functions
- Centralized `get_ha_client()` and `get_openai_client()` functions
- Created `api/common/__init__.py` for easy imports

### ✅ Phase 2: Router Structure
- Created `api/ask_ai/` directory for modular Ask AI routers
- Created endpoint groupings documentation (`ENDPOINT_GROUPINGS.md`)
- Identified 16 endpoints in `ask_ai_router.py` (8,674 lines)

### ✅ Phase 3: First Router Extraction
- Extracted Model Comparison Router (`api/ask_ai/model_comparison_router.py`)
  - `GET /model-comparison/metrics`
  - `GET /model-comparison/summary`
- Router is independent, uses only database dependencies

## Next Steps

### Immediate
1. Update `main.py` to include model_comparison_router
2. Remove model comparison endpoints from original `ask_ai_router.py`
3. Test that endpoints still work

### Future Extractions (Prioritized)
1. **Alias Management Router** - Simple, independent (3 endpoints)
2. **Analytics/Metrics Router** - Mostly independent (3 endpoints)
3. **Entity Search Router** - Simple dependency (1 endpoint)
4. **YAML Processing Router** - Moderate dependency (1 endpoint)
5. **Query/Clarification/Suggestion routers** - Complex, high coupling (requires careful refactoring)

## Notes

- Using incremental approach to minimize risk
- Each extraction is tested before moving to next
- Common dependencies module allows all routers to share client instances
- Original router remains functional during transition

