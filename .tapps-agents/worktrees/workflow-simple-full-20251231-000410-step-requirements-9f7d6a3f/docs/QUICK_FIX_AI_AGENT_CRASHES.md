# Quick Fix: AI Agent Crashes

**TL;DR:** Connection errors crash the AI agent. Use these quick fixes.

## 🚨 Immediate Fixes

### 1. Start New Chat
**When:** You see "Connection Error" or responses are slow

**How:** Press `Cmd/Ctrl + L` to start new chat

**Why:** Reduces context size and token usage

### 2. Close Unused Files
**When:** Many files are open

**How:** Press `Cmd/Ctrl + W` to close files

**Why:** Reduces context window size

### 3. Use Simple Mode
**When:** Doing standard tasks (build, review, test, fix)

**How:** Use `@simple-mode` commands instead of direct agent calls

**Example:**
```bash
# ✅ GOOD: Simple Mode (has retry logic)
@simple-mode *review services/websocket-ingestion/src/main.py

# ❌ BAD: Direct batch operation (can crash)
python -m tapps_agents.cli reviewer review services/**/*.py
```

## 🛡️ Prevention

### Before Starting Tasks
- [ ] Close unused files
- [ ] Start new chat if previous was long (>20 messages)
- [ ] Use Simple Mode for standard tasks
- [ ] Break large tasks into smaller chunks

### Safe Commands
- `@simple-mode *review {file}` ✅
- `@simple-mode *test {file}` ✅
- `@simple-mode *fix {file} "{desc}"` ✅
- `python -m tapps_agents.cli reviewer score {file}` ✅

### Risky Commands
- Batch operations ❌
- Long-running workflows ❌
- Multiple parallel tool calls ❌

## 📋 Full Guide

See `implementation/AI_AGENT_CRASH_FIX_PLAN.md` for complete details.

