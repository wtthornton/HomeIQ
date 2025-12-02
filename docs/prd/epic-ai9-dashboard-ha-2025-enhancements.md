# Epic AI-9: Dashboard Home Assistant 2025 Enhancements

**Status:** 📋 **PLANNING**  
**Type:** Brownfield Enhancement (AI Automation UI)  
**Priority:** Medium  
**Effort:** 4 Stories (10 story points, 2-3 weeks estimated)  
**Created:** January 2025  
**Last Updated:** January 2025

---

## Epic Goal

Enhance the AI Automation UI dashboard to display and utilize Home Assistant 2025 attributes (aliases, labels, options, icon) and best practices information (tags, mode, initial_state).

**Business Value:**
- **+30% user satisfaction** - Better visualization of automation details
- **+20% adoption rate** - Clearer information increases confidence
- **100% feature visibility** - All new attributes visible to users

---

## Existing System Context

### Current Functionality

**AI Automation UI** (Port 3000) currently:
- Displays automation suggestions in conversational cards
- Shows device information in device explorer
- Filters suggestions by various criteria
- Displays basic entity information

**Current Dashboard Display Status:**

**Already Displayed:**
- ✅ Entity names and IDs
- ✅ Basic device information
- ✅ Suggestion descriptions
- ✅ Entity icons (may use original_icon)

**Missing:**
- ❌ Automation tags display
- ❌ Entity labels display
- ❌ Entity options display
- ❌ Automation metadata (mode, initial_state)
- ❌ Enhanced icon display (current icon vs original)

### Technology Stack

- **Frontend:** `services/ai-automation-ui/` (React, TypeScript)
- **Components:** 
  - `src/components/ConversationalSuggestionCard.tsx`
  - `src/components/FilterPills.tsx`
  - `src/components/discovery/DeviceExplorer.tsx`
- **Types:** `src/types/index.ts`
- **API Client:** Connects to AI Automation Service (Port 8024)

### Integration Points

- Suggestion card display (`ConversationalSuggestionCard.tsx`)
- Device explorer (`DeviceExplorer.tsx`)
- Filter components (`FilterPills.tsx`)
- Type definitions (`types/index.ts`)
- API responses from AI Automation Service

---

## Enhancement Details

### What's Being Added/Changed

1. **Display Automation Tags** (NEW)
   - Tags displayed on suggestion cards
   - Tag-based filtering in dashboard
   - Tag badges with color coding (energy=green, security=red, etc.)
   - Tag tooltips explaining meaning

2. **Display Entity Labels and Options** (NEW)
   - Entity labels displayed in device info
   - Entity options displayed in device info (e.g., default brightness)
   - Label-based filtering in device explorer
   - Options shown as preferences in suggestions

3. **Display Automation Metadata (Mode, Initial State)** (NEW)
   - Automation mode displayed (single/restart/queued/parallel)
   - Initial state displayed (enabled/disabled)
   - Mode tooltip explaining meaning
   - Visual indicators for mode type

4. **Enhanced Entity Icon Display** (ENHANCEMENT)
   - Current `icon` (not `original_icon`) displayed
   - Icon changes reflected in UI
   - Icon fallback handling (if icon missing, use original_icon)
   - Icon tooltip showing icon source

### How It Integrates

- **Non-Breaking Changes:** All enhancements are additive, existing UI unchanged
- **Incremental Integration:** Each story builds on previous work
- **Backward Compatible:** Existing displays continue to work
- **Progressive Enhancement:** New features enhance existing UI

---

## Success Criteria

1. **Functional:**
   - All new attributes displayed in dashboard
   - Tag filtering working
   - Label/option display working
   - Metadata display working
   - Icon display correct

2. **Technical:**
   - E2E tests pass
   - No breaking changes
   - Responsive design maintained
   - Performance requirements met

3. **Quality:**
   - All existing functionality verified
   - UI/UX consistency maintained
   - Comprehensive documentation
   - Code reviewed and approved

---

## Stories

### Phase 1: Tag and Metadata Display (Week 1)

#### Story AI9.1: Display Automation Tags
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Display automation tags on suggestion cards with filtering and color coding.

**Acceptance Criteria:**
1. Tags displayed on suggestion cards
2. Tag-based filtering in dashboard
3. Tag badges with color coding (energy=green, security=red, etc.)
4. Tag tooltips explaining meaning
5. E2E tests verify tag display

**Files to Update:**
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
- `services/ai-automation-ui/src/components/FilterPills.tsx`
- `services/ai-automation-ui/src/types/index.ts` - Add `tags` to `Suggestion` interface

---

#### Story AI9.2: Display Entity Labels and Options
**Type:** Feature  
**Points:** 3  
**Effort:** 6-8 hours

Display entity labels and options in device info and suggestions.

**Acceptance Criteria:**
1. Entity labels displayed in device info
2. Entity options displayed in device info (e.g., default brightness)
3. Label-based filtering in device explorer
4. Options shown as preferences in suggestions
5. E2E tests verify label/option display

**Files to Update:**
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
- `services/ai-automation-ui/src/components/discovery/DeviceExplorer.tsx`
- `services/ai-automation-ui/src/types/index.ts` - Add `labels`, `options` to entity types

---

### Phase 2: Metadata and Icon Enhancement (Week 2-3)

#### Story AI9.3: Display Automation Metadata (Mode, Initial State)
**Type:** Feature  
**Points:** 2  
**Effort:** 4-6 hours

Display automation mode and initial state on suggestion cards.

**Acceptance Criteria:**
1. Automation mode displayed (single/restart/queued/parallel)
2. Initial state displayed (enabled/disabled)
3. Mode tooltip explaining meaning
4. Visual indicators for mode type
5. E2E tests verify metadata display

**Files to Update:**
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
- `services/ai-automation-ui/src/types/index.ts` - Add `mode`, `initial_state` to `Suggestion` interface

---

#### Story AI9.4: Enhanced Entity Icon Display
**Type:** Enhancement  
**Points:** 2  
**Effort:** 4-6 hours

Ensure current `icon` (not `original_icon`) is displayed with proper fallback handling.

**Acceptance Criteria:**
1. Current `icon` (not `original_icon`) displayed
2. Icon changes reflected in UI
3. Icon fallback handling (if icon missing, use original_icon)
4. Icon tooltip showing icon source
5. E2E tests verify icon display

**Files to Update:**
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
- `services/ai-automation-ui/src/components/discovery/DeviceExplorer.tsx`
- `services/ai-automation-ui/src/types/index.ts` - Ensure `icon` field included

---

## Dependencies

### External Dependencies
- **Home Assistant 2025.10+** - Required for new API attributes
- **AI Automation Service** - Must provide tags, labels, options, metadata in API responses

### Internal Dependencies
- **Epic AI-7** - Best Practices Implementation (provides tags, mode, initial_state)
- **Epic AI-8** - HA 2025 API Integration (provides labels, options, icon)

---

## Risk Mitigation

### Technical Risks

**UI Changes:**
- **Risk:** Dashboard changes may break existing UI
- **Mitigation:** Backward compatibility, feature flags
- **Testing:** E2E tests for all UI changes

**API Compatibility:**
- **Risk:** API may not provide all new attributes
- **Mitigation:** Graceful fallback, optional fields
- **Testing:** Test with missing attributes

### Timeline Risks

**Dependency on Other Epics:**
- **Risk:** Depends on Epic AI-7 and AI-8 completion
- **Mitigation:** Can start UI work in parallel, use mock data
- **Approach:** Coordinate with backend team

---

## Related Documentation

- [HA Best Practices & API 2025 Update Plan](../../implementation/HA_BEST_PRACTICES_AND_API_2025_UPDATE_PLAN.md)
- [Epic AI-7: Home Assistant Best Practices Implementation](./epic-ai7-home-assistant-best-practices-implementation.md)
- [Epic AI-8: Home Assistant 2025 API Integration](./epic-ai8-home-assistant-2025-api-integration.md)

---

**Epic Owner:** Product Manager  
**Technical Lead:** AI Automation UI Team  
**Status:** 📋 Planning  
**Next Steps:** Begin Story AI9.1 - Display Automation Tags (after Epic AI-7 Story AI7.8 completes)

