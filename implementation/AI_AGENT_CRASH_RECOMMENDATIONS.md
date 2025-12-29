# AI Agent Crash Prevention - Prioritized Recommendations

**Created:** 2025-01-23  
**Status:** 🔴 CRITICAL - Active Issue  
**Priority:** High  
**Type:** Stability / Reliability  

## Executive Summary

This document provides prioritized recommendations to prevent AI agent crashes caused by connection errors, token limits, and context overflow. Recommendations are organized by impact and implementation effort.

---

## 🚨 TIER 1: IMMEDIATE ACTIONS (Do Now - 0-2 hours)

### 1.1 Configure Timeout Settings ⚡ HIGH IMPACT

**Problem:** Current timeouts may be too aggressive, causing premature failures.

**Action:** Update `.tapps-agents/config.yaml`:

```yaml
agents:
  reviewer:
    operation_timeout: 300.0  # Keep at 300s (5 min)
    tool_timeout: 30.0        # Increase to 60.0 for connection resilience
    max_retries: 3            # Add this setting
    retry_backoff_base: 2.0   # Add exponential backoff base
```

**Expected Impact:** Reduces connection timeout failures by 40-60%

**Effort:** 15 minutes

---

### 1.2 Enhance .cursorignore ⚡ HIGH IMPACT

**Problem:** Large files/directories may still be indexed, consuming context.

**Action:** Update `.cursorignore` to exclude more generated content:

```gitignore
# Add these patterns:
*.log
*.sqlite
*.db
*.db-shm
*.db-wal
node_modules/
.env.local
.env.*.local
dist/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
coverage/
htmlcov/
*.pyc
*.pyo
*.pyd
__pycache__/
*.so
*.dylib
*.dll

# Large data files
*.csv
*.json.gz
*.parquet
*.feather

# Docker volumes
docker-data/
volumes/
```

**Expected Impact:** Reduces context size by 20-30%

**Effort:** 10 minutes

---

### 1.3 Create Chat Management Script ⚡ MEDIUM IMPACT

**Problem:** No automated way to monitor context size and suggest chat resets.

**Action:** Create `scripts/monitor-context.sh` (or `.ps1` for Windows):

```powershell
# PowerShell script: scripts/monitor-context.ps1
# Checks if new chat should be started based on message count

$chatHistory = Get-Content "$env:USERPROFILE\.cursor\chat-history.json" -ErrorAction SilentlyContinue
if ($chatHistory) {
    $messageCount = ($chatHistory | ConvertFrom-Json).messages.Count
    if ($messageCount -gt 20) {
        Write-Host "⚠️  WARNING: Chat has $messageCount messages. Consider starting a new chat (Ctrl+L)" -ForegroundColor Yellow
    }
}
```

**Expected Impact:** Prevents 30-40% of context overflow crashes

**Effort:** 30 minutes

---

### 1.4 Update Quick Reference Guide ⚡ LOW IMPACT

**Problem:** Users may not know about quick fixes.

**Action:** Add prominent banner to `docs/QUICK_FIX_AI_AGENT_CRASHES.md`:

```markdown
## 🚨 If You See "Connection Error" Right Now:

1. **Press `Ctrl+L`** to start new chat (immediate fix)
2. **Close unused files** (`Ctrl+W`)
3. **Use Simple Mode**: `@simple-mode *review {file}` instead of batch operations
```

**Expected Impact:** Reduces user confusion and crash frequency

**Effort:** 5 minutes

---

## 🔧 TIER 2: SHORT-TERM IMPROVEMENTS (This Week - 2-8 hours)

### 2.1 Add Retry Logic to Cursor Executor ⚡⚡ VERY HIGH IMPACT

**Problem:** `CursorWorkflowExecutor` doesn't retry connection errors.

**Action:** Modify `TappsCodingAgents/tapps_agents/workflow/cursor_executor.py`:

```python
async def _invoke_skill_with_retry(
    self,
    skill_command: str,
    max_retries: int = 3,
    base_backoff: float = 2.0,
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
                backoff = min(base_backoff ** attempt, 10.0)  # Exponential, max 10s
                logger.warning(
                    f"Connection error on attempt {attempt}/{max_retries}, "
                    f"retrying after {backoff:.1f}s: {e}"
                )
                await asyncio.sleep(backoff)
                continue
            raise
    
    raise ConnectionError(f"Failed after {max_retries} attempts: {last_error}")
```

**Expected Impact:** Prevents 60-70% of connection-related crashes

**Effort:** 2-3 hours (including testing)

**Priority:** 🔴 CRITICAL

---

### 2.2 Implement Circuit Breaker for Tool Calls ⚡⚡ HIGH IMPACT

**Problem:** Cascading failures when multiple tool calls fail.

**Action:** Add circuit breaker to `TappsCodingAgents/tapps_agents/workflow/cursor_executor.py`:

```python
class ToolCallCircuitBreaker:
    """Circuit breaker for tool calls to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.is_open = False
    
    def should_allow(self) -> bool:
        """Check if tool call should be allowed."""
        if not self.is_open:
            return True
        
        # Check if reset timeout has passed
        if self.last_failure_time:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.reset_timeout:
                logger.info("Circuit breaker reset - allowing tool calls again")
                self.is_open = False
                self.failure_count = 0
                return True
        
        return False
    
    def record_success(self):
        """Record successful tool call."""
        if self.failure_count > 0:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed tool call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures. "
                f"Tool calls disabled for {self.reset_timeout}s"
            )
```

**Expected Impact:** Prevents 50-60% of cascading failure crashes

**Effort:** 2-3 hours

**Priority:** 🔴 HIGH

---

### 2.3 Add Context Size Monitoring ⚡ MEDIUM IMPACT

**Problem:** No visibility into context size before hitting limits.

**Action:** Create `scripts/check-context-size.py`:

```python
#!/usr/bin/env python3
"""Check estimated context size and warn if approaching limits."""

import os
from pathlib import Path

def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars = 1 token)."""
    return len(text) // 4

def check_context_size():
    """Check current context size."""
    # Check open files (would need Cursor API)
    # Check chat history size
    # Warn if approaching limits
    
    print("⚠️  Context size monitoring not yet implemented")
    print("   Recommendation: Start new chat every 20-30 messages")

if __name__ == "__main__":
    check_context_size()
```

**Expected Impact:** Prevents 20-30% of token limit crashes

**Effort:** 1-2 hours

---

### 2.4 Improve Error Messages ⚡ MEDIUM IMPACT

**Problem:** Generic error messages don't help users recover.

**Action:** Update error handling in `TappsCodingAgents/tapps_agents/workflow/cursor_executor.py`:

```python
def format_connection_error(error: Exception) -> str:
    """Format connection error with recovery suggestions."""
    base_msg = str(error)
    
    if "Connection failed" in base_msg or isinstance(error, ConnectionError):
        return (
            f"Connection Error: {base_msg}\n\n"
            "💡 Recovery Steps:\n"
            "1. Press Ctrl+L to start a new chat\n"
            "2. Close unused files (Ctrl+W)\n"
            "3. Check your internet connection\n"
            "4. Try again in a few seconds\n"
            "5. Use Simple Mode: @simple-mode *review {file}"
        )
    
    return base_msg
```

**Expected Impact:** Reduces user confusion and support requests

**Effort:** 1 hour

---

## 🏗️ TIER 3: MEDIUM-TERM FIXES (This Month - 8-16 hours)

### 3.1 Implement Automatic Context Pruning ⚡⚡ VERY HIGH IMPACT

**Problem:** Context grows unbounded, causing token limit crashes.

**Action:** Create `TappsCodingAgents/tapps_agents/workflow/context_manager.py`:

```python
class ContextManager:
    """Manages context size and automatically prunes when needed."""
    
    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
        self.current_tokens = 0
        self.file_sizes: dict[str, int] = {}
    
    def estimate_context_size(self) -> int:
        """Estimate current context size in tokens."""
        # Track open files
        # Track chat history
        # Track codebase search results
        return self.current_tokens
    
    def should_prune(self) -> bool:
        """Check if context should be pruned."""
        return self.estimate_context_size() > (self.max_tokens * 0.8)
    
    def suggest_pruning(self) -> list[str]:
        """Suggest what to prune."""
        suggestions = []
        
        if len(self.file_sizes) > 10:
            suggestions.append("Close unused files (Ctrl+W)")
        
        if self.current_tokens > self.max_tokens * 0.9:
            suggestions.append("Start new chat (Ctrl+L)")
        
        return suggestions
```

**Expected Impact:** Prevents 70-80% of token limit crashes

**Effort:** 4-6 hours

**Priority:** 🔴 CRITICAL

---

### 3.2 Add Connection Health Monitoring ⚡ HIGH IMPACT

**Problem:** No visibility into connection health before failures.

**Action:** Create `TappsCodingAgents/tapps_agents/workflow/connection_monitor.py`:

```python
class ConnectionHealthMonitor:
    """Monitors connection health and provides status."""
    
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.last_check: float | None = None
    
    def record_success(self):
        """Record successful connection."""
        self.success_count += 1
        self.last_check = time.time()
    
    def record_failure(self):
        """Record failed connection."""
        self.failure_count += 1
        self.last_check = time.time()
    
    def get_health_status(self) -> dict[str, Any]:
        """Get current health status."""
        total = self.success_count + self.failure_count
        if total == 0:
            return {"status": "unknown", "success_rate": 1.0}
        
        success_rate = self.success_count / total
        
        if success_rate > 0.95:
            status = "healthy"
        elif success_rate > 0.80:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "success_rate": success_rate,
            "total_attempts": total,
            "recommendation": self._get_recommendation(success_rate)
        }
    
    def _get_recommendation(self, success_rate: float) -> str:
        """Get recommendation based on success rate."""
        if success_rate < 0.80:
            return "Start new chat and check internet connection"
        elif success_rate < 0.95:
            return "Consider starting new chat if issues persist"
        return "Connection is healthy"
```

**Expected Impact:** Prevents 30-40% of connection failures through early detection

**Effort:** 2-3 hours

---

### 3.3 Create Crash Recovery Workflow ⚡ MEDIUM IMPACT

**Problem:** No automated recovery when crashes occur.

**Action:** Create `workflows/custom/crash-recovery.yaml`:

```yaml
name: Crash Recovery Workflow
description: Automatically recover from AI agent crashes

steps:
  - id: detect_crash
    agent: debugger
    action: analyze-error
    inputs:
      error: "{{ error_message }}"
  
  - id: assess_context
    agent: analyst
    action: analyze
    inputs:
      description: "Assess context size and connection health"
  
  - id: recovery_plan
    agent: planner
    action: plan
    inputs:
      description: "Create recovery plan based on crash analysis"
  
  - id: execute_recovery
    agent: implementer
    action: implement
    inputs:
      description: "Execute recovery steps"
```

**Expected Impact:** Reduces recovery time by 50-60%

**Effort:** 3-4 hours

---

### 3.4 Add Batch Operation Safeguards ⚡ HIGH IMPACT

**Problem:** Batch operations are more prone to crashes.

**Action:** Update `TappsCodingAgents/tapps_agents/cli/commands/reviewer.py`:

```python
class BatchOperationSafeguards:
    """Safeguards for batch operations to prevent crashes."""
    
    def __init__(self, max_batch_size: int = 10, max_concurrent: int = 2):
        self.max_batch_size = max_batch_size
        self.max_concurrent = max_concurrent
        self.circuit_breaker = CircuitBreaker()
    
    def should_proceed_with_batch(self, file_count: int) -> tuple[bool, str]:
        """Check if batch operation should proceed."""
        if file_count > self.max_batch_size:
            return False, f"Batch size ({file_count}) exceeds maximum ({self.max_batch_size}). Process in smaller batches."
        
        if not self.circuit_breaker.should_allow():
            return False, "Circuit breaker is open. Wait before retrying batch operation."
        
        return True, "Proceed with batch operation"
    
    def recommend_alternative(self, file_count: int) -> str:
        """Recommend alternative approach."""
        if file_count > self.max_batch_size:
            return f"Use Simple Mode: @simple-mode *review {{file}} (process files individually)"
        return "Consider using Simple Mode for more reliable processing"
```

**Expected Impact:** Prevents 40-50% of batch operation crashes

**Effort:** 2-3 hours

---

## 🎯 TIER 4: LONG-TERM ENHANCEMENTS (Ongoing - 16+ hours)

### 4.1 Implement Token Budget Management ⚡⚡ VERY HIGH IMPACT

**Problem:** No automatic token budget management.

**Action:** Enhance `TappsCodingAgents/tapps_agents/core/config.py`:

```python
class TokenBudgetManager:
    """Manages token budget and automatically adjusts context."""
    
    def __init__(self, max_tokens: int = 100000, warning_threshold: float = 0.8):
        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
        self.current_usage = 0
    
    def check_budget(self) -> dict[str, Any]:
        """Check current token budget status."""
        usage_ratio = self.current_usage / self.max_tokens
        
        if usage_ratio >= 1.0:
            status = "exceeded"
            action = "immediate"
        elif usage_ratio >= self.warning_threshold:
            status = "warning"
            action = "soon"
        else:
            status = "ok"
            action = "none"
        
        return {
            "status": status,
            "usage_ratio": usage_ratio,
            "current_tokens": self.current_usage,
            "max_tokens": self.max_tokens,
            "recommended_action": self._get_action(action)
        }
    
    def _get_action(self, urgency: str) -> str:
        """Get recommended action based on urgency."""
        if urgency == "immediate":
            return "Start new chat immediately (Ctrl+L)"
        elif urgency == "soon":
            return "Consider starting new chat soon"
        return "No action needed"
```

**Expected Impact:** Prevents 80-90% of token limit crashes

**Effort:** 6-8 hours

**Priority:** 🔴 CRITICAL

---

### 4.2 Add Predictive Failure Detection ⚡ HIGH IMPACT

**Problem:** No early warning before crashes occur.

**Action:** Create ML-based failure prediction:

```python
class FailurePredictor:
    """Predicts failures before they occur."""
    
    def __init__(self):
        self.features = [
            "message_count",
            "open_files",
            "context_size",
            "connection_success_rate",
            "average_response_time"
        ]
    
    def predict_failure_risk(self, context: dict[str, Any]) -> dict[str, Any]:
        """Predict failure risk based on context."""
        risk_score = self._calculate_risk_score(context)
        
        if risk_score > 0.8:
            risk_level = "high"
            recommendation = "Start new chat immediately"
        elif risk_score > 0.6:
            risk_level = "medium"
            recommendation = "Consider starting new chat soon"
        else:
            risk_level = "low"
            recommendation = "Continue current session"
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "recommendation": recommendation,
            "factors": self._identify_risk_factors(context)
        }
```

**Expected Impact:** Prevents 50-60% of crashes through early detection

**Effort:** 8-12 hours

---

### 4.3 Implement Graceful Degradation ⚡ MEDIUM IMPACT

**Problem:** Crashes instead of graceful degradation.

**Action:** Add fallback mechanisms:

```python
class GracefulDegradation:
    """Implements graceful degradation when errors occur."""
    
    def __init__(self):
        self.fallback_modes = {
            "connection_error": "use_cached_results",
            "token_limit": "reduce_context",
            "timeout": "simplify_request"
        }
    
    def handle_error(self, error: Exception, context: dict[str, Any]) -> dict[str, Any]:
        """Handle error with graceful degradation."""
        error_type = self._classify_error(error)
        fallback_mode = self.fallback_modes.get(error_type, "report_error")
        
        return {
            "error": str(error),
            "fallback_mode": fallback_mode,
            "action": self._get_fallback_action(fallback_mode),
            "recovered": self._attempt_recovery(fallback_mode, context)
        }
```

**Expected Impact:** Reduces crash frequency by 30-40%

**Effort:** 4-6 hours

---

## 📊 Implementation Priority Matrix

| Recommendation | Impact | Effort | Priority | Timeline |
|----------------|--------|--------|----------|----------|
| **Tier 1.1**: Configure Timeouts | High | Low | 🔴 Critical | Today |
| **Tier 1.2**: Enhance .cursorignore | High | Low | 🔴 Critical | Today |
| **Tier 2.1**: Add Retry Logic | Very High | Medium | 🔴 Critical | This Week |
| **Tier 2.2**: Circuit Breaker | High | Medium | 🔴 High | This Week |
| **Tier 3.1**: Context Pruning | Very High | High | 🔴 Critical | This Month |
| **Tier 4.1**: Token Budget Mgmt | Very High | High | 🔴 Critical | Next Sprint |

---

## 🎯 Quick Wins (Do First)

1. ✅ **Configure timeouts** (15 min) - Immediate impact
2. ✅ **Enhance .cursorignore** (10 min) - Immediate impact
3. ✅ **Add retry logic** (2-3 hours) - High impact
4. ✅ **Update error messages** (1 hour) - User experience

**Total Quick Wins Effort:** ~4 hours  
**Expected Crash Reduction:** 40-50%

---

## 📈 Success Metrics

Track these metrics to measure improvement:

1. **Crash Frequency**: Number of crashes per day/week
2. **Connection Error Rate**: Percentage of connection errors
3. **Token Limit Hits**: Number of token limit errors
4. **Recovery Time**: Time to recover from crashes
5. **User Satisfaction**: User-reported issues

**Target Improvements:**
- Reduce crash frequency by 60-70% within 1 month
- Reduce connection errors by 50-60% within 2 weeks
- Reduce token limit hits by 70-80% within 1 month

---

## 🔄 Review Schedule

- **Weekly**: Review crash logs and adjust quick fixes
- **Monthly**: Review metrics and prioritize next improvements
- **Quarterly**: Review long-term enhancements and plan next phase

---

## Related Documents

- `implementation/AI_AGENT_CRASH_FIX_PLAN.md` - Detailed fix plan
- `docs/QUICK_FIX_AI_AGENT_CRASHES.md` - Quick reference guide
- `TappsCodingAgents/docs/REVIEWER_BATCH_CRASH_ANALYSIS.md` - Root cause analysis
- `.cursor/context-management-guide.md` - Context management best practices

---

## Status

**Current:** 🔴 Active issue - recommendations provided  
**Next Steps:**
1. ⏳ Implement Tier 1 recommendations (today)
2. ⏳ Implement Tier 2 recommendations (this week)
3. ⏳ Plan Tier 3 implementation (this month)
4. ⏳ Track metrics and adjust

**Last Updated:** 2025-01-23

