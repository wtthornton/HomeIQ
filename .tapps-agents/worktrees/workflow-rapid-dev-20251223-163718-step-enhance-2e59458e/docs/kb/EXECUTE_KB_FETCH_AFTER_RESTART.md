# Execute KB Fetch After Cursor Restart

**Purpose:** Batch commands to fetch all Epic AI-17 & AI-18 documentation  
**Prerequisites:** Cursor restarted, MCP connection verified  
**Execution:** Run these commands in sequence after `*context7-kb-test` succeeds

---

## Pre-Flight Check

Before executing, verify MCP is working:

```bash
@bmad-master
*context7-kb-test
```

**Expected:** Connection successful, KB cache accessible

---

## Phase 1: Critical Dependencies (Epic AI-17 Foundation)

**Priority:** 🔴 CRITICAL - Required for Story AI17.1, AI17.2, AI17.3

```bash
@bmad-master

# FastAPI - Dependency Injection & Async Patterns
*context7-docs fastapi dependency-injection
*context7-docs fastapi async-routes
*context7-docs fastapi testing-patterns
*context7-docs fastapi middleware-patterns

# pytest-asyncio - Async Testing
*context7-docs pytest-asyncio async-fixtures
*context7-docs pytest-asyncio async-tests
*context7-docs pytest-asyncio async-context-managers
*context7-docs pytest-asyncio mocking-async

# Pydantic 2.x - Validation & Settings
*context7-docs pydantic validation-patterns
*context7-docs pydantic settings-management
*context7-docs pydantic basemodel-patterns
*context7-docs pydantic data-serialization
*context7-docs pydantic async-validation

# Python 3.12+ - Async Patterns
*context7-docs python asyncio-patterns
*context7-docs python async-generators
*context7-docs python async-context-managers
*context7-docs python concurrent-execution

# structlog - Structured Logging
*context7-docs structlog structured-logging
*context7-docs structlog async-logging
*context7-docs structlog context-variables
```

**Estimated Time:** 5-10 minutes  
**Topics:** 20

---

## Phase 2: Mock Services (Epic AI-17.2)

**Priority:** 🟡 HIGH - Required for Story AI17.2

```bash
@bmad-master

# pytest-mock - Mocking Patterns
*context7-docs pytest-mock mocking-patterns
*context7-docs pytest-mock async-mocking
*context7-docs unittest.mock interface-matching
```

**Estimated Time:** 2-3 minutes  
**Topics:** 3

---

## Phase 3: Data & Training (Epic AI-18)

**Priority:** 🟡 HIGH - Required for Epic AI-18

```bash
@bmad-master

# pandas - Data Manipulation
*context7-docs pandas data-manipulation
*context7-docs pandas parquet-io
*context7-docs pandas async-pandas
*context7-docs pandas data-validation

# SQLite/aiosqlite - Async Database
*context7-docs aiosqlite async-patterns
*context7-docs sqlite data-lineage

# PyTorch - Model Loading
*context7-docs pytorch model-loading
*context7-docs pytorch model-evaluation
*context7-docs pytorch cpu-optimization
*context7-docs pytorch inference-patterns

# scikit-learn - Model Evaluation
*context7-docs scikit-learn model-evaluation
*context7-docs scikit-learn cross-validation
*context7-docs scikit-learn model-comparison
```

**Estimated Time:** 5-8 minutes  
**Topics:** 12

---

## Phase 4: Validation & Optimization (Epic AI-17.9, AI-17.10)

**Priority:** 🟢 MEDIUM - Required for Story AI17.9, AI17.10

```bash
@bmad-master

# PyYAML - YAML Validation
*context7-docs pyyaml yaml-parsing
*context7-docs pyyaml yaml-validation
*context7-docs pyyaml yaml-serialization
```

**Estimated Time:** 2-3 minutes  
**Topics:** 3

---

## Verification

After all phases complete, verify KB cache:

```bash
@bmad-master
*context7-kb-status
```

**Expected Results:**
- ✅ 35+ topics cached
- ✅ Hit rate >70%
- ✅ All libraries have meta.yaml files
- ✅ Cross-references updated

---

## Quick Status Check

Check progress at any time:

```bash
*context7-kb-status
```

Or search for specific documentation:

```bash
*context7-kb-search fastapi dependency injection
*context7-kb-search pytest-asyncio async fixtures
*context7-kb-search pydantic validation
```

---

## Troubleshooting

### If a command fails:

1. **Check MCP connection:** `*context7-kb-test`
2. **Verify API key:** Check `.cursor/mcp.json` (if accessible)
3. **Retry command:** Some libraries may need multiple attempts
4. **Check KB cache:** `*context7-kb-status` to see what's cached

### If authentication fails:

1. **Restart Cursor:** MCP server needs restart after config changes
2. **Verify file:** Ensure `.cursor/mcp.json` exists and has correct key
3. **Check logs:** Look for MCP connection errors in Cursor

---

## Total Execution Time

**Estimated Total:** 15-25 minutes for all 35 topics

**Breakdown:**
- Phase 1: 5-10 min (20 topics)
- Phase 2: 2-3 min (3 topics)
- Phase 3: 5-8 min (12 topics)
- Phase 4: 2-3 min (3 topics)

---

## Success Criteria

✅ **KB Ready for Epic AI-17 & AI-18 when:**
- All 35 topics cached
- `*context7-kb-status` shows >70% hit rate
- All libraries have meta.yaml files
- Can search and find documentation via `*context7-kb-search`

---

**Last Updated:** January 2025  
**Status:** Ready to execute after Cursor restart

