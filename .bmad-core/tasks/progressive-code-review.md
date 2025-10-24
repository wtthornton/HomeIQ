<!-- Powered by BMAD™ Core -->

# progressive-code-review

Perform incremental AI code review after each task completion during story development. Provides immediate feedback to prevent accumulation of issues.

## Purpose

Enable continuous quality assessment during development by reviewing code after each task rather than waiting for story completion. Catches issues early when fixes are cheapest.

## When to Use

**Auto-triggered during `*develop-story` command:**
- After completing each task in the story
- Before marking task checkbox as [x]
- Only if `progressive_review: true` in core-config.yaml

**Manual trigger:**
- `*review-task {task_number}` - Review specific completed task

## Prerequisites

- Task implementation complete (code written, tests added)
- Tests passing for the task
- Not yet marked complete in story file

## Review Scope

**Focus on:**
- Code quality for the specific task
- Security vulnerabilities introduced
- Performance anti-patterns (check CLAUDE.md)
- Test coverage for the task's acceptance criteria
- Adherence to coding standards

**Out of scope:**
- Overall story completeness (that's for full QA review)
- Architecture changes (handled in architect review)
- Requirements traceability (handled in final QA)

## Review Process

### 1. Identify Changed Files

```bash
# Get files changed since last task completion
git diff HEAD~1 --name-only
```

### 2. AI Review Analysis

Call LLM with focused prompt:

```yaml
review_context:
  scope: task_level
  task_id: "{task_number}"
  changed_files: [list of files]

review_criteria:
  - Security vulnerabilities (SQL injection, XSS, auth bypasses)
  - Performance issues (N+1 queries, blocking operations, memory leaks)
  - Code quality (complexity, duplication, naming)
  - Test coverage (missing edge cases, incomplete mocking)
  - Standards compliance (CLAUDE.md, coding-standards.md)

severity_threshold:
  block_task: high  # High severity blocks task completion
  warn_task: medium # Medium severity warns but allows completion
  log_only: low     # Low severity logged for final QA
```

### 3. Generate Review Output

**Format:**

```yaml
task_review:
  story_id: "1.3"
  task_number: 2
  reviewed_at: "2025-01-24T10:30:00Z"
  reviewer: "Claude Code Review"
  model: "claude-sonnet-4-5"

  findings:
    - id: "TASK-2-SEC-001"
      severity: high
      category: security
      file: "services/auth-api/src/login.py"
      line: 45
      finding: "No rate limiting on login endpoint"
      impact: "Brute force attacks possible"
      suggested_fix: "Add rate limiting middleware: @rate_limit(max_requests=5, window=60)"

    - id: "TASK-2-PERF-001"
      severity: medium
      category: performance
      file: "services/auth-api/src/login.py"
      line: 67
      finding: "Synchronous database query in async endpoint"
      impact: "Blocks event loop, reduces throughput"
      suggested_fix: "Use await session.execute() instead of session.query()"

  metrics:
    files_reviewed: 3
    lines_added: 156
    lines_deleted: 23
    test_files: 1
    test_coverage_delta: "+12%"

  decision: PASS|CONCERNS|BLOCK
  decision_reason: "1-2 sentence explanation"
```

### 4. Decision Logic

**BLOCK (prevents task completion):**
- Any high severity security issues
- Critical performance problems (blocking async, memory leaks)
- Missing tests for critical paths
- Violates mandatory architecture constraints

**CONCERNS (allows completion with warning):**
- Medium severity issues
- Non-critical performance improvements
- Test coverage gaps for edge cases
- Minor standards violations

**PASS:**
- No blocking issues
- All critical paths tested
- Follows coding standards

### 5. Update Story File

**Append to new section: `### Task Review Results`**

```markdown
### Task Review Results

#### Task 2: Implement JWT Authentication - Reviewed 2025-01-24

**Decision:** CONCERNS

**Issues Found:**
- [MEDIUM] TASK-2-PERF-001: Synchronous DB query blocks event loop (services/auth-api/src/login.py:67)
  - Fix: Use `await session.execute()`

**Metrics:**
- Files: 3 changed (+156/-23 lines)
- Tests: 1 file added (+12% coverage)

**Action:** Developer should address MEDIUM issues before moving to next task.

---
```

## Integration with Dev Workflow

**Modified `*develop-story` command:**

```yaml
for each task in story:
  1. Read task requirements
  2. Implement code
  3. Write tests
  4. Run tests
  5. >> NEW: Run progressive-code-review
  6. If BLOCK:
       - Show findings
       - HALT - require fixes before proceeding
  7. If CONCERNS:
       - Show findings
       - Ask: "Fix now or defer to final QA? (fix/defer)"
  8. If PASS or (CONCERNS + defer):
       - Mark task [x]
       - Continue to next task
```

## Configuration

**Add to `.bmad-core/core-config.yaml`:**

```yaml
qa:
  progressive_review:
    enabled: true
    review_location: docs/qa/progressive

    auto_trigger: true  # Auto-review after each task
    severity_blocks:    # What severities block task completion
      - high

    ai_config:
      model: "claude-sonnet-4-5"
      max_tokens: 4000
      temperature: 0.0

    review_focus:
      - security
      - performance  # Uses CLAUDE.md as reference
      - testing
      - standards

    skip_for_tasks:   # Task types that skip review
      - documentation
      - configuration
```

## Storage

**Progressive review files:**
- Location: `{qa.progressive_review.review_location}/{epic}.{story}-task-{n}.yml`
- Example: `docs/qa/progressive/1.3-task-2.yml`

**Benefits:**
- Incremental review history
- Can reference in final QA gate
- Tracks quality trend across tasks

## Rollup to Final QA

When QA runs `*review`, it should:

1. Read all progressive review files for the story
2. Check if CONCERNS were deferred
3. Include in final gate decision
4. Verify earlier issues were actually fixed

## Example Output

```yaml
# docs/qa/progressive/1.3-task-2.yml
schema: 1
story: "1.3"
task: 2
task_title: "Implement JWT Authentication"
reviewed_at: "2025-01-24T10:30:00Z"
reviewer: "Claude Code Review (progressive)"
model: "claude-sonnet-4-5"

decision: CONCERNS
decision_reason: "Performance issue with blocking DB call should be fixed"

findings:
  - id: "TASK-2-PERF-001"
    severity: medium
    category: performance
    file: "services/auth-api/src/login.py"
    line: 67
    finding: "Synchronous database query in async endpoint"
    impact: "Blocks event loop, reduces throughput"
    suggested_fix: "Use await session.execute() instead of session.query()"
    references:
      - "CLAUDE.md#api-performance (Async Everything principle)"
      - "docs/architecture/coding-standards.md#async-patterns"

metrics:
  files_reviewed: 3
  lines_changed: 179
  test_coverage_delta: "+12%"

developer_action: "deferred"  # or "fixed"
deferred_reason: "Will address during final QA review cycle"
```

## Key Principles

- **Fast feedback loop** - Issues found when context fresh
- **Lower fix cost** - Catching issues early cheaper than later
- **Maintains momentum** - CONCERNS don't block, only BLOCK does
- **Accumulates evidence** - Progressive reviews feed final gate
- **Performance-aware** - Uses CLAUDE.md as performance reference
- **Pragmatic** - Balance between quality and velocity

## AI Review Prompt Template

```
You are reviewing Task {task_number} of Story {story_id}.

TASK DESCRIPTION:
{task_description}

FILES CHANGED:
{git_diff_summary}

REVIEW CRITERIA:
1. Security vulnerabilities (auth, injection, XSS, data exposure)
2. Performance anti-patterns (check CLAUDE.md for HomeIQ performance requirements)
3. Code quality (complexity, duplication, naming, error handling)
4. Test coverage (edge cases, error scenarios, mocking appropriateness)
5. Standards compliance (coding-standards.md, architecture constraints)

CONTEXT:
- Project: HomeIQ - Home automation data ingestion platform
- Performance targets: See CLAUDE.md (async-first, <100ms responses, batch operations)
- Stack: Python 3.11 FastAPI, SQLAlchemy 2.0 async, InfluxDB, SQLite

OUTPUT FORMAT: YAML with findings array, metrics, and decision (PASS/CONCERNS/BLOCK)

Focus on issues that:
- Create security vulnerabilities
- Violate performance requirements in CLAUDE.md
- Missing critical test coverage
- Block future development

Be pragmatic - not every minor issue needs flagging.
```

## Future Enhancements

1. **AI learning** - Track which issues get fixed vs waived to tune thresholds
2. **Performance regression detection** - Benchmark before/after each task
3. **Auto-fix suggestions** - Generate code diffs for simple fixes
4. **Trend analysis** - Quality score trend across tasks in a story
