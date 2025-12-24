# Progressive Code Review Results

This directory contains progressive task-level code review results.

## Purpose

Progressive reviews run after each task completion during story development, catching issues early when context is fresh and fixes are cheap.

## File Naming Convention

`{epic}.{story}-task-{n}.yml`

Examples:
- `1.3-task-2.yml` - Review for Story 1.3, Task 2
- `17.3-task-5.yml` - Review for Story 17.3, Task 5

## Review Process

1. Developer completes a task
2. Progressive review automatically runs (if enabled in core-config.yaml)
3. Review produces PASS/CONCERNS/BLOCK decision
4. HIGH severity issues block task completion
5. MEDIUM/LOW severity issues logged for final QA
6. Results saved to this directory

## Configuration

See `.bmad-core/core-config.yaml` → `qa.progressive_review`

## Related Documentation

- `.bmad-core/tasks/progressive-code-review.md` - Task definition
- `.bmad-core/CODE_REVIEW_INTEGRATION_SUMMARY.md` - Implementation guide
- `.bmad-core/data/code-review-quick-reference.md` - Quick reference

## Performance Checks

Reviews automatically check against CLAUDE.md for HomeIQ-specific performance requirements:
- Async/await violations
- Database anti-patterns (N+1, unbatched writes)
- Missing caching
- Security vulnerabilities

## Metrics

Track effectiveness:
- Issues found per task
- Issues fixed immediately vs deferred
- Time saved vs finding in final QA
- False positive rate
