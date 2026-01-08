# Build Feature

Build a new feature for HomeIQ using the complete TappsCodingAgents workflow.

## Instructions

Execute the full Simple Mode build workflow:

```
@simple-mode *build "{{feature_description}}"
```

This orchestrates:
1. **@enhancer** - Enhance prompt with requirements
2. **@planner** - Create user stories
3. **@architect** - Design architecture (Epic 31 compliant)
4. **@designer** - API/component design
5. **@implementer** - Code implementation
6. **@reviewer** - Quality review (must score ≥70)
7. **@tester** - Generate tests

## Output

Workflow documentation saved to:
- `docs/workflows/simple-mode/step1-enhanced-prompt.md`
- `docs/workflows/simple-mode/step2-user-stories.md`
- `docs/workflows/simple-mode/step3-architecture.md`
- `docs/workflows/simple-mode/step4-design.md`
- `docs/workflows/simple-mode/step6-review.md`
- `docs/workflows/simple-mode/step7-testing.md`

## Parameters

- `feature_description`: What feature to build (e.g., "Add device battery monitoring to health dashboard")
