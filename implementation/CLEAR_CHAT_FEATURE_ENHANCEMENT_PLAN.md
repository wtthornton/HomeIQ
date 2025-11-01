# Clear Chat / Start New Feature Enhancement Plan

**Feature:** Enhanced "Clear Chat" functionality for Ask AI page  
**Page:** `http://localhost:3001/ask-ai`  
**Date:** January 2025  
**Status:** Planning

---

## Current Implementation Analysis

### Existing Functionality
The `clearChat` function in `services/ai-automation-ui/src/pages/AskAI.tsx` (lines 466-477) currently:

```466:477:services/ai-automation-ui/src/pages/AskAI.tsx
  const clearChat = () => {
    localStorage.removeItem('ask-ai-conversation');
    setMessages([welcomeMessage]);
    setConversationContext({
      mentioned_devices: [],
      mentioned_intents: [],
      active_suggestions: [],
      last_query: '',
      last_entities: []
    });
    toast.success('Chat cleared');
  };
```

**What it does:**
- ✅ Clears localStorage conversation data
- ✅ Resets messages to welcome message only
- ✅ Resets conversation context
- ✅ Shows success toast notification
- ✅ Has a "Clear" button in the header (line 661-670)

**What's missing:**
- ❌ No confirmation dialog (risk of accidental clearing)
- ❌ Doesn't clear `processingActions` state
- ❌ Doesn't clear `testedSuggestions` state
- ❌ Doesn't clear `inputValue` state
- ❌ Doesn't reset `isLoading` or `isTyping` states
- ❌ No visual feedback/animation during clear
- ❌ Button could be more prominent/discoverable
- ❌ No option to export before clearing

---

## Proposed Enhancements

### 1. Add Confirmation Dialog ⭐ **PRIORITY 1**

**Rationale:** Prevent accidental clearing of valuable conversation history.

**Implementation:**
- Create a simple confirmation modal component (reuse patterns from `BatchActionModal.tsx`)
- Show dialog when "Clear" button is clicked
- Display:
  - Warning message
  - Message count that will be cleared
  - Option to export before clearing
  - "Clear & Start New" and "Cancel" buttons

**User Flow:**
```
User clicks "Clear" button
  ↓
Confirmation modal appears
  ↓
User can:
  - Export conversation first (optional)
  - Confirm clear (proceeds to clear)
  - Cancel (closes modal, no action)
```

### 2. Complete State Reset ⭐ **PRIORITY 1**

**Current gaps:** Some state variables are not reset:
- `processingActions` - Set of ongoing operations
- `testedSuggestions` - Set of tested suggestion IDs
- `inputValue` - Current input field value
- `isLoading` - Loading state flag
- `isTyping` - Typing indicator state

**Implementation:**
```typescript
const clearChat = () => {
  // Clear all state
  localStorage.removeItem('ask-ai-conversation');
  setMessages([welcomeMessage]);
  setInputValue(''); // Clear input field
  setIsLoading(false); // Reset loading
  setIsTyping(false); // Reset typing indicator
  setProcessingActions(new Set()); // Clear processing actions
  setTestedSuggestions(new Set()); // Clear tested suggestions
  setConversationContext({
    mentioned_devices: [],
    mentioned_intents: [],
    active_suggestions: [],
    last_query: '',
    last_entities: []
  });
  
  // Clear input field focus and scroll to top
  if (inputRef.current) {
    inputRef.current.value = '';
  }
  
  toast.success('Chat cleared - ready for a new conversation');
};
```

### 3. Enhanced UI/UX ⭐ **PRIORITY 2**

#### A. Better Button Design
- Change button text to "New Chat" or "Start New" (more intuitive)
- Add icon (refresh/plus icon)
- Improve visual prominence
- Add tooltip: "Clear conversation and start fresh"

#### B. Visual Feedback
- Add smooth fade-out animation when clearing messages
- Show loading state during clear operation
- Scroll to top smoothly after clearing
- Brief confirmation toast with message count cleared

#### C. Keyboard Shortcut
- Add `Ctrl+K` / `Cmd+K` shortcut to clear chat (common pattern in chat apps)
- Show hint in tooltip or help text

### 4. Export Before Clear Option ⭐ **PRIORITY 2**

**Feature:** Quick export button in confirmation modal

**User Flow:**
```
User clicks "Clear"
  ↓
Modal shows: "Export conversation before clearing?"
  ↓
[Export & Clear] [Clear] [Cancel]
```

**Implementation:**
- Add "Export & Clear" button in confirmation modal
- Calls `exportConversation()` then `clearChat()`
- Shows combined toast: "Conversation exported and cleared"

### 5. Undo Functionality (Future Enhancement) ⭐ **PRIORITY 3**

**Feature:** Ability to restore cleared conversation

**Implementation:**
- Store last conversation in a separate localStorage key (`ask-ai-last-cleared`)
- Show "Undo Clear" toast after clearing (similar to Gmail)
- Expires after 30 seconds or when new message is sent

---

## Implementation Plan

### Phase 1: Core Enhancements (2-3 hours)

**Files to Modify:**
1. `services/ai-automation-ui/src/pages/AskAI.tsx`
   - Enhance `clearChat()` function
   - Add state for confirmation modal
   - Update button UI

**Files to Create:**
2. `services/ai-automation-ui/src/components/ask-ai/ClearChatModal.tsx` (new)
   - Simple confirmation modal component
   - Reuse styling patterns from `BatchActionModal.tsx`
   - Include export option

**Tasks:**
- [ ] Create `ClearChatModal` component
- [ ] Add modal state to `AskAI.tsx`
- [ ] Enhance `clearChat()` to reset all state
- [ ] Update "Clear" button to open modal
- [ ] Add export option in modal
- [ ] Test state reset comprehensively

### Phase 2: UI Polish (1-2 hours)

**Tasks:**
- [ ] Update button design (text, icon, styling)
- [ ] Add fade-out animation for messages
- [ ] Improve toast messages
- [ ] Add tooltip to button
- [ ] Test animations and transitions

### Phase 3: Keyboard Shortcut (30 minutes)

**Tasks:**
- [ ] Add keyboard event listener for `Ctrl+K` / `Cmd+K`
- [ ] Update tooltip to mention shortcut
- [ ] Test shortcut on Windows/Mac

### Phase 4: Testing & Documentation (1 hour)

**Tasks:**
- [ ] Update `AskAIPage.ts` page object if needed
- [ ] Manual testing checklist
- [ ] Update component documentation

---

## Detailed Implementation Steps

### Step 1: Create ClearChatModal Component

**File:** `services/ai-automation-ui/src/components/ask-ai/ClearChatModal.tsx`

```typescript
/**
 * Clear Chat Confirmation Modal
 * 
 * Confirmation dialog for clearing the conversation history
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ClearChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  onExportAndClear?: () => void;
  messageCount: number;
  darkMode: boolean;
}

export const ClearChatModal: React.FC<ClearChatModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  onExportAndClear,
  messageCount,
  darkMode
}) => {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className={`relative max-w-md w-full rounded-2xl shadow-2xl p-6 ${
            darkMode ? 'bg-gray-800 text-white' : 'bg-white text-gray-900'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start gap-4 mb-6">
            <div className="text-4xl">🗑️</div>
            <div className="flex-1">
              <h2 className={`text-2xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                Clear Conversation?
              </h2>
              <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                This will clear all {messageCount} message{messageCount !== 1 ? 's' : ''} from this conversation.
                You can export the conversation before clearing if you want to save it.
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2">
            {onExportAndClear && (
              <button
                onClick={onExportAndClear}
                className={`w-full px-4 py-3 rounded-lg font-medium transition-colors ${
                  darkMode
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                📥 Export & Clear
              </button>
            )}
            <button
              onClick={onConfirm}
              className={`w-full px-4 py-3 rounded-lg font-medium transition-colors ${
                darkMode
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-red-600 hover:bg-red-700 text-white'
              }`}
            >
              Clear Conversation
            </button>
            <button
              onClick={onClose}
              className={`w-full px-4 py-3 rounded-lg font-medium transition-colors border ${
                darkMode
                  ? 'border-gray-600 hover:bg-gray-700 text-gray-300'
                  : 'border-gray-300 hover:bg-gray-50 text-gray-700'
              }`}
            >
              Cancel
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
```

### Step 2: Update AskAI.tsx

**Key Changes:**

1. **Import modal:**
```typescript
import { ClearChatModal } from '../components/ask-ai/ClearChatModal';
```

2. **Add modal state:**
```typescript
const [showClearModal, setShowClearModal] = useState(false);
```

3. **Enhanced clearChat function:**
```typescript
const clearChat = () => {
  // Clear localStorage
  localStorage.removeItem('ask-ai-conversation');
  
  // Reset all state
  setMessages([welcomeMessage]);
  setInputValue('');
  setIsLoading(false);
  setIsTyping(false);
  setProcessingActions(new Set());
  setTestedSuggestions(new Set());
  setConversationContext({
    mentioned_devices: [],
    mentioned_intents: [],
    active_suggestions: [],
    last_query: '',
    last_entities: []
  });
  
  // Clear input field
  if (inputRef.current) {
    inputRef.current.value = '';
    inputRef.current.focus();
  }
  
  // Scroll to top
  if (messagesEndRef.current) {
    messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }
  
  // Close modal and show toast
  setShowClearModal(false);
  const messageCount = messages.length - 1; // Exclude welcome message
  toast.success(`Chat cleared! (${messageCount} message${messageCount !== 1 ? 's' : ''} removed)`);
};
```

4. **Add export and clear handler:**
```typescript
const handleExportAndClear = () => {
  exportConversation();
  // Small delay to ensure export completes
  setTimeout(() => {
    clearChat();
  }, 500);
};
```

5. **Update button:**
```typescript
<button
  onClick={() => setShowClearModal(true)}
  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
    darkMode
      ? 'border-gray-600 text-gray-300 hover:bg-gray-700 border'
      : 'border-gray-300 text-gray-600 hover:bg-gray-50 border'
  }`}
  title="Clear conversation (Ctrl+K)"
>
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
  </svg>
  New Chat
</button>
```

6. **Add keyboard shortcut:**
```typescript
// Add keyboard shortcut
useEffect(() => {
  const handleKeyPress = (e: KeyboardEvent) => {
    // Ctrl+K or Cmd+K
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      if (messages.length > 1) { // Only if there are messages to clear
        setShowClearModal(true);
      }
    }
  };
  
  window.addEventListener('keydown', handleKeyPress);
  return () => window.removeEventListener('keydown', handleKeyPress);
}, [messages.length]);
```

7. **Add modal to JSX:**
```typescript
{/* Clear Chat Modal */}
<ClearChatModal
  isOpen={showClearModal}
  onClose={() => setShowClearModal(false)}
  onConfirm={clearChat}
  onExportAndClear={handleExportAndClear}
  messageCount={messages.length - 1} // Exclude welcome message
  darkMode={darkMode}
/>
```

---

## Testing Checklist

### Manual Testing

- [ ] Click "New Chat" button - modal appears
- [ ] Modal shows correct message count
- [ ] Click "Cancel" - modal closes, no clearing
- [ ] Click "Clear Conversation" - all messages cleared, state reset
- [ ] Click "Export & Clear" - exports then clears
- [ ] Verify input field is cleared
- [ ] Verify scroll position resets
- [ ] Verify toast notification appears
- [ ] Test keyboard shortcut `Ctrl+K` / `Cmd+K`
- [ ] Test in dark mode
- [ ] Test with 0 messages (should not open modal)
- [ ] Test with many messages (50+)
- [ ] Verify localStorage is cleared
- [ ] Refresh page after clearing - should show welcome message only

### Automated Testing

- [ ] Update `AskAIPage.ts` if needed
- [ ] Add test for modal opening/closing
- [ ] Add test for clear functionality
- [ ] Add test for export and clear
- [ ] Add test for keyboard shortcut

---

## Acceptance Criteria

✅ **Must Have:**
- Confirmation modal prevents accidental clearing
- All state is properly reset (messages, context, actions, suggestions, input)
- Button is clear and discoverable
- Export option available in modal
- Toast notification confirms action

✅ **Should Have:**
- Keyboard shortcut (`Ctrl+K` / `Cmd+K`)
- Smooth animations
- Improved button design with icon

✅ **Nice to Have:**
- Undo functionality (future phase)

---

## Files Summary

### Files to Create:
- `services/ai-automation-ui/src/components/ask-ai/ClearChatModal.tsx` (~120 lines)

### Files to Modify:
- `services/ai-automation-ui/src/pages/AskAI.tsx` (~50 lines changed)

### Files to Test:
- `tests/e2e/page-objects/AskAIPage.ts` (verify compatibility)

---

## Estimated Effort

- **Phase 1 (Core):** 2-3 hours
- **Phase 2 (UI Polish):** 1-2 hours
- **Phase 3 (Keyboard Shortcut):** 30 minutes
- **Phase 4 (Testing):** 1 hour

**Total:** 4.5 - 6.5 hours

---

## Notes

- Reuse modal patterns from `BatchActionModal.tsx` for consistency
- Follow existing dark mode styling patterns
- Ensure accessibility (keyboard navigation, ARIA labels)
- Consider mobile responsiveness for modal
- Keep animations smooth but not distracting

