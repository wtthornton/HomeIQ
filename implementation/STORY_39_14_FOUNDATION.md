# Story 39.14: Service Layer Reorganization - Foundation

**Epic 39, Story 39.14**  
**Status:** Foundation Complete - Ready for Implementation

## Analysis Complete

### Current Service Structure Identified

**Existing Domain Directories:**
- ✅ `automation/` - 9 files (YAML generation, deployment, validation)
- ✅ `clarification/` - 11 files (detection, question generation, RLHF)
- ✅ `conversation/` - 5 files (context, history, intent matching)
- ✅ `device/` - 1 file (device context)
- ✅ `entity/` - 4 files (extraction, enrichment, validation)
- ✅ `learning/` - 12 files (pattern learning, RLHF, quality scoring)
- ✅ `rag/` - 6 files (RAG client, retrieval, reranking)
- ✅ `blueprints/` - 3 files (matching, rendering, filling)
- ✅ `confidence/` - 1 file (confidence calculation)
- ✅ `function_calling/` - 1 file (function registry)

**Top-Level Services (Need Organization):**
- 25+ service files at top level that should be organized by domain

**Background Workers:**
- `scheduler/daily_analysis.py` - DailyAnalysisScheduler (3 AM batch job)
- `scheduler/learning_scheduler.py` - LearningScheduler

### Reorganization Strategy

**Proposed Domain Structure:**
```
services/
├── domain/
│   ├── automation/     # Merge existing automation/
│   ├── entity/         # Merge existing entity/ + move top-level entity services
│   ├── device/         # Merge existing device/ + move top-level device services
│   ├── pattern/        # Pattern and synergy services
│   ├── learning/       # Keep existing learning/
│   ├── conversation/   # Keep existing conversation/
│   ├── rag/            # Keep existing rag/
│   ├── validation/     # New: Validation services
│   └── analytics/      # New: Analytics and metrics services
├── core/               # Core infrastructure
│   ├── service_container.py
│   └── error_recovery.py
└── workers/            # Background workers
    ├── daily_analysis_scheduler.py
    └── learning_scheduler.py
```

### Key Improvements Needed

1. **Domain Organization**
   - Move 25+ top-level services to appropriate domains
   - Consolidate related services

2. **Dependency Injection**
   - Standardize service initialization
   - Use service container consistently
   - Improve router dependency injection

3. **Background Workers**
   - Extract schedulers to `workers/` directory
   - Improve worker lifecycle management
   - Better separation of concerns

## Implementation Approach

Given the scope of this story (3-4 hours), we'll focus on:
1. Extracting background workers (highest impact)
2. Organizing most critical top-level services
3. Improving dependency injection patterns

## Files Created

- `services/ai-automation-service/STORY_39_14_PLAN.md` - Detailed reorganization plan
- `implementation/STORY_39_14_START.md` - Analysis summary
- `implementation/STORY_39_14_FOUNDATION.md` - This document

## Next Steps

1. Extract schedulers to `workers/` directory
2. Move critical top-level services to domains
3. Update imports and references
4. Test that everything still works

