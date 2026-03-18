# Flaky Test Registry (Epic 89.3)

Tests listed here require live services or have known intermittent failures.
They are excluded from the main CI gate but run in a separate allow-fail job.

## Quarantine Policy

1. **Add** a test here when it fails intermittently in CI but passes locally
2. **Tag** the test with `test.fixme()` and reference this file
3. **Remove** from quarantine once the root cause is fixed and the test is stable for 5+ CI runs

## Quarantined Tests

### Require Live AI Services (`AI_SERVICES_AVAILABLE=1`)

These tests need a running OpenAI API key and full backend stack.
They are skipped in CI by default via `test.skip(!process.env.AI_SERVICES_AVAILABLE)`.

| File | Test | Reason | Date Added |
|------|------|--------|------------|
| `ai-automation-ui/pages/enhancement-button.spec.ts` | Enhancement Button — Live AI (3 tests) | Requires live OpenAI + ha-ai-agent-service | 2026-03-18 |
| `ask-ai-complete.spec.ts` | All tests (19 tests) | Full OpenAI round-trips, 90s timeout — **Epic 90.4 reliability fixes applied, tracked in `test-live-ai.yml` CI job** | 2026-03-18 |
| `ask-ai-to-ha-automation.spec.ts` | All tests (12 tests) | Full pipeline: OpenAI + HA automation creation, 120s timeout — **Epic 90.3 YAML assertions added, tracked in `test-live-ai.yml` CI job** | 2026-03-18 |
| `ask-ai-debug.spec.ts` | Debug tests (2 tests) | Debugging utility, not for CI | 2026-03-18 |

### Intermittent Failures

| File | Test | Symptom | Root Cause | Date Added |
|------|------|---------|------------|------------|
| `visual-regression.spec.ts` | Dark/mobile/tablet snapshots | Missing baselines | Baselines not yet generated (Epic 89.4) | 2026-03-18 |

## CI Job for Live AI Tests

The `test-live-ai.yml` workflow (Epic 90, Story 90.6) runs quarantined Ask AI tests against the Docker stack with live OpenAI:
- **Trigger:** Manual (`workflow_dispatch`) + nightly at 3:00 AM UTC
- **Tests:** `ask-ai-to-ha-automation.spec.ts` + `ask-ai-complete.spec.ts`
- **Config:** retries=2, workers=1, timeout=180s
- **Artifacts:** HTML report, JSON results, pass-rate trend data
- **Un-quarantine criteria:** 5+ consecutive green runs in this workflow

## How to Run Quarantined Tests Locally

```bash
# Run all live-AI tests (requires running stack + OPENAI_API_KEY)
AI_SERVICES_AVAILABLE=1 npx playwright test --grep "Live AI|Complete Workflow"

# Run just the enhancement button live tests
AI_SERVICES_AVAILABLE=1 npx playwright test enhancement-button.spec.ts

# Run the full Ask AI pipeline tests
AI_SERVICES_AVAILABLE=1 npx playwright test ask-ai-complete.spec.ts ask-ai-to-ha-automation.spec.ts
```
