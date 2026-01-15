# Enhance Button Issue Analysis

**Date:** January 15, 2026
**Issue:** Enhance button doesn't return/work after automation creation
**Status:** Root cause identified

## Problem Description

After creating an automation successfully, the Enhance button remains visible but clicking it doesn't work. The button appears to do nothing (no response/no modal).

## Root Cause Analysis

### Issue Location

**File:** `services/ai-automation-ui/src/pages/HAAgentChat.tsx`

**Problem Flow:**

1. User creates automation via `CTAActionButtons` (line 840-846)
2. `onSuccess` callback is triggered after successful creation:
   ```typescript
   onSuccess={(automationId) => {
     toast.success(`Automation ${automationId} created successfully!`);
     // Refresh conversation to show new message
     if (currentConversationId) {
       loadConversation();  // ← This reloads messages from API
     }
   }}
   ```

3. `loadConversation()` (lines 130-156) reloads conversation from API:
   - Replaces all messages with `setMessages(deduplicated)` (line 145)
   - Does NOT update `originalPrompt` state
   - Messages are reloaded, so memoized `latestUserMessage` recalculates

4. `EnhancementButton` is rendered (lines 933-939):
   ```typescript
   <EnhancementButton
     originalPrompt={originalPrompt || userMsg?.content || ''}  // ← Problem here
     ...
   />
   ```

5. **The Issue:**
   - `originalPrompt` state is only set when `handlePreviewAutomation()` is called (line 502)
   - If user didn't preview automation first, `originalPrompt` is empty
   - After `loadConversation()`, `userMsg` is recalculated from reloaded messages
   - But if `originalPrompt` is empty and `userMsg?.content` is also empty/undefined, the button receives an empty string

6. When Enhance button is clicked (EnhancementButton.tsx line 50-59):
   ```typescript
   if (!originalPrompt) {
     toast.error('Original prompt is required for enhancements.', { icon: '❌' });
     return;  // ← Fails here with error toast
   }
   ```

### Why It Fails

**Primary Issue:** State synchronization problem
- `originalPrompt` is local state that isn't persisted/restored after conversation reload
- After `loadConversation()` replaces messages, `originalPrompt` state may be stale or empty
- The fallback `userMsg?.content` might work, but timing/dependency issues could cause it to be empty

**Secondary Issues:**
1. **Memoization Dependency:** `latestUserMessage` (line 482-490) depends on `messages` array, which is replaced during reload
2. **State Initialization:** `originalPrompt` is only initialized when preview is opened, not when automation is detected
3. **No State Persistence:** `originalPrompt` isn't saved/restored with conversation state

## Evidence from Code

### EnhancementButton Requirements (EnhancementButton.tsx:50-59)
```typescript
if (!conversationId) {
  toast.error('No conversation active. Please start a conversation first.', { icon: '❌' });
  return;
}

if (!originalPrompt) {
  toast.error('Original prompt is required for enhancements.', { icon: '❌' });
  return;  // ← User sees this error, but it appears to "do nothing"
}
```

### originalPrompt State Management (HAAgentChat.tsx:492-505)
```typescript
const handlePreviewAutomation = (message: ChatMessage) => {
  const automation = detectAutomation(message);
  if (automation) {
    setPreviewAutomationYaml(automation.yaml);
    setPreviewAutomationAlias(automation.alias);
    setPreviewToolCall(automation.toolCall ?? undefined);
    setAutomationPreviewOpen(true);
    
    // Use memoized latest user message
    if (latestUserMessage) {
      setOriginalPrompt(latestUserMessage.content);  // ← Only set here
    }
  }
};
```

### After Automation Creation (HAAgentChat.tsx:840-846)
```typescript
onSuccess={(automationId) => {
  toast.success(`Automation ${automationId} created successfully!`);
  // Refresh conversation to show new message
  if (currentConversationId) {
    loadConversation();  // ← Reloads messages, originalPrompt NOT updated
  }
}}
```

### EnhancementButton Render (HAAgentChat.tsx:933-939)
```typescript
<EnhancementButton
  automationYaml={automationYaml || undefined}
  originalPrompt={originalPrompt || userMsg?.content || ''}  // ← Fallback may fail
  conversationId={currentConversationId}
  darkMode={darkMode}
  onEnhancementSelected={handleEnhancementSelected}
/>
```

## Expected vs Actual Behavior

### Expected Behavior
- After automation creation, Enhance button should work
- Clicking Enhance should open modal with enhancement suggestions
- `originalPrompt` should be available from latest user message

### Actual Behavior
- Enhance button is visible after automation creation
- Clicking Enhance shows error toast: "Original prompt is required for enhancements."
- No modal appears (because function returns early)
- User sees no visible response (only brief error toast)

## Test Scenarios to Verify

1. **Without Preview:**
   - Create automation directly (don't preview first)
   - Click Enhance button
   - Expected: Should work (use latest user message)
   - Actual: Fails with error toast

2. **With Preview:**
   - Preview automation first (sets `originalPrompt`)
   - Create automation
   - Click Enhance button
   - Expected: Should work
   - Actual: May work if `originalPrompt` still set

3. **After Conversation Reload:**
   - Create automation
   - `loadConversation()` is called
   - Click Enhance button
   - Expected: Should work (originalPrompt restored or fallback works)
   - Actual: Fails (originalPrompt lost after reload)

## Fix Strategy

### Option 1: Ensure originalPrompt is Set After Reload (Recommended)

Update `loadConversation()` to set `originalPrompt` after loading messages:

```typescript
const loadConversation = async () => {
  if (currentConversationId) {
    try {
      setIsInitializing(true);
      const conversation = await getConversation(currentConversationId);
      setCurrentConversation(conversation);
      const loadedMessages = conversation.messages?.map((msg) => ({
        ...msg,
        isLoading: false,
      })) || [];
      
      const deduplicated = deduplicateMessages(loadedMessages);
      setMessages(deduplicated);
      
      // Set originalPrompt from latest user message if not already set
      if (!originalPrompt) {
        const latestUserMsg = deduplicated.slice().reverse().find(m => m.role === 'user');
        if (latestUserMsg) {
          setOriginalPrompt(latestUserMsg.content);
        }
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
      toast.error('Failed to load conversation');
    } finally {
      setIsInitializing(false);
    }
  }
};
```

### Option 2: Use Memoized Value Directly (Simpler)

Change EnhancementButton render to always use memoized value:

```typescript
const latestUserMessageForEnhance = useMemo(() => {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'user') {
      return messages[i];
    }
  }
  return undefined;
}, [messages]);

// In render:
<EnhancementButton
  originalPrompt={originalPrompt || latestUserMessageForEnhance?.content || ''}
  ...
/>
```

### Option 3: Set originalPrompt on Automation Detection

Set `originalPrompt` when automation is detected, not just when preview is opened:

```typescript
// Detect automation and set originalPrompt
useEffect(() => {
  const automation = messages.find(m => detectAutomation(m));
  if (automation && !originalPrompt) {
    const userMsg = messages.slice().reverse().find(m => m.role === 'user');
    if (userMsg) {
      setOriginalPrompt(userMsg.content);
    }
  }
}, [messages, originalPrompt]);
```

## Recommended Solution

**Implement Option 1 + Option 3** (defensive approach):
- Set `originalPrompt` in `loadConversation()` after messages are loaded
- Also set it when automation is detected (useEffect)
- This ensures `originalPrompt` is always available when EnhancementButton is rendered

## Additional Improvements

1. **Better Error Handling:** Show visible error state instead of just toast
2. **Debug Logging:** Log when `originalPrompt` is missing to help diagnose
3. **UI Feedback:** Disable Enhance button if prerequisites missing (already implemented, but could improve tooltip)
4. **State Persistence:** Consider storing `originalPrompt` in conversation metadata if needed for persistence

## Next Steps

1. ✅ Root cause identified
2. ⏳ Create Playwright test to reproduce issue
3. ⏳ Implement fix (Option 1 + Option 3)
4. ⏳ Test fix with Playwright
5. ⏳ Verify error no longer occurs
