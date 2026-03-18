# Ask AI YAML Verification Test Matrix

**Epic 90** | **Created:** 2026-03-18

## Overview

This document maps the complete Ask AI → YAML verification coverage across three verification levels, ensuring generated automations are not just created but structurally correct and semantically aligned with the user's intent.

## Verification Levels

| Level | What it Checks | Where |
|-------|---------------|-------|
| **L1: API Exists** | Automation ID returned, appears in deploy API | `ask-ai-to-ha-automation.spec.ts` (existing) |
| **L2: YAML Valid** | Trigger/action arrays present, platform values valid, entity ID format correct | `yaml-validator.ts` helper (Story 90.2) |
| **L3: YAML Semantic** | Trigger platform matches prompt intent, action services match intent, entity IDs reference correct devices | Per-test assertions (Story 90.3) |

## Test Matrix: 5 Prompt Categories x 3 Verification Levels

### Presence-Based Automations

| Test | Prompt | L1 | L2 | L3: Trigger | L3: Action | L3: Entities |
|------|--------|:--:|:--:|-------------|------------|--------------|
| Office presence | "Turn on office lights when motion detected in the office" | Y | Y | `state` | `light.turn_on` | `binary_sensor.*motion`, `light.*office` |
| Bar presence | "Turn on bar lights when presence detected near the bar area" | Y | Y | `state` | `light.turn_on` | `binary_sensor.*` |

### Time-Based Automations

| Test | Prompt | L1 | L2 | L3: Trigger | L3: Action | L3: Entities |
|------|--------|:--:|:--:|-------------|------------|--------------|
| Roborock DND | "Enable Roborock DND mode at 10pm" | Y | Y | `time` | `switch.turn_on` | `switch.*roborock*` |
| Bedtime scene | "At 10:30pm activate the bedtime scene and turn off..." | Y | Y | `time` | `scene.turn_on`, `switch.turn_on` | scene entity |
| Sunset lighting | "When the sun sets, activate the evening lighting scene" | Y | Y | `sun` | `scene.turn_on`, `light.turn_on` | scene + light entities |

### Device-State Automations

| Test | Prompt | L1 | L2 | L3: Trigger | L3: Action | L3: Entities |
|------|--------|:--:|:--:|-------------|------------|--------------|
| Office fan auto-off | "Auto-turn off office fan switch when office is unoccupied" | Y | Y | `state` | `*turn_off` | `switch.*fan`, `binary_sensor.*` |
| Movie mode | "When Frame TV turns on, dim living room lights to 20%" | Y | Y | `state` | `light.turn_on` | `media_player.*`, `light.*` |
| Office TV nightlight | "Turn on office LED strip when office TV turns on" | Y | Y | `state` | `switch.turn_on` | `media_player.*`, `switch.*` |

### Security/Outdoor Automations

| Test | Prompt | L1 | L2 | L3: Trigger | L3: Action | L3: Entities |
|------|--------|:--:|:--:|-------------|------------|--------------|
| Outdoor motion | "Turn on outdoor lights when backyard motion detected" | Y | Y | `state` | `light.turn_on` | `binary_sensor.*`, `light.*` |
| Garage door | "Turn on garage lights when garage door opens" | Y | Y | `state` | `light.turn_on` | `binary_sensor.*`, `light.*garage*` |
| Front door motion | "Turn on porch lights when front door motion detected at night" | Y | Y | `state` | `light.turn_on` | `binary_sensor.*`, `light.*` |

### Multi-Domain Automations

| Test | Prompt | L1 | L2 | L3: Trigger | L3: Action | L3: Entities |
|------|--------|:--:|:--:|-------------|------------|--------------|
| Away mode | "When everyone leaves home, turn off all lights, switches, and media players" | Y | Y | `state` | `light.turn_off`, `switch.turn_off`, `media_player.turn_off` | `person.*` |
| Welcome home (approve) | "When I arrive home, turn on entryway lights and activate welcome scene" | Y | Y | `state` | `light.turn_on`, `scene.turn_on` | `person.*` |

## Backend Integration Tests (No UI)

| Test File | Tests | What it Covers |
|-----------|-------|---------------|
| `test_ask_ai_yaml_pipeline.py` | 7 | Chat API → tool_call → YAML preview (5 prompt categories + 2 contract tests) |
| `test_yaml_validation_service.py` | 15 | 6-stage validation pipeline (syntax, schema, entity, service, safety, style) |
| `test_hybrid_flow_pipeline.py` | 7 | Plan → Validate → Compile determinism + cross-service validation |

## Predictive Service Tests

| Test File | Tests | What it Covers |
|-----------|-------|---------------|
| `blueprint-suggestion-service/tests/test_suggestion_scorer.py` | 35 | Score calculation, weight normalization, complexity bonus, edge cases |
| `blueprint-suggestion-service/tests/test_api.py` | 15 | HTTP endpoints, filters, pagination, admin auth |
| `rule-recommendation-ml/tests/test_recommender.py` | 30 | Collaborative filtering, device-based, popular, cold-start, save/load |
| `rule-recommendation-ml/tests/test_api.py` | 27 | HTTP endpoints, feedback, recommendations, patterns |

## Pass-Rate Tracking

### CI Artifact Format

The `test-live-ai.yml` workflow produces a `pass-rate.json` artifact:

```json
{
  "timestamp": "2026-03-18T03:00:00Z",
  "run_id": "12345678",
  "branch": "master",
  "total": 31,
  "passed": 28,
  "flaky": 2,
  "failed": 1,
  "pass_rate": 96.8
}
```

### Trend Analysis

Download pass-rate artifacts from GitHub Actions to track stability over time:
```bash
gh run list --workflow=test-live-ai.yml --json databaseId,conclusion,createdAt
gh run download <run_id> --name live-ai-pass-rate
```

## Files Reference

| File | Purpose | Story |
|------|---------|-------|
| `tests/e2e/helpers/yaml-validator.ts` | Fetch + validate automation YAML from HA | 90.2 |
| `tests/e2e/helpers/test-cleanup.ts` | Automation tracking + cleanup harness | 90.5 |
| `tests/e2e/ask-ai-to-ha-automation.spec.ts` | 14 E2E tests with YAML assertions | 90.3 |
| `tests/e2e/ask-ai-complete.spec.ts` | 26 tests (fast/slow split, resilient waits) | 90.4 |
| `tests/integration/test_ask_ai_yaml_pipeline.py` | Backend chat → YAML round-trip | 90.1 |
| `tests/integration/test_yaml_validation_service.py` | Validation service 6-stage pipeline | 90.7 |
| `tests/integration/test_hybrid_flow_pipeline.py` | Hybrid Flow determinism proof | 90.9 |
| `.github/workflows/test-live-ai.yml` | CI workflow for live AI tests | 90.6 |
