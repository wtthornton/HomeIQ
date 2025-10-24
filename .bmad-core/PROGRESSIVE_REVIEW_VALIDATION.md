# Progressive Review Integration - Validation Guide

## What Was Implemented

✅ **Configuration Added** to `core-config.yaml`:
- Progressive review settings (enabled by default)
- Background review settings (disabled by default)
- Performance check patterns (HomeIQ-specific)
- CLAUDE.md loaded for dev and qa agents

✅ **QA Agent Updated** (`agents/qa.md`):
- New command: `*review-task {story} {task_number}`
- Added `progressive-code-review.md` to dependencies
- Can now perform task-level reviews during development

✅ **Dev Agent Updated** (`agents/dev.md`):
- Modified `*develop-story` workflow to include progressive reviews
- New command: `*review-task {task_number}` for manual reviews
- Added `progressive-code-review.md` to dependencies

✅ **Directory Structure Created**:
- `docs/qa/progressive/` - Progressive review results
- `docs/qa/background/` - Background review results (when enabled)
- README files in both directories

✅ **Task Definitions Created**:
- `tasks/progressive-code-review.md` - Task-level review implementation
- `tasks/background-code-review.md` - Continuous background review (optional)

✅ **Documentation Created**:
- `CODE_REVIEW_INTEGRATION_SUMMARY.md` - Quick start guide
- `data/code-review-integration-guide.md` - Comprehensive guide
- `data/code-review-quick-reference.md` - One-page reference
- `data/code-review-config-template.yaml` - Configuration examples
- `utils/progressive-review-implementation-example.md` - Technical details

## Quick Validation Test

### Test 1: Configuration Loads Correctly

```bash
# Verify configuration is valid YAML
python3 -c "import yaml; yaml.safe_load(open('.bmad-core/core-config.yaml'))"
```

Expected: No errors

### Test 2: Directory Structure Exists

```bash
ls -la docs/qa/progressive/
ls -la docs/qa/background/
```

Expected: Both directories exist with README.md files

### Test 3: Agent Files are Valid

```bash
# Check QA agent has progressive-code-review command
grep -A 3 "review-task" .bmad-core/agents/qa.md

# Check Dev agent has progressive review in workflow
grep "progressive_review" .bmad-core/agents/dev.md
```

Expected: Both commands found

### Test 4: Task Files Exist

```bash
ls -la .bmad-core/tasks/progressive-code-review.md
ls -la .bmad-core/tasks/background-code-review.md
```

Expected: Both files exist

## How to Use (First Time)

### Option A: Manual Progressive Review

1. Start a story with the dev agent
2. Complete a task (implement + test)
3. Before marking task complete, run:
   ```
   Review this task using progressive-code-review
   ```
4. See findings (PASS/CONCERNS/BLOCK)
5. Fix HIGH severity issues if BLOCK
6. Choose to fix or defer CONCERNS
7. Mark task complete

### Option B: Integrated Workflow (Automatic)

The dev agent's `*develop-story` command now includes progressive review:

1. Read task
2. Implement code
3. Write tests
4. Run validations
5. **→ Progressive review runs automatically** ←
6. If BLOCK: Must fix to continue
7. If CONCERNS: Choose fix/defer
8. If PASS: Mark complete

### Option C: QA Agent Direct Call

From QA agent:
```
*review-task 1.3 2
```

Reviews Story 1.3, Task 2 specifically.

## Expected Behavior

### When Progressive Review is Enabled (Default)

**After completing a task:**

```
✓ Code written
✓ Tests passing

⏳ Running progressive review...

Decision: PASS / CONCERNS / BLOCK

[If BLOCK]
⚠️  HIGH severity issues found:
1. [HIGH] Blocking async operation in src/middleware.py:23
   Fix: Use asyncio.to_thread() or async JWT library
   Reference: CLAUDE.md#api-performance

Action: Fix HIGH issues to continue

[If CONCERNS]
⚠️  Issues found (can defer):
1. [MEDIUM] Missing cache on expensive query
   Fix: Add cache with 60s TTL
   Reference: CLAUDE.md#caching-strategies

Options:
1. Fix now (recommended, 5 min)
2. Defer to final QA
3. Skip (not recommended)

[If PASS]
✓ No issues found
✓ Task complete
```

### What Gets Checked

**Security (CRITICAL):**
- Auth bypasses
- SQL injection
- XSS vulnerabilities
- Exposed secrets

**Performance (HIGH - HomeIQ Specific):**
- Blocking async operations → CLAUDE.md#api-performance
- N+1 database queries → CLAUDE.md#database-performance
- Unbatched writes → CLAUDE.md#event-processing
- Missing caching → CLAUDE.md#caching-strategies
- Unbounded queries → CLAUDE.md#database-performance
- Sync HTTP in async code → CLAUDE.md#api-performance

**Testing (MEDIUM):**
- Missing critical path tests
- Poor edge case coverage
- Weak error scenario tests

**Code Quality (LOW):**
- High complexity
- Code duplication
- Poor naming

## Configuration Options

### Current Configuration (core-config.yaml)

```yaml
qa:
  progressive_review:
    enabled: true              # ✓ Active
    severity_blocks: [high]    # Only HIGH blocks
    review_focus:
      - security
      - performance            # Uses CLAUDE.md
      - testing
      - standards

  background_review:
    enabled: false             # ✗ Disabled (optional)
```

### To Adjust Strictness

**More Strict (Block on MEDIUM too):**
```yaml
severity_blocks: [high, medium]
```

**Less Strict (Only block on security):**
```yaml
review_focus:
  - security
```

**Disable for Prototypes:**
```yaml
progressive_review:
  enabled: false
```

## Success Metrics to Track

After using on 3-5 stories, measure:

1. **Issue Detection Rate**
   - Goal: 70-90% of issues caught before final QA
   - Track: Issues found in progressive vs final QA

2. **Fix Time Reduction**
   - Goal: 5 min per issue (vs 30 min in final QA)
   - Track: Time to fix issues found progressively

3. **False Positive Rate**
   - Goal: <20%
   - Track: How many BLOCK/CONCERNS were incorrect

4. **Developer Satisfaction**
   - Survey after 5 stories
   - Is feedback helpful?
   - Does it slow development?

## Troubleshooting

### Problem: Too many false positives

**Solution:**
```yaml
severity_blocks: [high]  # Only block on HIGH
```

### Problem: Missing critical issues

**Solution:** Enhance review prompts in `progressive-code-review.md` task

### Problem: Reviews too slow

**Solution:**
```yaml
ai_config:
  max_tokens: 2000  # Reduce from 4000
```

### Problem: Too expensive

**Solution:** Disable for simple tasks:
```yaml
skip_for_tasks:
  - documentation
  - configuration
  - minor-refactoring
```

## Next Steps

1. **Read** `CODE_REVIEW_INTEGRATION_SUMMARY.md` for full context
2. **Test** on one task manually
3. **Measure** results on first story
4. **Iterate** based on findings
5. **Consider** background reviews if stories >8 hours

## ROI Expectations

**Typical Story (5-7 tasks):**
- API Cost: $0.30-0.45
- Issues caught: 2-4
- Time saved: 1-2 hours
- **ROI: 20-40x**

**Long Story (10+ tasks):**
- API Cost: $0.45-0.60
- Issues caught: 4-8
- Time saved: 2-4 hours
- **ROI: 40-80x**

## Files Modified

```
.bmad-core/
├── core-config.yaml                    [MODIFIED] Added progressive review config
├── agents/
│   ├── qa.md                          [MODIFIED] Added *review-task command
│   └── dev.md                         [MODIFIED] Integrated into *develop-story
├── tasks/
│   ├── progressive-code-review.md     [NEW] Task definition
│   └── background-code-review.md      [NEW] Optional background reviewer
├── data/
│   ├── code-review-integration-guide.md        [NEW]
│   ├── code-review-quick-reference.md          [NEW]
│   └── code-review-config-template.yaml        [NEW]
└── utils/
    └── progressive-review-implementation-example.md [NEW]

docs/qa/
├── progressive/
│   └── README.md                      [NEW] Directory documentation
└── background/
    └── README.md                      [NEW] Directory documentation
```

## Status: READY TO USE ✅

The progressive code review integration is fully implemented and ready for testing.

Start with one task on your next story and measure the results!
