# Background Code Review Results

This directory contains background continuous code review results.

## Purpose

Background reviews run asynchronously during development, monitoring file changes and providing real-time feedback without blocking developer flow.

## Status

**Currently:** DISABLED (see core-config.yaml → qa.background_review.enabled: false)

Background reviews are optional and recommended only for:
- Stories with 8+ tasks
- Development sessions >4 hours
- Security-critical code

## File Naming Convention

`{epic}.{story}-{timestamp}.yml`

Example:
- `1.3-20250124-103045.yml` - Background review session for Story 1.3

## How It Works (When Enabled)

1. File watcher monitors code changes
2. Debounces changes (waits 5s after last edit)
3. Runs AI review on changed files
4. Caches results to prevent duplicate reviews
5. Notifies developer of HIGH severity issues
6. Logs all findings for final QA

## To Enable

Edit `.bmad-core/core-config.yaml`:

```yaml
qa:
  background_review:
    enabled: true  # Change from false
```

## Configuration

See `.bmad-core/core-config.yaml` → `qa.background_review`

## Related Documentation

- `.bmad-core/tasks/background-code-review.md` - Task definition
- `.bmad-core/CODE_REVIEW_INTEGRATION_SUMMARY.md` - Implementation guide

## Cost Considerations

Background reviews increase API costs (~$0.60-1.20 per story vs $0.30-0.45 for progressive only).

Use only when:
- ROI justifies cost (long builds, critical code)
- Team wants real-time feedback
- Budget allows higher API usage

## Recommendation

Start with progressive reviews only. Enable background reviews after testing progressive approach on 5+ stories.
