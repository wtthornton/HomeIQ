# AI Agent Crash Prevention - Quick Start Guide

**TL;DR:** Follow these steps in order to prevent AI agent crashes.

## 🚀 5-Minute Quick Fixes

### Step 1: Update Timeout Configuration (2 minutes)

Edit `.tapps-agents/config.yaml` and add these settings:

```yaml
agents:
  reviewer:
    tool_timeout: 60.0        # Increase from 30.0
    max_retries: 3            # Add this
    retry_backoff_base: 2.0   # Add this
```

**Why:** Gives connections more time to recover from transient errors.

---

### Step 2: Enhance .cursorignore (1 minute)

Add these patterns to `.cursorignore`:

```gitignore
# Add to existing .cursorignore:
*.log
*.sqlite
*.db
*.db-shm
*.db-wal
node_modules/
.env.local
dist/
coverage/
htmlcov/
```

**Why:** Prevents large files from consuming context tokens.

---

### Step 3: Use Simple Mode (Always)

**Instead of:**
```bash
python -m tapps_agents.cli reviewer review services/**/*.py
```

**Use:**
```bash
@simple-mode *review services/websocket-ingestion/src/main.py
```

**Why:** Simple Mode has built-in retry logic and error handling.

---

## 🛡️ Daily Habits

### Before Starting Work

- [ ] Close unused files (`Ctrl+W`)
- [ ] Start new chat if previous was long (`Ctrl+L`)
- [ ] Check service health if doing API work

### During Work

- [ ] Keep only active files open
- [ ] Use Simple Mode for standard tasks
- [ ] Start new chat every 20-30 messages
- [ ] Watch for "Connection Error" warnings

### When You See Errors

1. **Connection Error**: Press `Ctrl+L` to start new chat
2. **Slow Responses**: Close unused files
3. **Token Limit**: Start new chat immediately

---

## 📋 Command Reference

### Safe Commands (Use These)

```bash
# Single file review
@simple-mode *review {file}

# Single file test
@simple-mode *test {file}

# Single file fix
@simple-mode *fix {file} "{description}"

# Quick quality check (no API calls)
python -m tapps_agents.cli reviewer score {file}
```

### Risky Commands (Use Carefully)

```bash
# Batch operations - can crash
python -m tapps_agents.cli reviewer review **/*.py

# Long-running workflows - can timeout
python -m tapps_agents.cli workflow full --auto

# Multiple parallel operations - can exhaust connections
```

---

## 🎯 Priority Actions

### This Week

1. ✅ Update timeout configuration (done in 2 min)
2. ✅ Enhance .cursorignore (done in 1 min)
3. ⏳ Add retry logic to Cursor executor (2-3 hours)
4. ⏳ Add circuit breaker (2-3 hours)

**Expected Result:** 40-50% reduction in crashes

### This Month

1. ⏳ Implement context pruning (4-6 hours)
2. ⏳ Add connection health monitoring (2-3 hours)
3. ⏳ Create crash recovery workflow (3-4 hours)

**Expected Result:** 70-80% reduction in crashes

---

## 📊 Monitoring

### Check Crash Frequency

```powershell
# Count crashes in logs (if logging enabled)
Get-Content .tapps-agents/logs/*.log | Select-String "Connection Error" | Measure-Object
```

### Check Service Health

```powershell
$services = @(
    @{Name="websocket-ingestion"; Port=8001},
    @{Name="data-api"; Port=8006}
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

---

## 🆘 Emergency Recovery

### If Agent Crashes Right Now

1. **Press `Ctrl+L`** - Start new chat
2. **Close all files** - `Ctrl+W` on each
3. **Check connection** - Verify internet/VPN
4. **Use Simple Mode** - `@simple-mode *review {file}`
5. **Report issue** - Include error message

---

## 📚 Full Documentation

- **Detailed Recommendations**: `implementation/AI_AGENT_CRASH_RECOMMENDATIONS.md`
- **Fix Plan**: `implementation/AI_AGENT_CRASH_FIX_PLAN.md`
- **Quick Reference**: `docs/QUICK_FIX_AI_AGENT_CRASHES.md`

---

**Last Updated:** 2025-01-23

