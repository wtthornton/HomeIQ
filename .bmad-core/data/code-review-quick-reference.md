<!-- Powered by BMAD™ Core -->

# Code Review Integration - Quick Reference

## 🎯 The Problem

**Current:** Dev completes story → QA finds issues → Context lost, expensive fixes
**Solution:** Review after EACH task → Fix while context fresh → 20x faster fixes

## 🏆 Recommended Approach: Progressive Task Reviews

**When:** After completing each task within a story
**Cost:** $0.30-0.45 per story
**Time:** +5-10 min per story, saves 1-2 hours
**ROI:** 20x minimum

## ⚡ Quick Start (5 Minutes)

### 1. Add to `core-config.yaml`

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
    review_focus: [security, performance, testing, standards]
```

### 2. Test on One Task

```
1. Dev implements Task 1
2. Run: "Review this task using progressive-code-review"
3. Fix HIGH severity issues (BLOCK)
4. Defer or fix CONCERNS
5. Mark task complete
```

### 3. Measure

Track for first story:
- Issues caught: ___
- Fixed immediately: ___
- Time saved: ___

## 🔍 What Gets Reviewed

### Security (Priority: CRITICAL)
- Auth/authorization bypasses
- SQL injection, XSS
- Exposed secrets
- Crypto issues

### Performance (Priority: HIGH - HomeIQ Specific)
Uses `CLAUDE.md` as reference:
- ✗ Blocking async operations
- ✗ N+1 database queries
- ✗ Unbatched writes (<100 points)
- ✗ Missing caching
- ✗ Unbounded queries (no LIMIT)
- ✗ Sync HTTP in async (requests vs aiohttp)

### Testing (Priority: MEDIUM)
- Missing critical path tests
- Poor edge case coverage
- Weak error scenario tests

### Code Quality (Priority: LOW)
- High complexity
- Code duplication
- Poor naming

## 📊 Decision Logic

| Severity | Action | Example |
|----------|--------|---------|
| **HIGH** | BLOCK - must fix to continue | Auth bypass, blocking async, SQL injection |
| **MEDIUM** | CONCERNS - fix now or defer | Missing cache, moderate complexity, edge case tests |
| **LOW** | PASS - log for final QA | Minor style, optional optimizations |

## 🎨 Developer Experience

**Task completion with review:**

```
✓ Code written
✓ Tests passing

⏳ Running review...

⚠️  BLOCK: HIGH severity issue found

Issue: Blocking JWT decode in async function
File: src/middleware.py:23
Fix: Use async JWT library or asyncio.to_thread()
Reference: CLAUDE.md#api-performance

Action: Fix now to continue

---

✓ Code fixed
✓ Re-review PASS
✓ Task marked complete [x]
```

## 💰 Cost & ROI

| Metric | Value |
|--------|-------|
| Reviews per story | 10-15 |
| API cost | $0.30-0.45 |
| Time added | 5-10 min |
| Time saved | 1-2 hours |
| Fix cost reduction | 30 min → 5 min per issue |
| **ROI** | **20x minimum** |

## 📁 Files Created

```
.bmad-core/
├── tasks/
│   └── progressive-code-review.md          ← Task definition
├── data/
│   ├── code-review-integration-guide.md    ← Full guide
│   ├── code-review-config-template.yaml    ← Config examples
│   └── code-review-quick-reference.md      ← This file
├── utils/
│   └── progressive-review-implementation-example.md
└── CODE_REVIEW_INTEGRATION_SUMMARY.md      ← Start here
```

## 🚀 3-Phase Rollout

### Phase 1 (Week 1): Progressive Reviews
- Add config
- Test on 2-3 stories
- Measure results
- **Decision point:** Continue if catching >70% of issues

### Phase 2 (Week 2-3): Background Reviews (Optional)
- For stories with 10+ tasks
- Real-time feedback
- Higher cost, higher value
- **Decision point:** Use if stories consistently >8 hours

### Phase 3 (Week 3): Pre-Commit Hook
- Use your original script
- Safety net only
- Catches anything that slipped through

## ⚙️ Configuration Scenarios

### Simple Projects (3-5 tasks)
```yaml
progressive_review:
  enabled: true
  severity_blocks: [high]
```

### Medium Projects (5-10 tasks, HomeIQ typical)
```yaml
progressive_review:
  enabled: true
  severity_blocks: [high]
performance_checks:
  enabled: true
  reference_doc: "CLAUDE.md"
```

### Critical Projects (security-sensitive)
```yaml
progressive_review:
  enabled: true
  severity_blocks: [high, medium]  # Stricter
background_review:
  enabled: true
  auto_start_conditions:
    min_tasks: 5
```

## 🎯 HomeIQ-Specific Checks

Reviews automatically check against `CLAUDE.md`:

```python
# Example findings for HomeIQ

PERF-001: Blocking async operation
  → CLAUDE.md#api-performance (Async Everything)
  → Severity: HIGH

PERF-002: Unbatched InfluxDB writes
  → CLAUDE.md#event-processing (Batch 1000 points)
  → Severity: HIGH

PERF-003: Missing cache on expensive query
  → CLAUDE.md#caching-strategies (Cache expensive ops)
  → Severity: MEDIUM

DB-001: N+1 query in device lookup
  → CLAUDE.md#database-performance (Use eager loading)
  → Severity: HIGH
```

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Too many false positives | Increase severity threshold |
| Missing critical issues | Enhance review prompts, add project context |
| Developer frustration | Only block on HIGH, make CONCERNS optional |
| High API costs | Reduce max_tokens, increase cache_ttl |
| Reviews too slow | Use faster model, reduce context size |

## ✅ Success Metrics (After 5 Stories)

- [ ] 70-90% of issues caught before final QA
- [ ] 5x faster fix time per issue (30min → 5min)
- [ ] Higher code quality scores
- [ ] Fewer rework cycles
- [ ] Developer satisfaction: positive

## 🚫 What NOT to Do

- ❌ Don't block on MEDIUM/LOW severity (kills momentum)
- ❌ Don't try all three approaches at once (start simple)
- ❌ Don't skip measuring results (need data to improve)
- ❌ Don't override safety checks frequently (defeats purpose)
- ❌ Don't use for prototypes/experiments (overkill)

## 💡 Pro Tips

1. **Start conservative:** Only block on HIGH, learn patterns
2. **Use CLAUDE.md:** HomeIQ-specific performance checks
3. **Fix immediately:** 5 min now vs 30 min later
4. **Track metrics:** Measure to improve
5. **Iterate prompts:** Add project context based on findings
6. **Keep pre-commit hook:** Defense in depth
7. **Trust the process:** Short-term friction, long-term gain

## 📖 Learn More

- **Full guide:** `code-review-integration-guide.md`
- **Technical details:** `progressive-review-implementation-example.md`
- **Configuration:** `code-review-config-template.yaml`
- **Summary:** `CODE_REVIEW_INTEGRATION_SUMMARY.md`

## 🎬 Next Action

1. Read `CODE_REVIEW_INTEGRATION_SUMMARY.md` (10 min)
2. Add config to `core-config.yaml` (2 min)
3. Test on one task (5 min)
4. Measure and iterate

**The infrastructure is ready. Just add config and go!**

---

**Remember:** Progressive reviews shift quality left. Fix issues when they're created, not discovered. 20x ROI minimum.
