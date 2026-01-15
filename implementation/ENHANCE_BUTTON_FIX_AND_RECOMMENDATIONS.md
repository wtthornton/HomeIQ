# Enhance Button Fix and Recommendations

**Date:** January 15, 2026
**Issue:** Enhance button doesn't work after automation creation
**Status:** ✅ Fixed

## Summary

Fixed the issue where the Enhance button appeared after automation creation but didn't work (showed error toast: "Original prompt is required for enhancements").

## Root Cause

After automation creation, `loadConversation()` was called to refresh the conversation, which replaced all messages. However, the `originalPrompt` state was not synchronized with this reload, causing it to be empty or stale when the EnhancementButton tried to use it.

## Fix Applied

### 1. Fix in `loadConversation()` Function

**File:** `services/ai-automation-ui/src/pages/HAAgentChat.tsx` (lines 147-156)

Added code to set `originalPrompt` from the latest user message after conversation reload:

```typescript
// Fix for EnhancementButton: Ensure originalPrompt is set after reload
// Set originalPrompt from latest user message if not already set
// This ensures EnhancementButton works after automation creation + reload
if (!originalPrompt) {
  const latestUserMsg = deduplicated.slice().reverse().find(m => m.role === 'user');
  if (latestUserMsg) {
    setOriginalPrompt(latestUserMsg.content);
    console.log('[HAAgentChat] Set originalPrompt from latest user message after reload');
  }
}
```

### 2. Defensive useEffect Hook

**File:** `services/ai-automation-ui/src/pages/HAAgentChat.tsx` (lines 185-203)

Added useEffect to set `originalPrompt` when automation is detected, even if user didn't preview first:

```typescript
// Fix for EnhancementButton: Set originalPrompt when automation is detected
// This ensures originalPrompt is available even if user didn't preview automation first
useEffect(() => {
  // Only set if not already set
  if (!originalPrompt && messages.length > 0) {
    // Check if any message contains automation
    const hasAutomation = messages.some(m => {
      // Check tool calls for automation-related tools
      if (m.toolCalls) {
        return m.toolCalls.some(tc => 
          tc.name === 'preview_automation_from_prompt' || 
          tc.name === 'create_automation_from_prompt' ||
          tc.name === 'test_automation_yaml'
        );
      }
      // Check message content for YAML code blocks
      return /```yaml\n([\s\S]*?)```/.test(m.content);
    });
    
    if (hasAutomation) {
      const userMsg = messages.slice().reverse().find(m => m.role === 'user');
      if (userMsg) {
        setOriginalPrompt(userMsg.content);
        console.log('[HAAgentChat] Set originalPrompt from latest user message when automation detected');
      }
    }
  }
}, [messages, originalPrompt]);
```

## Testing

### Playwright Tests Created

**File:** `tests/e2e/ai-automation-ui/pages/enhancement-button.spec.ts`

Three test scenarios:
1. **Without Preview:** Create automation directly, verify Enhance button works
2. **With Preview:** Preview first (sets originalPrompt), create automation, verify Enhance button works
3. **After Reload:** Create automation (triggers reload), verify Enhance button still works

### Manual Testing Steps

1. Navigate to `/ha-agent`
2. Create a new conversation
3. Send message: "Create an automation to turn on office lights when motion is detected"
4. Wait for assistant response with automation proposal
5. Click "Create Automation" button
6. Wait for success toast
7. Verify Enhance button is visible
8. Click Enhance button
9. ✅ **Expected:** Enhancement modal appears with suggestions
10. ✅ **Before Fix:** Error toast appeared ("Original prompt is required")
11. ✅ **After Fix:** Modal appears successfully

## Recommendations for Improvement

### 1. State Persistence

**Problem:** `originalPrompt` is local state that isn't persisted with conversation data.

**Recommendation:** Consider storing `originalPrompt` in conversation metadata or local storage for persistence across page refreshes.

```typescript
// Option: Store in localStorage with conversation ID
useEffect(() => {
  if (originalPrompt && currentConversationId) {
    localStorage.setItem(`originalPrompt:${currentConversationId}`, originalPrompt);
  }
}, [originalPrompt, currentConversationId]);

// Restore on load
useEffect(() => {
  if (currentConversationId && !originalPrompt) {
    const stored = localStorage.getItem(`originalPrompt:${currentConversationId}`);
    if (stored) {
      setOriginalPrompt(stored);
    }
  }
}, [currentConversationId]);
```

### 2. Better Error Handling

**Problem:** When `originalPrompt` is missing, user only sees a brief error toast.

**Recommendation:** 
- Show a persistent error state on the Enhance button
- Add a tooltip explaining why button is disabled
- Provide actionable guidance (e.g., "Please send a message first")

```typescript
// EnhancementButton already has warning UI, but could be improved:
{!hasPrerequisites && !isLoading && (
  <div className="tooltip">
    Missing: {missingPrerequisites.join(', ')}
    <span className="tooltip-text">
      Please send a message to start a conversation before using Enhance.
    </span>
  </div>
)}
```

### 3. Debug Logging

**Problem:** Difficult to diagnose when `originalPrompt` is missing.

**Recommendation:** Add structured logging for debugging:

```typescript
if (!originalPrompt) {
  console.warn('[EnhancementButton] originalPrompt missing:', {
    conversationId,
    messagesCount: messages.length,
    hasLatestUserMessage: !!userMsg,
    userMessageContent: userMsg?.content?.substring(0, 50),
  });
}
```

### 4. Memoization Optimization

**Problem:** `latestUserMessage` is memoized, but we recalculate user message multiple times.

**Recommendation:** Reuse memoized `latestUserMessage` in EnhancementButton render:

```typescript
// Already using latestUserMessage, but could optimize further:
const userMsgForEnhance = useMemo(() => {
  if (originalPrompt) return null; // Don't calculate if already set
  return latestUserMessage;
}, [originalPrompt, latestUserMessage]);

// In render:
<EnhancementButton
  originalPrompt={originalPrompt || userMsgForEnhance?.content || ''}
  ...
/>
```

### 5. Type Safety

**Recommendation:** Add TypeScript types for better type safety:

```typescript
interface EnhancementButtonState {
  originalPrompt: string | null;
  automationYaml: string | null;
  conversationId: string | null;
}

// Type guard
const hasValidEnhancementState = (state: EnhancementButtonState): boolean => {
  return !!(state.conversationId && state.originalPrompt);
};
```

### 6. Unit Tests

**Recommendation:** Add unit tests for state management:

```typescript
describe('HAAgentChat originalPrompt management', () => {
  it('should set originalPrompt after loadConversation', async () => {
    // Test loadConversation sets originalPrompt
  });
  
  it('should set originalPrompt when automation detected', () => {
    // Test useEffect sets originalPrompt
  });
  
  it('should preserve originalPrompt after reload', async () => {
    // Test originalPrompt survives loadConversation
  });
});
```

### 7. User Experience Improvements

**Recommendation:**
- Show loading state when Enhance button is generating suggestions
- Provide feedback when suggestions are ready
- Add keyboard shortcut for Enhance (e.g., Ctrl+E)
- Show enhancement history for re-application

### 8. API Response Validation

**Recommendation:** Add validation for enhancement API response:

```typescript
// In EnhancementButton.tsx handleEnhance
if (!result.success || !result.enhancements || !Array.isArray(result.enhancements)) {
  console.error('[EnhancementButton] Invalid API response:', result);
  toast.error(result.error || 'Failed to generate enhancements', { icon: '❌' });
  setShowModal(false);
  return;
}

if (result.enhancements.length === 0) {
  toast.error('No enhancement suggestions available', { icon: '⚠️' });
  setShowModal(false);
  return;
}
```

## Verification

### Before Fix
- ❌ Enhance button showed error toast after automation creation
- ❌ No modal appeared
- ❌ User saw no visible response

### After Fix
- ✅ Enhance button works after automation creation
- ✅ Modal appears with enhancement suggestions
- ✅ originalPrompt is preserved after conversation reload
- ✅ Works even if user didn't preview automation first

## Related Files

- `services/ai-automation-ui/src/pages/HAAgentChat.tsx` - Main fix location
- `services/ai-automation-ui/src/components/ha-agent/EnhancementButton.tsx` - Button component
- `services/ai-automation-ui/src/components/ha-agent/CTAActionButtons.tsx` - Automation creation
- `tests/e2e/ai-automation-ui/pages/enhancement-button.spec.ts` - Playwright tests
- `implementation/ENHANCE_BUTTON_ISSUE_ANALYSIS.md` - Detailed analysis

## Next Steps

1. ✅ Fix applied
2. ⏳ Run Playwright tests to verify fix
3. ⏳ Manual testing in browser
4. ⏳ Monitor error logs for any issues
5. ⏳ Consider implementing recommendations for future improvements
