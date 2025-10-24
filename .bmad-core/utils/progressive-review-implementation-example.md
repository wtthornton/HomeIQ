<!-- Powered by BMAD™ Core -->

# Progressive Review Implementation Example

Concrete example showing how progressive code review integrates with BMAD dev workflow.

## Current Dev Workflow (Before)

```
Story 1.3: Implement JWT Authentication
├─ Task 1: Set up JWT library
├─ Task 2: Create auth middleware
├─ Task 3: Implement login endpoint
├─ Task 4: Implement token refresh
├─ Task 5: Add rate limiting
└─ Task 6: Write integration tests

Dev Agent:
  1. Read story
  2. Implement all 6 tasks sequentially
  3. Mark all tasks [x]
  4. Set status: "Ready for Review"

QA Agent (hours/days later):
  1. Review entire implementation
  2. Find issues:
     - Task 2: Middleware blocks event loop (HIGH)
     - Task 3: No rate limiting (HIGH)
     - Task 4: Missing token expiry check (MEDIUM)
     - Task 5: Tests don't cover edge cases (MEDIUM)
  3. Create gate: FAIL
  4. Dev has to context switch back, remember decisions, fix issues

Problem: Feedback loop is 4-24 hours, context lost, high fix cost
```

## New Dev Workflow (With Progressive Review)

```
Story 1.3: Implement JWT Authentication

Task 1: Set up JWT library
  → Dev implements
  → Dev writes tests
  → Tests pass
  → PROGRESSIVE REVIEW RUNS (automatic)
     ├─ Review: Added pyjwt dependency, basic setup
     ├─ Findings: None
     ├─ Decision: PASS
     └─ Mark task [x]

Task 2: Create auth middleware
  → Dev implements
  → Dev writes tests
  → Tests pass
  → PROGRESSIVE REVIEW RUNS (automatic)
     ├─ Review: Middleware implementation
     ├─ Findings:
     │  └─ HIGH: Blocking JWT decode in async function
     │     File: services/auth-api/src/middleware.py:23
     │     Issue: jwt.decode() is synchronous, blocks event loop
     │     Fix: Use async JWT library or run in executor
     │     Reference: CLAUDE.md#api-performance (Async Everything)
     ├─ Decision: BLOCK (HIGH severity)
     └─ Dev must fix before continuing

  → Dev fixes immediately (context still fresh)
     ├─ Changes to async JWT decode
     ├─ Tests still pass

  → PROGRESSIVE REVIEW RE-RUNS
     ├─ Review: Fixed middleware
     ├─ Findings: None
     ├─ Decision: PASS
     └─ Mark task [x]

Task 3: Implement login endpoint
  → Dev implements
  → Dev writes tests
  → Tests pass
  → PROGRESSIVE REVIEW RUNS
     ├─ Review: Login endpoint
     ├─ Findings:
     │  ├─ HIGH: No rate limiting on login endpoint
     │  │  File: services/auth-api/src/routes.py:45
     │  │  Issue: Brute force attacks possible
     │  │  Fix: Add @rate_limit decorator
     │  │  Reference: Security best practices
     │  └─ MEDIUM: Missing error logging
     │     File: services/auth-api/src/routes.py:52
     │     Issue: Failed login attempts not logged
     │     Fix: Add logger.warning() for failed attempts
     ├─ Decision: BLOCK (HIGH severity present)

  → Dev chooses action:
     Option 1: Fix HIGH now (recommended)
     Option 2: Acknowledge will fix in Task 5 (rate limiting task exists)

  → Dev chooses Option 2 (rate limiting is next task anyway)
     └─ Reviewer accepts, logs as "deferred to Task 5"
     └─ Mark task [x] with note

Task 4: Implement token refresh
  → Dev implements
  → Dev writes tests
  → Tests pass
  → PROGRESSIVE REVIEW RUNS
     ├─ Review: Token refresh logic
     ├─ Findings:
     │  └─ MEDIUM: Token expiry not validated
     │     File: services/auth-api/src/refresh.py:34
     │     Issue: Doesn't check if refresh token expired
     │     Fix: Add expiry check before refresh
     ├─ Decision: CONCERNS (no HIGH severity)

  → Dev chooses action:
     Option 1: Fix now (5 min)
     Option 2: Defer to final QA

  → Dev fixes immediately (easy fix, context fresh)
     └─ Mark task [x]

Task 5: Add rate limiting
  → Dev implements (also fixes deferred issue from Task 3)
  → Dev writes tests
  → Tests pass
  → PROGRESSIVE REVIEW RUNS
     ├─ Review: Rate limiting + deferred fix
     ├─ Findings: None
     ├─ Notes: Task 3 HIGH severity issue now resolved
     ├─ Decision: PASS
     └─ Mark task [x]

Task 6: Write integration tests
  → Dev implements
  → Tests pass
  → PROGRESSIVE REVIEW RUNS
     ├─ Review: Integration tests
     ├─ Findings:
     │  └─ LOW: Missing test for concurrent requests
     │     File: tests/integration/test_auth.py
     │     Issue: Rate limiting with concurrent requests not tested
     │     Fix: Add test with asyncio.gather()
     ├─ Decision: CONCERNS (no HIGH)

  → Dev defers to QA (acceptable for integration tests)
     └─ Mark task [x]

All Tasks Complete
  → Dev sets status: "Ready for Review"
  → Progressive review summary generated:
     ├─ Tasks reviewed: 6
     ├─ Issues found: 6 total (2 high, 3 medium, 1 low)
     ├─ Issues fixed immediately: 5
     ├─ Issues deferred to QA: 1 (LOW severity)
     └─ Time saved: ~60 min (vs finding in final QA)

QA Agent (Final Review):
  1. Review implementation
  2. Check progressive review history
  3. Find issues:
     - LOW: Missing concurrent request test (already identified)
     - (Everything else already caught and fixed)
  4. Create gate: PASS (with note about missing test)
  5. Total review time: 15 min (vs 45 min without progressive)

Result:
  - 5/6 issues caught early (fix time: 5 min each = 25 min)
  - 1/6 issue found in QA (fix time: 10 min)
  - Total fix time: 35 min
  - vs Without progressive: 6 issues in QA (fix time: 30 min each = 180 min)
  - Time saved: 145 minutes (2.4 hours)
```

## Technical Implementation

### 1. Modified Dev Agent Workflow

**File: `.bmad-core/agents/dev.md`**

Add to `develop-story` command:

```yaml
commands:
  - develop-story:
      order-of-execution: |
        For each task:
          1. Read task requirements
          2. Implement code
          3. Write tests
          4. Run tests → Must pass

          5. >> NEW: Progressive Review (if enabled)
             a. Check core-config.yaml → qa.progressive_review.enabled
             b. If true:
                - Run progressive-code-review task
                - Get decision: PASS|CONCERNS|BLOCK

                If BLOCK:
                  - Show findings
                  - HALT - require immediate fix
                  - Re-run review after fix

                If CONCERNS:
                  - Show findings
                  - Ask: "Fix now or defer to final QA? (fix/defer/skip)"
                  - If fix: Fix → Re-run review
                  - If defer: Log as deferred, continue
                  - If skip: Continue (not recommended)

                If PASS:
                  - Log review passed
                  - Continue

          6. Mark task [x] in story file
          7. Update File List
          8. Continue to next task
```

### 2. Progressive Review Task Execution

**File: `.bmad-core/tasks/progressive-code-review.md`** (already created)

**Execution flow:**

```python
async def progressive_review(task_number: int, story_id: str):
    # 1. Load configuration
    config = load_core_config()
    if not config['qa']['progressive_review']['enabled']:
        return {"decision": "SKIP", "reason": "Progressive review disabled"}

    # 2. Get changed files for this task
    changed_files = get_task_changes(task_number)

    # 3. Load review context
    context = {
        "story_id": story_id,
        "task_number": task_number,
        "claude_md": load_file("CLAUDE.md"),
        "coding_standards": load_file("docs/architecture/coding-standards.md"),
        "changed_files": changed_files
    }

    # 4. Build review prompt
    prompt = build_review_prompt(context)

    # 5. Call Claude API
    response = await call_claude_api(
        model=config['qa']['progressive_review']['ai_config']['model'],
        prompt=prompt,
        max_tokens=config['qa']['progressive_review']['ai_config']['max_tokens']
    )

    # 6. Parse findings
    findings = parse_review_response(response)

    # 7. Determine decision
    decision = determine_decision(
        findings=findings,
        block_severities=config['qa']['progressive_review']['severity_blocks']
    )

    # 8. Save results
    save_progressive_review(
        story_id=story_id,
        task_number=task_number,
        findings=findings,
        decision=decision
    )

    # 9. Update story file
    update_story_task_review_section(story_id, task_number, findings, decision)

    return {
        "decision": decision,  # PASS|CONCERNS|BLOCK
        "findings": findings,
        "metrics": {
            "files_reviewed": len(changed_files),
            "issues_found": len(findings)
        }
    }
```

### 3. Review Prompt Template

```python
def build_review_prompt(context):
    return f"""
You are reviewing Task {context['task_number']} of Story {context['story_id']} for the HomeIQ project.

PROJECT CONTEXT:
HomeIQ is a home automation data ingestion platform handling 1000+ events/sec with strict performance requirements.

TASK CHANGES:
{format_file_changes(context['changed_files'])}

REVIEW CRITERIA:

1. SECURITY (Priority: CRITICAL)
   - Authentication/authorization bypasses
   - SQL injection, XSS vulnerabilities
   - Exposed secrets or credentials
   - Insecure cryptography

2. PERFORMANCE (Priority: HIGH)
   Reference: See CLAUDE.md performance requirements

   Critical issues (CLAUDE.md violations):
   - Blocking operations in async functions (CLAUDE.md#api-performance)
   - N+1 database queries (CLAUDE.md#database-performance)
   - Unbatched writes (<100 points) (CLAUDE.md#event-processing)
   - Missing caching for expensive operations (CLAUDE.md#caching-strategies)
   - Synchronous HTTP in async code (requests instead of aiohttp)
   - Unbounded database queries (no LIMIT clause)

   Performance targets:
   - API response: <100ms
   - Device queries: <10ms (SQLite)
   - Event processing: 1000+ events/sec
   - Memory: <512MB per service

3. CODE QUALITY (Priority: MEDIUM)
   - Complexity (cyclomatic >10)
   - Code duplication (DRY violations)
   - Poor naming, magic numbers
   - Missing error handling
   - Improper exception handling

4. TESTING (Priority: MEDIUM)
   - Missing tests for critical paths
   - Inadequate edge case coverage
   - Missing error scenario tests
   - Test quality (brittle, unclear)

5. STANDARDS (Priority: LOW)
   Reference: docs/architecture/coding-standards.md
   - Type hints missing (Python)
   - Linting violations
   - Import organization

CODING STANDARDS:
{context['coding_standards']}

PERFORMANCE REQUIREMENTS (CRITICAL):
{extract_relevant_claude_md_sections(context['claude_md'], context['changed_files'])}

OUTPUT FORMAT (JSON):
{{
  "findings": [
    {{
      "id": "TASK-{context['task_number']}-CAT-NNN",
      "severity": "high|medium|low",
      "category": "security|performance|quality|testing|standards",
      "file": "path/to/file.py",
      "line": 123,
      "finding": "Clear description of issue",
      "impact": "Why this matters",
      "suggested_fix": "Specific code or approach to fix",
      "references": ["CLAUDE.md#section", "coding-standards.md#rule"]
    }}
  ],
  "metrics": {{
    "files_reviewed": 3,
    "lines_changed": 156,
    "complexity_score": 7.5
  }}
}}

IMPORTANT:
- Be strict on security and performance (HomeIQ processes sensitive data at scale)
- Reference CLAUDE.md sections for performance issues
- Provide actionable fixes with code examples
- Don't flag minor style issues unless severe
- HIGH severity should be rare (only critical issues)
"""

def extract_relevant_claude_md_sections(claude_md: str, changed_files: list) -> str:
    """
    Extract relevant CLAUDE.md sections based on changed files

    Example:
    - If services/data-api/src/*.py changed → Include "API Performance" section
    - If services/websocket-ingestion/*.py changed → Include "Event Processing" section
    - If *.db or database.py changed → Include "Database Performance" section
    """
    relevant_sections = []

    for file in changed_files:
        if 'api' in file or 'routes.py' in file:
            relevant_sections.append(extract_section(claude_md, "API Performance"))

        if 'database.py' in file or 'models.py' in file:
            relevant_sections.append(extract_section(claude_md, "Database Performance"))

        if 'websocket' in file or 'batch' in file:
            relevant_sections.append(extract_section(claude_md, "Event Processing Performance"))

        if 'cache' in file:
            relevant_sections.append(extract_section(claude_md, "Caching Strategies"))

    return "\n\n".join(relevant_sections)
```

### 4. Developer Experience

**What dev sees during task completion:**

```
Task 2: Create auth middleware

✓ Code implemented (src/middleware.py)
✓ Tests written (tests/test_middleware.py)
✓ Tests passing (3/3)

⏳ Running progressive code review...

⚠️  REVIEW RESULT: BLOCK

Issues found:
  1. [HIGH] Blocking JWT decode in async function
     File: src/middleware.py:23
     Issue: jwt.decode() is synchronous, blocks event loop
     Impact: Under load (1000 req/s), will cause request queuing and timeouts
     Fix: Use python-jose library with async support:
           from jose import jwt
           # or run in executor:
           await asyncio.to_thread(jwt.decode, token, key)
     Reference: CLAUDE.md#api-performance (Async Everything principle)

Action required: Fix HIGH severity issues before continuing to next task.

Options:
  1. Fix now (recommended)
  2. Skip review (not recommended - will fail QA)

Your choice: _
```

**After fix:**

```
✓ Code updated (src/middleware.py)
✓ Tests still passing (3/3)

⏳ Re-running progressive code review...

✓ REVIEW RESULT: PASS

No issues found. Great work!

✓ Task 2 marked complete [x]

Moving to Task 3...
```

## Performance Comparison

### Scenario: Story with 6 tasks, 4 issues introduced

**Without Progressive Review:**
```
Development time:        6 hours
QA review time:          1 hour
Issues found:            4 (2 HIGH, 2 MEDIUM)
Context switch:          Developer returns next day
Fix time per issue:      30 min (context loss, refactoring)
Total fix time:          2 hours
Total story time:        9 hours
Developer frustration:   High (major rework needed)
```

**With Progressive Review:**
```
Development time:        6.5 hours (+0.5 for review prompts)
Progressive reviews:     6 tasks × 30 sec = 3 min
QA review time:          15 min (most issues caught)
Issues found:
  - Progressive: 3 (2 HIGH, 1 MEDIUM) - fixed immediately
  - Final QA: 1 (LOW)
Fix time per issue:      5 min (context fresh, small scope)
Total fix time:          20 min
Total story time:        7.25 hours
Developer frustration:   Low (incremental fixes, learning)

Time saved: 1.75 hours (19% faster)
```

## Real Example from HomeIQ

**Story 17.3: Essential Performance Metrics**

This story implemented metrics collection with 8 tasks. Potential issues that progressive review would catch:

```
Task 1: Set up metrics collector
  → Progressive review: PASS

Task 2: Add timing decorator
  → Progressive review: CONCERNS
     - MEDIUM: Decorator doesn't handle async functions properly
     - Fixed immediately (added asyncio.iscoroutinefunction check)

Task 3: Implement counter metrics
  → Progressive review: PASS

Task 4: Implement gauge metrics
  → Progressive review: PASS

Task 5: Add InfluxDB integration
  → Progressive review: BLOCK
     - HIGH: Synchronous InfluxDB writes in async code
     - HIGH: No batching (writes individual points)
     - References: CLAUDE.md#database-performance (batch 1000 points)
     - Fixed immediately (switched to async batch writer)

Task 6: Create metrics endpoint
  → Progressive review: CONCERNS
     - MEDIUM: No caching (endpoint calls InfluxDB on each request)
     - References: CLAUDE.md#caching-strategies
     - Fixed immediately (added 60s cache TTL)

Task 7: Add health metrics
  → Progressive review: PASS

Task 8: Write integration tests
  → Progressive review: CONCERNS
     - LOW: Missing test for metrics expiry
     - Deferred to final QA (acceptable)

Result:
  - 5 issues caught during development
  - 4 fixed immediately (total fix time: 20 min)
  - 1 deferred (handled in final QA)
  - Final QA: PASS on first review (vs likely FAIL without progressive)
```

## Summary

Progressive code review transforms the dev workflow from:
- **Waterfall**: Code everything → Review → Fix everything
- **To Incremental**: Code task → Review → Fix → Next task

**Key benefits:**
1. **Fresh context**: Fix while code is still in mind
2. **Lower cost**: 5 min fix vs 30 min later
3. **Learning**: Immediate feedback improves future coding
4. **Quality**: Issues don't compound across tasks
5. **Confidence**: Know code is solid before final QA

**For HomeIQ specifically:**
- Performance issues caught immediately (CLAUDE.md violations)
- Async/await mistakes fixed before they spread
- Database optimization enforced (batching, caching)
- Security issues blocked before continuing

Start with this on your next story and measure the results!
