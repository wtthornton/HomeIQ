# Test Button - Approve & Create API Integration Plan

**Date:** January 2025  
**Feature:** Modify Test button to use Approve & Create API  
**Status:** 📋 Planning

---

## Overview

Change the Test button functionality to:
1. Use the same 'Approve & Create' API endpoint (no prompt simplification)
2. Create automation in Home Assistant
3. Immediately disable the automation after creation
4. Only allow single execution (disable button after first click)

---

## Current Behavior Analysis

### Current Test Endpoint (`/test`)
- **Location:** `services/ai-automation-service/src/api/ask_ai_router.py:1708`
- **Behavior:**
  - Simplifies prompt using AI (`simplify_query_for_test`)
  - Generates test automation YAML
  - Creates automation with `[TEST]` prefix
  - Triggers automation immediately
  - Disables automation after execution
- **API Call:** `POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/test`

### Current Approve Endpoint (`/approve`)
- **Location:** `services/ai-automation-service/src/api/ask_ai_router.py:2190`
- **Behavior:**
  - Generates full YAML from suggestion (no simplification)
  - Validates YAML with safety checks
  - Creates automation in Home Assistant
  - **Enables** automation automatically
- **API Call:** `POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/approve`

### Home Assistant API (2025.10.4)

Based on research:
- **Create Automation:** `POST /api/config/automation/config/{automation_id}`
- **Disable Automation:** `POST /api/services/automation/turn_off` with `{"entity_id": "automation.id"}`
- **Enable Automation:** `POST /api/services/automation/turn_on` with `{"entity_id": "automation.id"}`

The `ha_client.py` already has `disable_automation()` method at line 458.

---

## Proposed Changes

### Option 1: Frontend-Only Approach (Recommended)

**Changes:**
1. Frontend Test button calls `approveAskAISuggestion()` instead of `testAskAISuggestion()`
2. After successful approval, immediately call disable automation API
3. Track test state to prevent multiple clicks
4. Update UI to show disabled state

**Pros:**
- Minimal backend changes
- Reuses existing approve endpoint
- Clear separation of concerns

**Cons:**
- Requires two API calls (approve + disable)
- Slight delay between create and disable

### Option 2: Backend Parameter Approach

**Changes:**
1. Add optional `test_mode: bool` parameter to approve endpoint
2. When `test_mode=true`, create automation but disable it
3. Frontend calls approve with `test_mode=true`
4. Backend handles disable automatically

**Pros:**
- Single API call
- Atomic operation
- Cleaner frontend code

**Cons:**
- Requires backend changes
- Adds complexity to approve endpoint

**Recommendation:** **Option 1** - Frontend-only approach for faster implementation and minimal risk.

---

## Implementation Plan

### Phase 1: Frontend Changes

#### 1.1 Update `AskAI.tsx` Component

**File:** `services/ai-automation-ui/src/pages/AskAI.tsx`

**Changes:**
- Modify `handleSuggestionAction()` for `test` action
- Add state tracking for test button (per suggestion)
- Call `approveAskAISuggestion()` instead of `testAskAISuggestion()`
- After approval, call disable automation API
- Update button disabled state based on test state

**Key Code Changes:**

```typescript
// Add state to track tested suggestions
const [testedSuggestions, setTestedSuggestions] = useState<Set<string>>(new Set());

// Modify handleSuggestionAction for 'test'
if (action === 'test') {
  const messageWithQuery = messages.find(msg => 
    msg.suggestions?.some(s => s.suggestion_id === suggestionId)
  );
  const queryId = messageWithQuery?.id || 'unknown';
  
  // Mark as tested immediately (prevent double-click)
  setTestedSuggestions(prev => new Set(prev).add(suggestionId));
  
  const loadingToast = toast.loading('⏳ Creating automation (will be disabled)...');
  
  try {
    // Call approve endpoint (same as Approve & Create)
    const response = await api.approveAskAISuggestion(queryId, suggestionId);
    
    if (response.automation_id && response.status === 'approved') {
      // Immediately disable the automation
      try {
        await api.disableAutomation(response.automation_id);
        toast.dismiss(loadingToast);
        toast.success(
          `✅ Test automation created and disabled!\n\nAutomation ID: ${response.automation_id}`,
          { duration: 8000 }
        );
        toast(
          `💡 The automation "${response.automation_id}" is disabled. You can enable it manually or approve this suggestion.`,
          { icon: 'ℹ️', duration: 6000 }
        );
      } catch (disableError) {
        toast.dismiss(loadingToast);
        toast.error(
          `⚠️ Automation created but failed to disable: ${response.automation_id}`,
          { duration: 8000 }
        );
      }
    } else {
      toast.dismiss(loadingToast);
      toast.error(`❌ Failed to create test automation`);
      // Re-enable button on error
      setTestedSuggestions(prev => {
        const newSet = new Set(prev);
        newSet.delete(suggestionId);
        return newSet;
      });
    }
  } catch (error) {
    toast.dismiss(loadingToast);
    toast.error(`❌ Failed to create test automation`);
    // Re-enable button on error
    setTestedSuggestions(prev => {
      const newSet = new Set(prev);
      newSet.delete(suggestionId);
      return newSet;
    });
    throw error;
  }
}
```

#### 1.2 Update `ConversationalSuggestionCard.tsx`

**File:** `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`

**Changes:**
- Accept `tested` prop to show disabled state
- Update button UI to reflect tested state

**Key Code Changes:**

```typescript
interface Props {
  // ... existing props
  tested?: boolean; // Add this prop
}

// In the Test button section
<button
  onClick={handleTest}
  disabled={disabled || tested} // Add tested check
  className={`px-4 py-3 font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 shadow-md ${
    disabled || tested
      ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
      : darkMode
        ? 'bg-yellow-600 hover:bg-yellow-700 text-white hover:shadow-lg'
        : 'bg-yellow-500 hover:bg-yellow-600 text-white hover:shadow-lg'
  }`}
>
  {tested ? (
    <>
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
      <span>Tested</span>
    </>
  ) : (
    <>
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>Test</span>
    </>
  )}
</button>
```

#### 1.3 Update `api.ts` Service

**File:** `services/ai-automation-ui/src/services/api.ts`

**Changes:**
- Add `disableAutomation()` method if not already present

**Key Code Changes:**

```typescript
async disableAutomation(automationId: string): Promise<any> {
  return fetchJSON(`${API_BASE_URL}/deploy/automations/${automationId}/disable`, {
    method: 'POST',
  });
},
```

**Note:** Check if this method already exists. If it does (line 262), use existing implementation.

#### 1.4 Pass Tested State to Card

**File:** `services/ai-automation-ui/src/pages/AskAI.tsx`

**Changes:**
- Pass `tested` prop to `ConversationalSuggestionCard`

```typescript
<ConversationalSuggestionCard
  // ... existing props
  tested={testedSuggestions.has(suggestion.suggestion_id)}
/>
```

---

### Phase 2: API Verification

#### 2.1 Verify Disable Automation Endpoint

**Endpoint:** `POST /api/deploy/automations/{automation_id}/disable`

**Check:**
- Endpoint exists in `services/ai-automation-service/src/api/deployment_router.py`
- Returns proper success/error responses
- Uses correct HA API format

**Location:** Line 310 in `deployment_router.py` (already exists)

#### 2.2 Test Automation ID Format

**Verify:**
- `response.automation_id` from approve endpoint matches format expected by disable endpoint
- Entity ID format (e.g., `automation.test_123` vs `test_123`)

**Action:**
- Check `ha_client.create_automation()` return format
- Ensure consistency between create and disable calls

---

### Phase 3: Testing

#### 3.1 Manual Testing Checklist

- [ ] Test button calls approve endpoint (verify in Network tab)
- [ ] Automation is created in Home Assistant
- [ ] Automation is immediately disabled
- [ ] Button becomes disabled after first click
- [ ] Button shows "Tested" state
- [ ] Button cannot be clicked again
- [ ] Error handling works (re-enables button on failure)
- [ ] Toast messages are clear and informative

#### 3.2 Edge Cases

- [ ] Network failure during approve call
- [ ] Network failure during disable call
- [ ] Invalid automation_id returned
- [ ] Home Assistant API timeout
- [ ] Multiple suggestions - each tracked independently

#### 3.3 Integration Testing

**Update:** `tests/integration/ask-ai-test-button.spec.ts`

**Changes:**
- Update test to expect approve endpoint call
- Verify disable API call after approval
- Check automation is disabled in HA
- Verify button disabled state

---

## Migration Notes

### Breaking Changes
- **None** - Test button behavior changes, but API endpoints remain compatible

### Backward Compatibility
- Old test endpoint (`/test`) still exists but is no longer called from UI
- Can be deprecated in future if no other consumers

### User Experience Changes
- Test button now creates actual automation (not simplified version)
- Automation is disabled (not enabled) after creation
- Button is permanently disabled after first click
- More accurate test (full automation, not simplified command)

---

## Implementation Steps

1. **Step 1:** Add `disableAutomation()` to `api.ts` (if missing)
2. **Step 2:** Add `testedSuggestions` state to `AskAI.tsx`
3. **Step 3:** Update `handleSuggestionAction()` for test case
4. **Step 4:** Update `ConversationalSuggestionCard` to accept `tested` prop
5. **Step 5:** Pass `tested` prop from `AskAI.tsx` to card
6. **Step 6:** Test manually on `http://localhost:3001/ask-ai`
7. **Step 7:** Update integration tests
8. **Step 8:** Verify error handling

---

## Success Criteria

✅ Test button calls `approveAskAISuggestion()` API  
✅ No prompt simplification occurs  
✅ Automation is created in Home Assistant  
✅ Automation is immediately disabled  
✅ Button becomes disabled after first click  
✅ Button shows "Tested" state  
✅ Error handling works correctly  
✅ Integration tests pass  

---

## Timeline Estimate

- **Implementation:** 2-3 hours
- **Testing:** 1-2 hours
- **Total:** 3-5 hours

---

## Risk Assessment

### Low Risk
- Frontend-only changes
- Existing APIs are stable
- Clear error handling paths

### Mitigation
- Test thoroughly before deployment
- Keep old test endpoint available as fallback
- Monitor error logs after deployment

---

## Future Enhancements

1. **Option:** Add backend `test_mode` parameter for atomic operation
2. **Option:** Store test state in localStorage (persist across page reloads)
3. **Option:** Show automation status (enabled/disabled) in UI
4. **Option:** Add "Enable Test Automation" button after testing

---

## Related Files

### Frontend
- `services/ai-automation-ui/src/pages/AskAI.tsx`
- `services/ai-automation-ui/src/components/ConversationalSuggestionCard.tsx`
- `services/ai-automation-ui/src/services/api.ts`

### Backend (Reference Only)
- `services/ai-automation-service/src/api/ask_ai_router.py` (approve endpoint)
- `services/ai-automation-service/src/api/deployment_router.py` (disable endpoint)
- `services/ai-automation-service/src/clients/ha_client.py` (HA API client)

### Tests
- `tests/integration/ask-ai-test-button.spec.ts`

---

**Last Updated:** January 2025  
**Status:** 📋 Ready for Implementation

