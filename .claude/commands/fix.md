# Fix Command (Simple Mode)

Fix bugs and errors with systematic debugging workflow.

## Usage

```
@fix <file-path> "<description>"
```

Or with natural language:
```
Fix the null pointer error in src/api/auth.py
Debug and fix the authentication issue
Resolve the bug in login.py
```

## What It Does

Executes a complete fix workflow:

1. **Debug Error** - Analyzes error and finds root cause
2. **Implement Fix** - Applies the fix to resolve the issue
3. **Test Fix** - Generates/updates tests to verify the fix
4. **Validate** - Ensures fix doesn't break existing functionality

## Examples

```
@fix src/api/auth.py "Fix the null pointer error on line 42"
@fix src/api/auth.py "Resolve the authentication token validation issue"
@fix src/models/user.py "Fix the email validation bug"
```

## Features

- **Systematic Debugging**: Finds root cause, not just symptoms
- **Automatic Fix**: Implements the fix based on analysis
- **Test Verification**: Ensures fix works correctly
- **Quality Check**: Verifies fix doesn't introduce new issues

## Output

- Root cause analysis
- Fixed code file
- Test updates
- Validation results

## Integration

- **Cursor**: Use `@simple-mode *fix <file> "<desc>"` (Cursor Skill)
- **Claude Desktop**: Use `@fix <file> "<desc>"` (this command)
- **CLI**: Use `tapps-agents simple-mode fix --file <file> --prompt "<desc>"`

