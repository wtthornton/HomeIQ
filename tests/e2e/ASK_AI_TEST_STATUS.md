# Ask AI E2E Tests - Current Status

**Date:** March 18, 2026 (Epic 90 update)
**Previous:** October 19, 2025 (archived below)

---

## Current State (Post Epic 90)

### ask-ai-complete.spec.ts (26 tests)

| Group | Tests | Timeout | Retries | Expected Pass Rate |
|-------|-------|---------|---------|-------------------|
| **Fast -- UI Only** | 4 | 30s | 0 | 100% |
| **Slow -- OpenAI Round-Trip** | 22 | 120s | 2 | 90%+ |

**Changes (Story 90.4):**
- Split into Fast/Slow describe blocks
- All `waitForToast` timeouts increased to 45-60s
- All OpenAI tests use `test.slow()` + `test.setTimeout(120_000)`
- `expect.poll()` replaces fixed waits for async state checks
- Retry config: 2 retries for OpenAI tests

### ask-ai-to-ha-automation.spec.ts (14 tests)

| Verification | Coverage | Story |
|-------------|----------|-------|
| L1: API exists | 14/14 tests | Original |
| L2: YAML valid | 14/14 tests | 90.3 |
| L3: YAML semantic | 14/14 tests | 90.3 |

**Changes (Story 90.3):**
- All 14 tests now fetch automation YAML from HA API after creation
- Structural validation: trigger platform, action services, entity IDs, alias
- Prompt-specific assertions: presence→state trigger, time→time trigger, scene→scene.turn_on, etc.

### Test Infrastructure

| Component | File | Story |
|-----------|------|-------|
| YAML validation helper | `helpers/yaml-validator.ts` | 90.2 |
| Test cleanup harness | `helpers/test-cleanup.ts` | 90.5 |
| CI workflow (live AI) | `.github/workflows/test-live-ai.yml` | 90.6 |

### Backend Integration Tests (New)

| File | Tests | What it Proves |
|------|-------|---------------|
| `test_ask_ai_yaml_pipeline.py` | 7 | Chat → tool_call → YAML structure |
| `test_yaml_validation_service.py` | 15 | 6-stage validation (syntax→safety) |
| `test_hybrid_flow_pipeline.py` | 7 | Deterministic compile, cross-validation |

### Predictive Service Tests (New)

| Service | Tests | Coverage |
|---------|-------|----------|
| Blueprint suggestion scorer | 35 | Weights, complexity, fallback, edge cases |
| Blueprint suggestion API | 15 | Endpoints, filters, admin auth |
| Rule recommendation ML | 30 | Collaborative, device-based, popular, cold-start |
| Rule recommendation API | 27 | Endpoints, feedback, patterns |

---

## How to Run

### Live AI Tests (requires running stack + OpenAI)
```bash
AI_SERVICES_AVAILABLE=1 npx playwright test \
  ask-ai-complete.spec.ts \
  ask-ai-to-ha-automation.spec.ts \
  --retries=2 --workers=1
```

### Fast UI Tests Only (no OpenAI needed)
```bash
npx playwright test ask-ai-complete.spec.ts --grep "Fast"
```

### Backend Integration Tests
```bash
pytest tests/integration/test_ask_ai_yaml_pipeline.py -m integration
pytest tests/integration/test_yaml_validation_service.py -m integration
pytest tests/integration/test_hybrid_flow_pipeline.py -m integration
```

### CI Workflow
```bash
gh workflow run test-live-ai.yml
```

---

## Historical: October 2025 Status

> **Archived from original ASK_AI_TEST_STATUS.md**
>
> - Date: October 19, 2025
> - Pass rate: 27% (7/26 tests)
> - Root cause: Timing issues — `waitForToast` used 10-15s timeouts, OpenAI takes 10-25s
> - All 19 failing tests timed out waiting for toast messages
> - Recommendations: increase timeouts to 45s, add retry logic, split fast/slow tests
>
> All recommendations have been implemented in Epic 90 (Stories 90.3, 90.4).
