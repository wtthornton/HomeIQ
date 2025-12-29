# Debug Command

Analyze errors and find root causes with systematic debugging.

## Usage

```
@debug "<error-description>" --file <file-path>
```

Or with natural language:
```
Debug the null pointer error in src/api/auth.py
Fix the authentication error in login.py
Analyze why the API is returning 500 errors
```

## What It Does

1. **Analyzes Error**: Examines error messages, stack traces, and code
2. **Identifies Root Cause**: Finds the underlying issue
3. **Suggests Fix**: Provides specific fix recommendations
4. **Validates Solution**: Ensures fix resolves the issue

## Examples

```
@debug "Null pointer exception on line 42" --file src/api/auth.py
@debug "Authentication failed with invalid token" --file src/api/auth.py
@debug "TypeError: 'NoneType' object has no attribute 'name'" --file src/models/user.py
```

## Features

- **Error Analysis**: Parses error messages and stack traces
- **Code Tracing**: Traces execution flow to find issue
- **Root Cause**: Identifies underlying problem, not just symptoms
- **Fix Suggestions**: Provides specific code fixes
- **Validation**: Verifies fix resolves the issue

## Output

- Root cause analysis
- Specific fix recommendations
- Code examples for fixes
- Validation of solution

## Integration

- **Cursor**: Use `@debugger *debug "<error>" --file <file>` (Cursor Skill)
- **Claude Desktop**: Use `@debug "<error>" --file <file>` (this command)
- **CLI**: Use `tapps-agents debugger debug "<error>" --file <file>`

