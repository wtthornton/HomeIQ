# Cursor Context Management Guide

**Purpose:** Optimize context window usage in Cursor.ai for better performance and token efficiency.

---

## Quick Reference

### Start New Chats Frequently
- **When:** After completing a task, switching epics, or when context feels "heavy"
- **How:** `Cmd/Ctrl + L` to start new chat panel
- **Benefit:** Fresh context = faster responses

### Use Focused Queries
- ❌ **Bad:** "Review the entire codebase and suggest improvements"
- ✅ **Good:** "Review `ask_ai_router.py` lines 3700-3817 for token optimization"

### Close Unnecessary Files
- **Tip:** Only keep files open that you're actively editing
- **Why:** Cursor includes all open files in context
- **Action:** Close files when done with them

### Leverage File References
- **Instead of:** Auto-adding entire directories
- **Use:** `@filename.py` to reference specific files when needed
- **Example:** `@docs/prd/epic-ai17-simulation-framework-core.md`

---

## Project-Specific Optimizations

### 1. `.cursorignore` Configuration

Already configured to exclude:
- ✅ Archive directories (`docs/archive/`, `implementation/archive/`)
- ✅ Simulation generated data (`simulation/data/`, `simulation/training_data/`)
- ✅ Build artifacts, logs, cache files
- ✅ Test coverage files

**Check:** `.cursorignore` in project root

### 2. Use Sharded Documentation

**Instead of:**
- Loading entire `docs/prd.md` (huge file)

**Use:**
- Reference specific shards: `docs/prd/epic-ai17-simulation-framework-core.md`
- Use cross-references for related sections
- Load only what you need

**Benefit:** 90% token savings (as per BMAD sharding)

### 3. Epic Isolation

**Strategy:** One chat per epic
- Chat 1: Epic AI-17 (Simulation Framework)
- Chat 2: Epic AI-18 (Data Generation)
- Chat 3: Bug fixes / Quick tasks

**Why:** Prevents context pollution between unrelated work

### 4. BMAD Agent Selection

**Use specific agents for specific tasks:**
- `@dev` for implementation
- `@qa` for testing
- `@architect` for design decisions

**Benefit:** Agent-specific context loading is optimized

---

## Context Optimization Checklist

Before starting a new task, check:

- [ ] Are archive directories in `.cursorignore`? ✅ (Already done)
- [ ] Are simulation data directories excluded? ✅ (Already done)
- [ ] Are you starting with a fresh chat for new epic/work?
- [ ] Have you closed files from previous work?
- [ ] Are you using specific file references (`@filename`) instead of broad queries?
- [ ] Are you using sharded docs instead of monolithic files?

---

## Manual Context Management

### Clear Context Completely

1. **Close Cursor completely** and reopen
2. **Start new chat** (`Cmd/Ctrl + L`)
3. **Close old chat panels** (click X on chat tab)

### Partial Context Reset

1. **Close all open files** (File → Close All)
2. **Start new chat** (`Cmd/Ctrl + L`)
3. **Reopen only files you need** for current task

---

## Context Size Indicators

**Watch for these signs that context is too large:**
- ⚠️ Responses slow down significantly
- ⚠️ AI seems "confused" or references wrong files
- ⚠️ Token usage warnings appear
- ⚠️ Cursor becomes unresponsive

**When you see these:** Time to start a new chat!

---

## Advanced Tips

### 1. Use BMAD Workflow-Init
```bash
@bmad-master *workflow-init
```
This loads only necessary context based on workflow type.

### 2. Leverage Context7 KB Integration
- Use `*context7-docs` commands for library documentation
- Reduces need to include large documentation files in context
- KB cache reduces repeated lookups

### 3. File-Based Context Switching
Create separate `.cursor/rules/` configurations for different work contexts:
- Development rules
- Testing rules
- Documentation rules

(Currently all rules are always loaded, but this could be optimized)

---

## Monitoring Context Usage

### Check What's in Context

Currently, Cursor doesn't provide a direct "context size" indicator, but you can:

1. **Check open files** - More open files = larger context
2. **Check chat history** - Longer conversations = larger context
3. **Check codebase search results** - More results included = larger context

### Estimate Context Size

**Rough estimates:**
- Small file (~100 lines): ~3-5k tokens
- Medium file (~500 lines): ~15-20k tokens
- Large file (~2000 lines): ~60-80k tokens
- Chat history (10 messages): ~5-10k tokens
- Documentation (sharded): ~5-10k tokens per shard

**Typical Cursor context window:** 128k-200k tokens (depending on plan)

**Rule of thumb:** If you have 10+ large files open + long chat history, you're likely near limits.

---

## Recommended Workflow

### Daily Workflow

1. **Morning:** Start fresh chat for the day
2. **Epic Work:** Start new chat per epic
3. **Quick Fixes:** Can use existing chat
4. **End of Day:** Close Cursor or clear chat

### Per-Task Workflow

1. **Before Task:**
   - Close unrelated files
   - Start new chat if switching major topics
   - Reference specific files (`@filename`)

2. **During Task:**
   - Keep only active files open
   - Use focused queries
   - Reference files as needed

3. **After Task:**
   - Close files used in task
   - Save important context in notes
   - Consider starting new chat for next task

---

## Troubleshooting

### Issue: Context Too Large

**Symptoms:**
- Slow responses
- Token limit errors
- Confused AI responses

**Solutions:**
1. Start new chat immediately
2. Close all open files
3. Use more specific file references
4. Check `.cursorignore` includes large directories

### Issue: Missing Context

**Symptoms:**
- AI doesn't know about relevant files
- References wrong code sections

**Solutions:**
1. Explicitly reference files with `@filename`
2. Open relevant files (but keep it minimal)
3. Use codebase search to find relevant code first
4. Check if files are in `.cursorignore` (shouldn't be)

---

## Project Status

✅ **Already Optimized:**
- `.cursorignore` configured for archives and simulation data
- BMAD sharding reduces doc token usage by 90%
- Context7 KB integration reduces repeated doc lookups

📋 **Recommended Practices:**
- Start new chats per epic
- Use focused queries
- Close files when done
- Use file references (`@filename`)

---

**Last Updated:** January 2025  
**Related:** `.cursorignore`, `implementation/CURSOR_OPTIMIZATION_COMPLETE.md`

