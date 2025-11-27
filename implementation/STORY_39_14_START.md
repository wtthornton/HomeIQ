# Story 39.14: Service Layer Reorganization - Started

**Epic 39, Story 39.14**  
**Status:** In Progress

## Summary

Starting service layer reorganization to improve maintainability by organizing services by domain, improving dependency injection, and extracting background workers.

## Current State Analysis

### Services Directory Structure
- Mixed organization: Some domains exist (automation/, clarification/, entity/) but many services are at top level
- 50+ service files in various locations
- Background workers embedded in scheduler module

### Key Findings
1. **Domain directories exist but incomplete**:
   - `automation/`, `clarification/`, `conversation/`, `entity/`, `learning/`, `rag/` - Good structure
   - Many services still at top level need to be organized

2. **Background workers**:
   - Scheduler in `src/scheduler/`
   - Daily analysis job runs at 3 AM
   - Needs extraction to workers/ module

3. **Dependency injection**:
   - Some dependency injection exists but inconsistent
   - Service container exists (`service_container.py`)
   - Needs standardization across all services

## Plan

1. ✅ Analyze current service structure
2. Create domain-based organization structure
3. Move services to appropriate domains
4. Extract background workers to `workers/`
5. Improve dependency injection patterns
6. Update imports and references

## Next Steps

- Analyze scheduler structure
- Create domain organization plan
- Start reorganizing services

