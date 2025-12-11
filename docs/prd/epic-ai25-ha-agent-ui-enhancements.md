# Epic AI-25: HA Agent UI Enhancements - Brownfield Enhancement

## Epic Goal

Enhance the HA Agent chat interface to provide structured automation proposal rendering, interactive call-to-action buttons, and improved markdown formatting to match the AI-generated proposal format and improve user experience.

## Epic Description

### Existing System Context

- **Current Functionality**: The HA Agent chat interface displays automation proposals as raw markdown text in chat bubbles. The AI generates structured proposals with sections (What it does, When it runs, What's affected, How it works), but these are displayed as plain text without visual formatting or interactive elements.

- **Technology Stack**: 
  - React 18.3.1 with TypeScript 5.6.3
  - TailwindCSS 3.4.13 for styling
  - Framer Motion for animations
  - React Syntax Highlighter for YAML display
  - Located in `services/ai-automation-ui/`

- **Integration Points**: 
  - `services/ai-automation-ui/src/pages/HAAgentChat.tsx` - Main chat component
  - `services/ai-automation-ui/src/components/ha-agent/` - Component library
  - `services/ha-ai-agent-service/src/prompts/system_prompt.py` - AI prompt format
  - `services/ha-ai-agent-service/src/services/enhancement_service.py` - Enhancement service

### Enhancement Details

**What's being added/changed:**

1. **Structured Proposal Rendering Component**: Parse and render AI-generated automation proposals with visual sections (What it does, When it runs, What's affected, How it works) instead of raw markdown text.

2. **Interactive Call-to-Action Buttons**: Replace text prompts like "Say 'approve', 'create', 'yes', or 'go ahead'!" with actual interactive buttons that trigger automation creation.

3. **Enhanced Markdown Rendering**: Improve markdown rendering in chat messages to properly display bold text, bullet lists, emojis, and structured content.

4. **Enhancement Button Warning Indicator**: Add persistent visual indicator when automation YAML and original prompt are missing (currently only shows as toast).

5. **Conditional Statement Handling**: Add interactive elements for conditional statements (e.g., "If your sensor has a different entity ID...").

**How it integrates:**

- Extends existing `HAAgentChat.tsx` component with new parsing logic
- Creates new `AutomationProposal.tsx` component for structured rendering
- Enhances `MessageBubble.tsx` (or creates if doesn't exist) for better markdown rendering
- Updates `EnhancementButton.tsx` to show persistent warning state
- Integrates with existing `AutomationPreview` modal and enhancement flow

**Success criteria:**

- Automation proposals display with structured sections (What it does, When it runs, What's affected, How it works) in visually distinct cards/sections
- Users can click "Approve", "Create", "Yes", or "Go Ahead" buttons to create automations directly
- Markdown formatting (bold, bullets, emojis) renders correctly in chat messages
- Enhancement button shows persistent warning when prerequisites are missing
- Conditional statements have interactive elements for user input
- All existing functionality remains intact
- No performance degradation

### Technology Research

- **React Markdown Libraries**: Research best practices for rendering markdown in React (react-markdown, marked, etc.)
- **MANDATORY**: Use Context7 KB-first commands (*context7-docs, *context7-resolve) when researching external libraries
- **ALWAYS**: Check KB cache first before fetching from Context7 API

## Stories

1. **Story AI25.1**: Create structured automation proposal rendering component
   - Parse AI-generated proposal format (What it does, When it runs, What's affected, How it works)
   - Create visual component with section cards
   - Integrate with existing chat message display

2. **Story AI25.2**: Add interactive call-to-action buttons and enhanced markdown rendering
   - Replace text prompts with interactive buttons (Approve, Create, Yes, Go Ahead)
   - Implement markdown rendering improvements for chat messages
   - Connect buttons to automation creation flow

3. **Story AI25.3**: Add enhancement button warning indicator and conditional statement handling
   - Add persistent visual warning for missing prerequisites
   - Implement interactive elements for conditional statements
   - Test and verify all enhancements

## Compatibility Requirements

- [x] Existing APIs remain unchanged
- [x] Database schema changes are backward compatible (N/A - UI only)
- [x] UI changes follow existing TailwindCSS patterns
- [x] Performance impact is minimal (client-side rendering only)
- [x] Existing automation creation flow remains functional
- [x] Enhancement button functionality preserved

## Risk Mitigation

**Primary Risk:** Breaking existing chat functionality or automation creation flow

**Mitigation:**
- Implement new components alongside existing code
- Maintain backward compatibility with existing message format
- Add feature flags for gradual rollout if needed
- Comprehensive testing of existing flows

**Rollback Plan:**
- Revert to previous message rendering if issues occur
- Keep existing text-based CTA as fallback
- All changes are in UI layer, no backend changes required

## Definition of Done

- [x] All stories completed with acceptance criteria met
- [x] Structured proposal rendering displays correctly for all proposal formats (AutomationProposal component)
- [x] Interactive CTA buttons successfully create automations (CTAActionButtons component)
- [x] Markdown rendering works for all message types (MessageContent component with react-markdown)
- [x] Enhancement button warning indicator displays correctly (persistent tooltip in EnhancementButton)
- [x] Conditional statement handling implemented (via proposalParser utility)
- [x] Existing functionality verified through testing
- [x] No regression in existing features
- [x] Code follows project coding standards (complexity ≤ 15, maintainability ≥ 65)
- [x] Documentation updated appropriately

## Related Epics

- Epic AI-20: HA AI Agent Completion & Production Readiness (base chat functionality)
- Epic AI-19: HA AI Agent Tier 1 Context Injection (AI prompt format)

