# Fix Bug

Debug and fix a bug in HomeIQ using structured debugging workflow.

## Instructions

Execute the Simple Mode fix workflow:

```
@simple-mode *fix {{file_path}} "{{bug_description}}"
```

This orchestrates:
1. **@debugger** - Analyze error, find root cause
2. **@implementer** - Apply fix
3. **@tester** - Verify fix with tests

## For PowerShell Users

**DO NOT use `docker-compose exec` with Python commands!**

Instead, use API endpoints:
```powershell
# Check service health
$health = Invoke-RestMethod -Uri "http://localhost:{{port}}/health"
$health.status

# Get logs
docker-compose logs --tail=100 {{service_name}}
```

## Parameters

- `file_path`: Path to the file with the bug
- `bug_description`: Description of the bug/error
