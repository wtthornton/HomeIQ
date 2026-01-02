# Step 1: Enhanced Prompt - Debug Tab Integration

## Original Request
Add Debug tab to AutomationPreview component - integrate DebugTab component with tabbed interface (Preview and Debug tabs) to show prompt breakdown, system prompt, injected context, conversation history, and token counts for debugging automation generation.

## Enhanced Requirements

### Functional Requirements
1. **Tabbed Interface**: Add tab navigation with "Preview" and "Debug" tabs
2. **Preview Tab**: Display automation YAML with syntax highlighting (existing functionality)
3. **Debug Tab**: Integrate existing DebugTab component to show:
   - System prompt breakdown
   - Injected context (Tier 1)
   - Preview context
   - Complete system prompt
   - User message
   - Conversation history
   - Full assembled messages
   - Token counts and budget analysis
4. **State Management**: Track active tab state ('preview' | 'debug')
5. **Conversation ID**: Pass conversationId prop to DebugTab component

### Non-Functional Requirements
- Maintain existing functionality (validation, creation, editing)
- Preserve dark mode support
- Ensure responsive layout
- Maintain accessibility standards
- No performance degradation

## Architecture Guidance
- Use React state for tab management
- Reuse existing DebugTab component (no duplication)
- Maintain component prop interface compatibility
- Follow existing styling patterns (Tailwind CSS)

## Quality Standards
- Overall Score: ≥ 70
- Maintainability: ≥ 7.0
- Test Coverage: ≥ 80% (target)
