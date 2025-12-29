# AI Agent Crash Fix Plan

**Created:** 2025-01-23  
**Status:** 🔴 CRITICAL - Active Issue  
**Priority:** High  
**Type:** Stability / Reliability  

## Problem Summary

The AI agent keeps crashing due to connection errors. The error message shows:
```
Connection failed. If the problem persists, please check your internet connection or VPN
```

### Root Causes Identified

1. **Connection Errors During Tool Calls**
   - Cursor Skills API calls failing
   - Context7 API calls timing out
   - Background Agent API connection issues
   - No retry logic for transient failures

2. **Token Budget Exceeded**
   - Long conversation history
   - Large context windows
   - No automatic context management

3. **No Error Recovery**
   - Crashes instead of graceful degradation
   - No circuit breaker pattern
   - No exponential backoff

4. **Context Window Overflow**
   - Too many files open
   - Large codebase context
   - No context pruning

## Immediate Workarounds

### 1. Start New Conversations Frequently

**Problem:** Long conversations accumulate context and exceed token limits.

**Solution:**
- Start a new chat (`Cmd/Ctrl + L`) every 20-30 messages
- Close files when done editing
- Use focused queries instead of broad requests

**When to Start New Chat:**
- ✅ After completing a feature/epic
- ✅ When you see "Connection Error" messages
- ✅ When responses become slow
- ✅ When context feels "heavy"

### 2. Reduce Context Size

**Problem:** Too many files open or large context windows.

**Solution:**
- Close unused files (`Cmd/Ctrl + W`)
- Use file references (`@filename`) instead of opening all files
- Use `.cursorignore` to exclude large files
- Focus on specific directories

**Best Practices:**
```bash
# Check .cursorignore includes:
.venv/
__pycache__/
.tapps-agents/kb/
.tapps-agents/cache/
.tapps-agents/sessions/
reports/
```

### 3. Use Smaller Batch Sizes

**Problem:** Batch operations cause connection pool exhaustion.

**Solution:**
- Review single files instead of batches
- Use `@simple-mode *review {file}` instead of batch reviews
- Process files one at a time for critical operations

**Instead of:**
```bash
# ❌ BAD: Batch review can crash
python -m tapps_agents.cli reviewer review services/**/*.py
```

**Use:**
```bash
# ✅ GOOD: Single file review
@simple-mode *review services/websocket-ingestion/src/main.py
```

### 4. Avoid Long-Running Operations

**Problem:** Long operations increase chance of connection errors.

**Solution:**
- Break large tasks into smaller chunks
- Use `--auto` flag sparingly
- Monitor for connection errors during execution

**Example:**
```bash
# ❌ BAD: Long-running workflow
python -m tapps_agents.cli workflow full --prompt "Build entire system" --auto

# ✅ GOOD: Smaller, focused workflows
@simple-mode *build "Create authentication service"
@simple-mode *build "Create data API service"
```

## Best Practices to Prevent Crashes

### 1. Use Simple Mode for Standard Tasks

**Why:** Simple Mode has built-in error handling and retry logic.

**Commands:**
```bash
@simple-mode *build "Feature description"
@simple-mode *review {file}
@simple-mode *fix {file} "Bug description"
@simple-mode *test {file}
```

**Benefits:**
- Automatic retry logic
- Graceful error handling
- Quality gates prevent bad code
- Smaller context windows

### 2. Monitor Connection Health

**Check Service Health:**
```powershell
# Check all services
$services = @(
    @{Name="websocket-ingestion"; Port=8001},
    @{Name="data-api"; Port=8006},
    @{Name="ha-ai-agent-service"; Port=8030}
)

foreach ($service in $services) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:$($service.Port)/health"
        Write-Host "$($service.Name): $($health.status)" -ForegroundColor Green
    } catch {
        Write-Host "$($service.Name): FAILED" -ForegroundColor Red
    }
}
```

### 3. Use Offline Alternatives When Available

**When Connection Errors Occur:**
- Use local code analysis instead of API calls
- Use cached Context7 documentation
- Skip non-critical operations

**Example:**
```bash
# Use local scoring instead of full review
python -m tapps_agents.cli reviewer score {file}

# Use cached docs instead of API calls
# Context7 KB cache is checked first automatically
```

### 4. Implement Circuit Breaker Pattern

**For Custom Code:**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
    
    def should_allow(self) -> bool:
        if not self.is_open:
            return True
        
        if self.last_failure_time:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.reset_timeout:
                self.is_open = False
                self.failure_count = 0
                return True
        
        return False
```

## Long-Term Fixes

### 1. Add Retry Logic to Tool Calls

**Location:** `TappsCodingAgents/tapps_agents/workflow/cursor_executor.py`

**Fix:** Add retry logic with exponential backoff for connection errors:

```python
async def _invoke_skill_with_retry(
    self,
    skill_command: str,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Invoke skill with retry logic for connection errors."""
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            result = await self._invoke_skill(skill_command)
            return result
        except (ConnectionError, TimeoutError, OSError) as e:
            last_error = e
            if attempt < max_retries:
                backoff = min(2 ** attempt, 10.0)  # Exponential backoff, max 10s
                await asyncio.sleep(backoff)
                continue
            raise
    
    raise ConnectionError(f"Failed after {max_retries} attempts: {last_error}")
```

### 2. Implement Context Management

**Add Automatic Context Pruning:**
- Track token usage
- Automatically close old files
- Prune conversation history
- Warn before token limit

### 3. Add Connection Health Monitoring

**Monitor Connection State:**
- Track connection success/failure rates
- Implement circuit breaker at framework level
- Provide connection status in UI
- Auto-retry with exponential backoff

### 4. Improve Error Messages

**Better Error Reporting:**
- Distinguish retryable vs non-retryable errors
- Provide actionable recovery steps
- Show connection status
- Suggest workarounds

## Detection and Prevention

### Signs of Impending Crash

**Watch for:**
- ⚠️ Slow response times
- ⚠️ "Connection Error" messages appearing
- ⚠️ Tool calls timing out
- ⚠️ Context window warnings
- ⚠️ Multiple retry attempts

**Action:** Start new chat immediately when you see these signs.

### Prevention Checklist

Before starting a new task:
- [ ] Close unused files
- [ ] Check `.cursorignore` excludes large files
- [ ] Start new chat if previous chat was long
- [ ] Use Simple Mode for standard tasks
- [ ] Break large tasks into smaller chunks
- [ ] Monitor connection health

## Quick Reference

### When Connection Errors Occur

1. **Immediate Actions:**
   - Click "Try again" button
   - If fails, start new chat (`Cmd/Ctrl + L`)
   - Close unused files
   - Reduce context size

2. **If Persists:**
   - Check service health (see above)
   - Verify internet/VPN connection
   - Use offline alternatives
   - Report issue with error details

3. **Prevention:**
   - Use Simple Mode commands
   - Start new chats frequently
   - Keep context small
   - Monitor for warning signs

### Commands That Are Safer

**Low Risk (Use These):**
- `@simple-mode *review {file}` - Single file, built-in retry
- `@simple-mode *test {file}` - Focused operation
- `python -m tapps_agents.cli reviewer score {file}` - Local operation
- `python -m tapps_agents.cli reviewer lint {file}` - Local operation

**Higher Risk (Use Carefully):**
- Batch operations (`reviewer review **/*.py`)
- Long-running workflows (`workflow full --auto`)
- Large context operations
- Multiple parallel tool calls

## Related Issues

- **REVIEWER_BATCH_CRASH_ANALYSIS.md** - Batch processing crash analysis
- **TAPPS_AGENTS_WORKFLOW_EXECUTION_NOT_RUNNING_ISSUE.md** - Workflow execution issues
- **ERROR_HANDLING.md** - Service error handling patterns

## Status

**Current:** 🔴 Active issue - crashes occurring  
**Next Steps:**
1. ✅ Document workarounds (this file)
2. ⏳ Implement retry logic in framework
3. ⏳ Add context management
4. ⏳ Add connection health monitoring
5. ⏳ Improve error messages

## Updates

- **2025-01-23**: Initial fix plan created with workarounds and long-term solutions

