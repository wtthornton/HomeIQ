<!-- Powered by BMAD™ Core -->

# Code Review Integration Guide

Comprehensive guide for integrating AI code review into BMAD workflows for long agent builds.

## Problem Statement

**Current workflow:**
```
Dev builds entire story → QA reviews → Issues found → Dev fixes → Repeat
```

**Problem:** By the time QA reviews, developer may have written 500+ lines with architectural issues that require major refactoring. Feedback loop is too long.

**Your pre-commit hook idea:** Good for preventing bad commits, but:
- Only runs on commit (dev may work for hours before committing)
- Binary pass/fail (blocks all work vs continuous feedback)
- Doesn't integrate with BMAD's structured workflow

## Recommended Solutions

### 🏆 **Option 1: Progressive Task-Level Review (BEST FOR MOST CASES)**

**When:** After each task completion within a story

**How it works:**
```
Task 1: Implement → Test → Review → Fix if HIGH → Mark [x]
Task 2: Implement → Test → Review → Fix if HIGH → Mark [x]
Task 3: Implement → Test → Review → Fix if HIGH → Mark [x]
Final QA: Comprehensive review → Gate decision
```

**Benefits:**
- ✅ Catches issues when context is fresh
- ✅ Lower cost to fix (issues found early)
- ✅ Maintains momentum (only HIGH blocks)
- ✅ No external dependencies
- ✅ Works in any IDE/environment

**Implementation:**
- Task: `.bmad-core/tasks/progressive-code-review.md`
- Config: Add to `core-config.yaml` (see below)
- Cost: ~10-20 reviews per story (~$0.30-0.60)

**Best for:**
- Stories with 3-10 tasks
- 2-8 hour development time
- Standard IDE environments
- Cost-conscious teams

---

### ⚡ **Option 2: Background Continuous Review (BEST FOR LONG BUILDS)**

**When:** Continuously during development (file saves trigger reviews)

**How it works:**
```
Dev writes code  ─┬─> Background watcher
                  │   ├─> Detects file change
                  │   ├─> Runs AI review (async)
                  │   ├─> Caches results
                  │   └─> Notifies if HIGH severity
                  │
                  └─> Dev continues working (unblocked)
```

**Benefits:**
- ✅ Real-time feedback (critical issues flagged immediately)
- ✅ Zero interruption (runs in background)
- ✅ Context-aware (reviews while code fresh)
- ✅ Accumulates evidence for final QA

**Trade-offs:**
- ⚠️ Requires file system monitoring
- ⚠️ Higher API costs (more frequent reviews)
- ⚠️ May have false positives

**Implementation:**
- Task: `.bmad-core/tasks/background-code-review.md`
- Requires: Python watchdog or equivalent
- Cost: ~20-40 reviews per story (~$0.60-1.20)

**Best for:**
- Stories with 10+ tasks
- 8+ hour development time
- Complex codebases
- Critical applications (security-sensitive)

---

### 🔒 **Option 3: Pre-Commit Hook (COMPLEMENTARY)**

**When:** Before git commit

**How it works:**
```
git commit → Hook triggers → AI reviews staged changes → Pass/Fail → Commit or block
```

**Benefits:**
- ✅ Prevents bad code from entering repo
- ✅ Works with any workflow
- ✅ Language/framework agnostic

**Trade-offs:**
- ⚠️ Late in cycle (issues already written)
- ⚠️ Binary decision (blocks all work)
- ⚠️ Doesn't integrate with BMAD tasks

**Implementation:**
- See example in your original message
- Add to `.git/hooks/pre-commit`

**Best for:**
- Additional safety net
- Teams with multiple devs
- Open source projects

---

## Recommended Hybrid Approach

**For HomeIQ and similar projects:**

```
1. Progressive task reviews (primary)
   ↓
2. Background reviews (for critical services)
   ↓
3. Pre-commit hook (safety net)
   ↓
4. Full QA review (comprehensive gate)
```

**Rationale:**
- Progressive reviews catch 80% of issues early (low cost)
- Background reviews monitor critical paths (auth, payments, security)
- Pre-commit hook prevents accidents
- Final QA ensures nothing slipped through

## Implementation Roadmap

### Phase 1: Progressive Reviews (Week 1)

1. **Add configuration to core-config.yaml:**

```yaml
qa:
  progressive_review:
    enabled: true
    review_location: docs/qa/progressive
    auto_trigger: true
    severity_blocks: [high]

    ai_config:
      model: "claude-sonnet-4-5"
      max_tokens: 4000
      temperature: 0.0

    review_focus:
      - security
      - performance
      - testing
      - standards
```

2. **Update dev agent command:**

Add to `.bmad-core/agents/dev.md`:

```yaml
commands:
  - develop-story:
      # ... existing ...
      progressive_review: true  # Enable task-level reviews
```

3. **Test on single story:**
   - Pick a medium-complexity story (5-7 tasks)
   - Run with progressive reviews enabled
   - Measure: time saved, issues caught, developer experience

4. **Iterate:**
   - Adjust severity thresholds
   - Refine review prompts
   - Optimize for false positive rate

### Phase 2: Background Reviews (Week 2-3)

**Only if Phase 1 successful and team wants real-time feedback**

1. **Install dependencies:**

```bash
pip install watchdog aiofiles
```

2. **Add configuration:**

```yaml
qa:
  background_review:
    enabled: true
    log_location: docs/qa/background

    auto_start_conditions:
      min_tasks: 8
      estimated_hours: 4

    file_patterns:
      - "services/**/*.py"    # Backend only initially

    notify_severity: [high]

    cost_controls:
      max_reviews_per_hour: 20
      cache_ttl: 3600
```

3. **Create background runner:**

```python
# .bmad-core/utils/background_reviewer.py
# Implementation from background-code-review.md
```

4. **Integrate with dev agent:**
   - Auto-start when conditions met
   - Status check command
   - Graceful shutdown

### Phase 3: Pre-Commit Hook (Week 3)

**Safety net for all developers**

1. **Create hook:**

```bash
# .git/hooks/pre-commit
#!/usr/bin/env bash
# Use your original pre-commit hook script
```

2. **Configure thresholds:**
   - Score threshold: 75 (allow some warnings)
   - Block on: HIGH security, critical performance
   - Allow with warnings: Medium severity

3. **Team rollout:**
   - Document bypass procedure (for emergencies)
   - Train team on interpreting results
   - Iterate on threshold tuning

## Decision Matrix

**Which approach should you use?**

| Scenario | Progressive | Background | Pre-Commit |
|----------|-------------|------------|------------|
| Story has <5 tasks | ✅ Yes | ❌ No (overkill) | ✅ Yes |
| Story has 5-10 tasks | ✅ Yes | ⚠️ Optional | ✅ Yes |
| Story has 10+ tasks | ✅ Yes | ✅ Yes | ✅ Yes |
| Security-critical code | ✅ Yes | ✅ Yes | ✅ Yes |
| Performance-critical (CLAUDE.md) | ✅ Yes | ✅ Yes | ✅ Yes |
| Prototype/Experiment | ❌ No | ❌ No | ⚠️ Optional |
| Open source contributors | ⚠️ Optional | ❌ No | ✅ Yes |

## Cost Analysis

**API costs per story (Claude Sonnet 4):**

| Approach | Reviews per Story | Input Tokens | Output Tokens | Cost per Story |
|----------|-------------------|--------------|---------------|----------------|
| Progressive only | 8-12 | ~150K | ~40K | $0.30-0.45 |
| Background only | 30-50 | ~300K | ~80K | $0.90-1.50 |
| Progressive + Background | 15-25 | ~225K | ~60K | $0.65-1.00 |
| Pre-commit only | 1 | ~50K | ~10K | $0.15 |

**ROI calculation:**

- Average issue cost (found in final QA): 30 min fix = $25 (at $50/hr)
- Average issue cost (found progressively): 5 min fix = $4
- Savings per issue: $21
- Issues caught early per story: 2-4
- **ROI: 40-80x** (save $42-84 in dev time, spend $0.30-1.00 on reviews)

## Performance-Specific Reviews (HomeIQ)

Your `CLAUDE.md` contains comprehensive performance guidelines. Reviews should reference it:

**Key checks for HomeIQ:**

1. **Async/Await:**
   - Flag: Blocking operations in async functions
   - Reference: CLAUDE.md#api-performance

2. **Database:**
   - Flag: N+1 queries, missing indexes, unbounded queries
   - Reference: CLAUDE.md#database-performance

3. **Caching:**
   - Flag: Expensive operations without caching, inappropriate TTLs
   - Reference: CLAUDE.md#caching-strategies

4. **Batch Processing:**
   - Flag: Individual writes instead of batching
   - Reference: CLAUDE.md#event-processing-performance

**Review prompt template:**

```
Review this code for HomeIQ performance requirements:

PERFORMANCE TARGETS (from CLAUDE.md):
- API response: <100ms
- Device queries: <10ms (SQLite)
- Event processing: 1000+ events/sec
- Memory: <512MB per service

CODE CHANGE:
{diff}

Check for:
1. Blocking async operations (violates "Async Everything")
2. Unbatched database writes (should batch 100-1000 points)
3. Missing caching for expensive operations
4. Memory leaks or unbounded growth

Reference specific CLAUDE.md sections in findings.
```

## Monitoring & Metrics

**Track effectiveness:**

```yaml
# docs/qa/review-metrics.yml

review_effectiveness:
  story: "1.3"

  progressive_reviews:
    tasks_reviewed: 8
    issues_found: 12
    issues_fixed_immediately: 8
    issues_deferred: 4

    severity_breakdown:
      high: 2
      medium: 7
      low: 3

    time_saved_estimate: "90 min"  # vs finding in final QA

  background_reviews:
    files_monitored: 15
    reviews_triggered: 32
    issues_found: 6
    developer_notified: 2

  final_qa:
    new_issues_found: 3  # Should be low if progressive worked
    deferred_issues_fixed: 4
    gate: "PASS"
```

**Success metrics:**

- **Issue detection rate:** >80% of issues caught before final QA
- **Fix time reduction:** <5 min per issue (vs 30 min in final QA)
- **False positive rate:** <20%
- **Developer satisfaction:** Survey after 5 stories

## Next Steps

1. **Start with Progressive Reviews:**
   - Lowest risk, highest ROI
   - Test on 2-3 stories
   - Gather metrics

2. **Evaluate results:**
   - If catching 80%+ of issues → Success, keep using
   - If <50% → Tune prompts and thresholds
   - If developers frustrated → Reduce auto-blocking

3. **Consider Background Reviews if:**
   - Stories consistently >8 hours
   - Security-critical code
   - Team wants real-time feedback
   - Budget allows higher API costs

4. **Add Pre-Commit Hook:**
   - After progressive reviews proven
   - As safety net, not primary defense
   - Document bypass procedure

## Questions to Ask Yourself

Before implementing:

1. **What's our average story completion time?**
   - <4 hours → Progressive only
   - 4-8 hours → Progressive + consider background
   - 8+ hours → Progressive + background

2. **What's our tolerance for interruptions?**
   - Low → Background (async notifications)
   - Medium → Progressive (at task boundaries)
   - High → Pre-commit only

3. **What's our API budget?**
   - Limited → Progressive only ($0.30-0.45/story)
   - Moderate → Progressive + pre-commit ($0.45-0.60/story)
   - Generous → All three ($0.80-1.20/story)

4. **What's our risk profile?**
   - Low (internal tools) → Progressive
   - Medium (business apps) → Progressive + pre-commit
   - High (security/finance) → All three

## Conclusion

**For HomeIQ specifically, I recommend:**

```
Phase 1 (Now): Progressive task-level reviews
  ↓
Phase 2 (After 5 stories): Add background reviews for critical services
  ↓
Phase 3 (After 10 stories): Add pre-commit hook as safety net
```

**Why this order:**
1. Progressive reviews have best ROI with lowest risk
2. Learn what issues are common in your codebase
3. Tune prompts based on actual findings
4. Add background reviews once patterns identified
5. Pre-commit hook catches anything that slips through

**Expected outcomes:**
- 80% of issues caught before final QA
- 5x faster fix time per issue
- Better code quality
- More confident deployments
- Developer learning from review feedback

Start simple, measure results, iterate. Don't try to implement all three at once.
