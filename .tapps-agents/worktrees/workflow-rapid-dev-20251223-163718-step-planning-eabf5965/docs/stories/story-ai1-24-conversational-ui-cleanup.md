# Story AI1.24: Conversational UI Cleanup & Full Implementation

**Epic:** AI-1 (Pattern Automation)  
**Status:** In Progress  
**Priority:** High  
**Created:** October 19, 2025

---

## Overview

Clean up dual-implementation technical debt and fully implement the conversational automation refinement flow (Story AI1.23). Remove legacy Dashboard that shows YAML immediately and ensure all paths use the new description-first, conversational refinement approach.

---

## Problem Statement

**Current State:**
- Two parallel UI implementations exist (old Dashboard vs. ConversationalDashboard)
- Backend generates YAML immediately (old approach) but uses new status states (`'draft'`)
- ConversationalDashboard is built but not routed
- User confusion about which UI to use
- Maintenance burden of two codebases

**Desired State:**
- Single conversational UI at root route (`/`)
- Backend generates description-only suggestions
- YAML only generated after user approval
- Clean codebase with no legacy components

---

## Acceptance Criteria

### Frontend Cleanup
- [ ] **AC1:** Old `Dashboard.tsx` deleted
- [ ] **AC2:** `ConversationalDashboard.tsx` moved to main route (`/`)
- [ ] **AC3:** Navigation updated (remove any references to old dashboard)
- [ ] **AC4:** All status filters updated to use new schema (`draft`, `refining`, `yaml_generated`)
- [ ] **AC5:** No YAML shown until status = `yaml_generated`

### Backend Cleanup
- [ ] **AC6:** Daily analysis job generates description-only (no YAML)
- [ ] **AC7:** Suggestion creation sets `automation_yaml = NULL` for drafts
- [ ] **AC8:** YAML generation only happens via `/approve` endpoint
- [ ] **AC9:** All suggestions created with status = `draft` (not `pending`)
- [ ] **AC10:** Remove legacy status states from backend code

### Database Cleanup
- [ ] **AC11:** Migration to set `automation_yaml = NULL` for all `draft` suggestions
- [ ] **AC12:** Remove any legacy `status = 'pending'` suggestions (convert to `draft`)

### Testing
- [ ] **AC13:** User can view draft suggestions (description only)
- [ ] **AC14:** User can refine suggestions with natural language
- [ ] **AC15:** YAML generates only after approval
- [ ] **AC16:** Deploy works with approved suggestions
- [ ] **AC17:** No legacy Dashboard references in UI

---

## Tasks

### Phase 1: Frontend Cleanup (Immediate)

#### Task 1.1: Delete Legacy Dashboard
**File:** `services/ai-automation-ui/src/pages/Dashboard.tsx`
- [x] Delete entire file
- [x] Remove from git

#### Task 1.2: Wire ConversationalDashboard to Root Route
**File:** `services/ai-automation-ui/src/App.tsx`
- [x] Change route from `<Dashboard />` to `<ConversationalDashboard />`
- [x] Remove Dashboard import
- [x] Add ConversationalDashboard import

#### Task 1.3: Update Navigation
**File:** `services/ai-automation-ui/src/components/Navigation.tsx`
- [ ] Check for any dashboard-specific navigation
- [ ] Update labels if needed

#### Task 1.4: Remove Status Mapping Hack
**File:** Multiple
- [x] Remove `mapStatus()` function (no longer needed)
- [x] All components use new status states natively

### Phase 2: Backend Cleanup (Critical Path)

#### Task 2.1: Update Suggestion Generation
**File:** `services/ai-automation-service/src/scheduler/daily_analysis.py`
- [ ] Line ~500-600: Update suggestion generation to NOT create YAML
- [ ] Set `automation_yaml = None` for new suggestions
- [ ] Ensure `description_only` field is populated
- [ ] Status should be `'draft'` (already correct)

#### Task 2.2: Update OpenAI Prompt
**File:** `services/ai-automation-service/src/llm/openai_client.py`
- [ ] Update initial suggestion prompt to generate description only
- [ ] Remove YAML generation from initial flow
- [ ] Keep YAML generation in approval flow only

#### Task 2.3: Update CRUD Operations
**File:** `services/ai-automation-service/src/database/crud.py`
- [ ] Line 197: Confirm `status='draft'` is correct
- [ ] Ensure `automation_yaml` can be NULL
- [ ] Remove any `status='pending'` references

#### Task 2.4: Clean Up API Endpoints
**Files:** 
- `services/ai-automation-service/src/api/suggestion_router.py`
- `services/ai-automation-service/src/api/suggestion_management_router.py`
- [ ] Remove legacy `/approve` that doesn't use conversational flow
- [ ] Ensure only conversational `/approve` generates YAML
- [ ] Remove any `status='pending'` filters

### Phase 3: Database Migration

#### Task 3.1: Create Migration Script
**File:** `services/ai-automation-service/alembic/versions/XXXXXX_cleanup_legacy_statuses.py`
- [ ] Set `automation_yaml = NULL` for all suggestions with `status='draft'`
- [ ] Convert any `status='pending'` to `status='draft'`
- [ ] Add migration script

#### Task 3.2: Run Migration
- [ ] Test migration on dev database
- [ ] Apply to production database
- [ ] Verify data integrity

### Phase 4: Component Cleanup

#### Task 4.1: Delete Legacy Components
**Files to Review/Delete:**
- [x] `services/ai-automation-ui/src/components/SuggestionCard.tsx` (if only used by old Dashboard)
- [ ] Check for any other Dashboard-specific components
- [ ] Remove from git

#### Task 4.2: Update Type Definitions
**File:** `services/ai-automation-ui/src/types/index.ts`
- [ ] Update `Suggestion` type to match new schema
- [ ] Remove legacy status types if defined

### Phase 5: Testing & Validation

#### Task 5.1: Manual Testing
- [ ] Trigger new analysis run
- [ ] Verify suggestions have description only (no YAML)
- [ ] Test conversational refinement
- [ ] Test approval generates YAML
- [ ] Test deployment works

#### Task 5.2: Update Tests
**Files:** `services/ai-automation-service/tests/`
- [ ] Update unit tests to expect description-only suggestions
- [ ] Update tests to use new status states
- [ ] Remove tests for legacy flow

#### Task 5.3: Documentation Update
- [ ] Update README files
- [ ] Update API documentation
- [ ] Update user guides

---

## Technical Details

### Status State Mapping (NEW - Delete Old)

**New Flow (Keep):**
```
draft → refining → yaml_generated → deployed/rejected
```

**Old Flow (Delete):**
```
pending → approved → deployed/rejected
```

### Suggestion Creation Flow

**Before (Delete):**
```python
# Daily analysis generates YAML immediately
suggestion = Suggestion(
    status='draft',  # Wrong: uses new status but old behavior
    automation_yaml=generated_yaml,  # Wrong: YAML exists immediately
    description_only=description  # Correct
)
```

**After (Implement):**
```python
# Daily analysis generates description only
suggestion = Suggestion(
    status='draft',  # Correct
    automation_yaml=None,  # Correct: No YAML yet
    description_only=description  # Correct
)
```

### Approval Flow

**Before (Delete):**
```
User clicks "Approve" → Status changes to 'approved' → Manual YAML edit → Deploy
```

**After (Implement):**
```
User refines with chat → User clicks "Approve" → GPT generates YAML → Status = 'yaml_generated' → Deploy
```

---

## Files to Delete

### Frontend
- [x] `services/ai-automation-ui/src/pages/Dashboard.tsx` - Old dashboard
- [ ] `services/ai-automation-ui/src/components/SuggestionCard.tsx` - If legacy only
- [ ] `services/ai-automation-ui/src/components/BatchActions.tsx` - Check if legacy only
- [ ] `services/ai-automation-ui/src/components/SearchBar.tsx` - Check if legacy only

### Backend
- [ ] Any legacy API endpoints that use `status='pending'`
- [ ] Legacy suggestion generation code paths

---

## Files to Update

### Frontend
- [x] `services/ai-automation-ui/src/App.tsx` - Route change
- [ ] `services/ai-automation-ui/src/components/Navigation.tsx` - Remove old dashboard refs
- [ ] `services/ai-automation-ui/src/types/index.ts` - Type definitions

### Backend
- [ ] `services/ai-automation-service/src/scheduler/daily_analysis.py` - Description-only generation
- [ ] `services/ai-automation-service/src/llm/openai_client.py` - Prompt updates
- [ ] `services/ai-automation-service/src/database/crud.py` - Status cleanup
- [ ] `services/ai-automation-service/src/api/*.py` - Remove legacy endpoints

---

## Risk Assessment

### Low Risk
- Frontend deletions (can always restore from git)
- Route changes (immediate visual feedback)

### Medium Risk
- Backend suggestion generation changes (affects daily job)
- Database migration (test thoroughly first)

### High Risk
- Deleting API endpoints (check for external dependencies)

---

## Rollback Plan

1. Git revert commits in reverse order
2. Restore old Dashboard.tsx from git history
3. Revert route changes
4. Rollback database migration (down migration)
5. Restart services

---

## Success Metrics

- [ ] Zero references to old Dashboard in codebase
- [ ] All new suggestions have `automation_yaml = NULL`
- [ ] Users successfully refine suggestions conversationally
- [ ] YAML only appears after approval
- [ ] No confusion about which UI to use
- [ ] Cleaner codebase (fewer LOC)

---

## Dependencies

- Story AI1.23 (Conversational Refinement) - Must be complete
- ConversationalDashboard component - Already built
- Backend conversational API - Already built

---

## Timeline

- **Phase 1 (Frontend Cleanup):** 1-2 hours
- **Phase 2 (Backend Cleanup):** 3-4 hours
- **Phase 3 (Database Migration):** 1 hour
- **Phase 4 (Component Cleanup):** 1 hour
- **Phase 5 (Testing):** 2-3 hours

**Total Estimated Time:** 8-11 hours (1-2 days)

---

## Related Stories

- **Story AI1.23:** Conversational Suggestion Refinement (foundation)
- **Story AI1.21:** Natural Language Generation (description generation)
- **Story AI1.11:** Deployment Integration (deploy approved suggestions)

---

## Notes

- This is a **cleanup story**, not a feature story
- Reduces technical debt significantly
- Simplifies maintenance going forward
- Users get cleaner, more intuitive experience
- No functional regressions (new UI is feature-complete)

---

**Author:** BMad Master  
**Reviewer:** TBD  
**Last Updated:** October 19, 2025

