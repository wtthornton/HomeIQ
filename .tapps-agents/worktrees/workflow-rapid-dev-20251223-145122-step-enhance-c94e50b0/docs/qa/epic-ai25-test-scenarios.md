# Epic AI-25: HA Agent UI Enhancements - Test Scenarios

**Epic:** AI-25 - HA Agent UI Enhancements  
**QA Agent:** Quinn (Test Architect & Quality Advisor)  
**Date:** January 2025  
**Status:** 🧪 Test Execution

---

## Test Strategy

### Risk Assessment
- **Risk Level:** Medium
- **Impact:** High (User-facing UI changes)
- **Probability:** Medium (New components, integration points)
- **Test Depth:** Comprehensive (All stories, edge cases, integration)

### Test Coverage
- ✅ Unit Tests: Parser utility, component logic
- ✅ Integration Tests: Component integration with chat interface
- ✅ Manual Tests: UI rendering, user workflows, edge cases
- ✅ Performance Tests: Parsing speed, render performance

---

## Story AI25.1: Structured Proposal Rendering

### Test Scenario 1.1: Proposal Detection
**Given:** A chat message with proposal format  
**When:** `isProposalMessage()` is called  
**Then:** Returns `true` for valid proposals

**Test Cases:**
- ✅ Standard format: "Here's what I'll create for you:"
- ✅ Case variations: "here's what i'll create", "HERE'S WHAT"
- ✅ With/without punctuation
- ✅ Edge case: Empty string → `false`
- ✅ Edge case: Non-proposal text → `false`

### Test Scenario 1.2: Proposal Parsing
**Given:** A valid proposal message  
**When:** `parseProposal()` is called  
**Then:** Returns structured sections array

**Test Cases:**
- ✅ All 4 sections present (what, when, affected, how)
- ✅ Missing sections (partial proposals)
- ✅ Out-of-order sections
- ✅ Sections with emojis (✨, 📋, 🎯, ⚙️)
- ✅ Sections without emojis
- ✅ Malformed markdown (extra asterisks, missing colons)
- ✅ Long content (multi-line sections)
- ✅ Special characters in content

### Test Scenario 1.3: AutomationProposal Component Rendering
**Given:** Parsed proposal sections  
**When:** Component renders  
**Then:** Displays structured visual cards

**Test Cases:**
- ✅ All sections render correctly
- ✅ Color coding per section type
- ✅ Dark mode styling
- ✅ Light mode styling
- ✅ Responsive design (mobile/desktop)
- ✅ Animation on mount
- ✅ Empty sections array (graceful handling)
- ✅ Long content (text wrapping, scrolling)

### Test Scenario 1.4: Integration with Chat Interface
**Given:** Assistant message with proposal  
**When:** Message renders in chat  
**Then:** Shows AutomationProposal component

**Test Cases:**
- ✅ Proposal detected and rendered
- ✅ Non-proposal messages render normally
- ✅ Mixed content (proposal + regular text)
- ✅ Multiple proposals in conversation
- ✅ Proposal with automation YAML
- ✅ Proposal with tool calls

---

## Story AI25.2: Interactive CTA Buttons & Markdown Rendering

### Test Scenario 2.1: Markdown Rendering
**Given:** Message with markdown content  
**When:** MessageContent component renders  
**Then:** Formats markdown correctly

**Test Cases:**
- ✅ Bold text (`**text**`)
- ✅ Bullet lists (`- item`)
- ✅ Numbered lists (`1. item`)
- ✅ Code blocks (```yaml ... ```)
- ✅ Inline code (`code`)
- ✅ Links (`[text](url)`)
- ✅ Headings (`# H1`, `## H2`)
- ✅ Emojis (✨, 🚀, etc.)
- ✅ Mixed markdown
- ✅ Dark mode styling
- ✅ Light mode styling
- ✅ Malformed markdown (graceful handling)

### Test Scenario 2.2: CTA Button Detection
**Given:** Message with CTA prompt  
**When:** CTAActionButtons component checks message  
**Then:** Detects CTA and renders buttons

**Test Cases:**
- ✅ "Say 'approve', 'create', 'yes', or 'go ahead'!"
- ✅ "Ready to create this?"
- ✅ Case variations
- ✅ No CTA prompt → buttons not shown
- ✅ Multiple CTA prompts → buttons shown once

### Test Scenario 2.3: CTA Button Functionality
**Given:** CTA buttons rendered  
**When:** User clicks button  
**Then:** Creates automation via API

**Test Cases:**
- ✅ "Approve" button → calls create_automation_from_prompt
- ✅ "Create" button → calls create_automation_from_prompt
- ✅ "Yes" button → calls create_automation_from_prompt
- ✅ "Go Ahead" button → calls create_automation_from_prompt
- ✅ Loading state during creation
- ✅ Success state (shows automation ID)
- ✅ Error handling (API failure)
- ✅ Missing YAML → shows error toast
- ✅ Already created → shows success message

### Test Scenario 2.4: YAML Extraction
**Given:** Message with automation YAML  
**When:** CTAActionButtons extracts YAML  
**Then:** Uses YAML for automation creation

**Test Cases:**
- ✅ YAML in code block (```yaml ... ```)
- ✅ YAML provided as prop
- ✅ YAML from detectAutomation()
- ✅ Missing YAML → error handling
- ✅ Invalid YAML → error handling

### Test Scenario 2.5: Integration with Chat
**Given:** Assistant message with CTA  
**When:** Message renders  
**Then:** Shows CTA buttons below message

**Test Cases:**
- ✅ CTA buttons appear for assistant messages
- ✅ CTA buttons appear for proposals
- ✅ CTA buttons don't appear for user messages
- ✅ Multiple messages with CTAs
- ✅ Conversation refresh after creation

---

## Story AI25.3: Enhancement Button Warning Indicator

### Test Scenario 3.1: Prerequisite Checking
**Given:** EnhancementButton component  
**When:** Prerequisites checked  
**Then:** Returns correct state

**Test Cases:**
- ✅ All prerequisites present → enabled
- ✅ Missing conversationId → disabled
- ✅ Missing automationYaml → disabled
- ✅ Missing originalPrompt → disabled
- ✅ Multiple missing → shows all in tooltip

### Test Scenario 3.2: Warning Indicator Display
**Given:** Missing prerequisites  
**When:** Button renders  
**Then:** Shows warning state

**Test Cases:**
- ✅ Warning icon (⚠️) displayed
- ✅ Yellow border on button
- ✅ Disabled state (cursor-not-allowed)
- ✅ Tooltip shows missing prerequisites
- ✅ Tooltip positioned correctly
- ✅ Dark mode tooltip styling
- ✅ Light mode tooltip styling

### Test Scenario 3.3: Button States
**Given:** EnhancementButton component  
**When:** State changes  
**Then:** Visual feedback updates

**Test Cases:**
- ✅ Enabled state (✨ icon, purple background)
- ✅ Disabled/warning state (⚠️ icon, yellow border)
- ✅ Loading state (spinner, disabled)
- ✅ State transitions smooth

### Test Scenario 3.4: Integration
**Given:** Chat interface  
**When:** Enhancement button shown  
**Then:** Warning state updates dynamically

**Test Cases:**
- ✅ Warning appears when prerequisites missing
- ✅ Warning disappears when prerequisites added
- ✅ Button enables when all prerequisites present
- ✅ Works with proposal messages
- ✅ Works with regular messages

---

## Integration Tests

### Test Scenario I.1: Full Workflow
**Given:** User requests automation  
**When:** AI generates proposal  
**Then:** All enhancements work together

**Test Cases:**
- ✅ Proposal renders with structured sections
- ✅ Markdown formatted correctly
- ✅ CTA buttons appear
- ✅ Enhancement button shows correct state
- ✅ User can approve via CTA button
- ✅ User can enhance via enhancement button
- ✅ All components work in dark mode
- ✅ All components work in light mode

### Test Scenario I.2: Edge Cases
**Given:** Various edge cases  
**When:** Components handle edge cases  
**Then:** Graceful degradation

**Test Cases:**
- ✅ Empty messages
- ✅ Very long messages
- ✅ Malformed markdown
- ✅ Missing sections in proposals
- ✅ Special characters
- ✅ Unicode characters
- ✅ Multiple rapid interactions
- ✅ Network failures

### Test Scenario I.3: Performance
**Given:** Large messages/conversations  
**When:** Components render  
**Then:** Acceptable performance

**Test Cases:**
- ✅ Parsing speed (< 10ms for typical proposal)
- ✅ Render performance (< 100ms for component)
- ✅ Memory usage (no leaks)
- ✅ Large conversation (100+ messages)
- ✅ Multiple proposals in conversation

---

## Test Execution Plan

### Phase 1: Unit Tests
1. Test proposalParser.ts functions
2. Test component logic (props, state)
3. Test edge cases

### Phase 2: Integration Tests
1. Test component integration
2. Test API interactions
3. Test state management

### Phase 3: Manual Tests
1. Visual rendering verification
2. User workflow testing
3. Browser compatibility
4. Responsive design

### Phase 4: Performance Tests
1. Parsing performance
2. Render performance
3. Memory profiling

---

## Test Results

_To be filled during test execution_

---

## Risk Assessment

### High Risk Areas
- YAML extraction from messages (could fail silently)
- API integration (network failures)
- State management (conversation refresh)

### Medium Risk Areas
- Proposal parsing (edge cases)
- Markdown rendering (malformed content)
- Component integration (multiple components)

### Low Risk Areas
- Visual styling (dark/light mode)
- Animation performance
- Tooltip positioning

---

**Last Updated:** January 2025  
**Next Review:** After test execution

