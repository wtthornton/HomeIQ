# Task 1.1: Add Context7 Awareness to Architect Agent

## Task Information
- **Story**: Context7 MCP Integration Implementation Plan
- **Task ID**: 1.1
- **Priority**: High
- **Estimate**: 5 minutes
- **Status**: Pending

## Task Description
Add Context7 MCP tool awareness to the architect agent persona so that Winston (the architect) knows about Context7 capabilities and can suggest their use when making technology decisions.

## Acceptance Criteria
- [ ] Context7 awareness added to architect agent core_principles
- [ ] Winston can mention Context7 when making technology decisions
- [ ] No existing architect functionality is broken
- [ ] Change is easily reversible

## Implementation Steps

### Step 1: Locate Architect Agent File
- File: `.bmad-core/agents/architect.md`
- Section: `core_principles` (around line 45-55)

### Step 2: Add Context7 Principle
Add this line to the `core_principles` section:
```yaml
core_principles:
  - Context7 Integration - Use Context7 MCP tools (mcp_Context7_resolve-library-id, mcp_Context7_get-library-docs) for up-to-date library documentation when making technology decisions
```

### Step 3: Validate Change
- Verify YAML syntax is correct
- Ensure no existing principles are modified
- Test that architect agent still loads correctly

## Files to Modify
- `.bmad-core/agents/architect.md`

## Testing
- [ ] Architect agent loads without errors
- [ ] Winston mentions Context7 when relevant
- [ ] No existing architect functionality is broken

## Rollback Plan
Remove the added Context7 principle line from `.bmad-core/agents/architect.md`

## Success Criteria
- Context7 awareness successfully added to architect agent
- Winston can suggest Context7 usage for technology decisions
- Change is easily reversible
