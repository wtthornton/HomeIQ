# Task 2.1: Add Context7 Commands to BMad Master Agent

## Task Information
- **Story**: Context7 MCP Integration Implementation Plan
- **Task ID**: 2.1
- **Priority**: High
- **Estimate**: 10 minutes
- **Status**: Pending

## Task Description
Add Context7 MCP tool commands to the BMad Master agent so that users can directly invoke Context7 functionality through BMad commands.

## Acceptance Criteria
- [ ] Context7 commands added to BMad Master agent
- [ ] Commands follow BMad command naming conventions
- [ ] Commands are properly documented
- [ ] No existing BMad Master functionality is broken

## Implementation Steps

### Step 1: Locate BMad Master Agent File
- File: `.bmad-core/agents/bmad-master.md`
- Section: `commands` (around line 52-62)

### Step 2: Add Context7 Commands
Add these commands to the `commands` section:
```yaml
commands:
  - context7-resolve {library}: Resolve library name to Context7-compatible library ID
  - context7-docs {library} {topic}: Get focused documentation for library with optional topic
  - context7-help: Show Context7 usage examples and best practices
```

### Step 3: Add Context7 Task to Dependencies
Add to the `dependencies` section:
```yaml
dependencies:
  tasks:
    - context7-simple.md
```

### Step 4: Validate Changes
- Verify YAML syntax is correct
- Ensure no existing commands are modified
- Test that BMad Master agent still loads correctly

## Files to Modify
- `.bmad-core/agents/bmad-master.md`

## Testing
- [ ] BMad Master agent loads without errors
- [ ] Context7 commands appear in help output
- [ ] No existing BMad Master functionality is broken

## Rollback Plan
Remove the added Context7 commands and task dependency from `.bmad-core/agents/bmad-master.md`

## Success Criteria
- Context7 commands successfully added to BMad Master agent
- Users can invoke Context7 functionality through BMad commands
- Change is easily reversible
