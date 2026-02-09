# Phase 4: Automation API Documentation

**Epic:** HomeIQ Automation Platform Improvements  
**Date:** February 2026  
**Status:** Complete

---

## 1. Unified Validation API

**Endpoint:** `POST /api/v1/automations/validate`  
**Service:** ai-automation-service-new (Port 8024)  
**Base URL:** `http://localhost:8024`

Validates Home Assistant automation YAML and returns structured entity/service validation.

### Request

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `yaml_content` | string | *required* | Home Assistant automation YAML |
| `normalize` | bool | `true` | Normalize YAML to canonical format |
| `validate_entities` | bool | `true` | Validate entity IDs exist in Home Assistant |
| `validate_services` | bool | `true` | Validate service calls |

### Response

| Field | Type | Description |
|-------|------|-------------|
| `valid` | bool | Overall validity |
| `errors` | string[] | All validation errors |
| `warnings` | string[] | Non-blocking warnings |
| `entity_validation` | object | `{ performed, passed, errors }` |
| `service_validation` | object | `{ performed, passed, errors }` |
| `score` | float | Validation score |
| `fixed_yaml` | string \| null | Auto-fixed YAML if fixes applied |
| `fixes_applied` | string[] | List of fixes applied |

### Consumers

- **HA AI Agent** (`ai_automation_client.py`) – validation before suggesting automations
- **ai-automation-ui** (`api.ts` `validateYAML`) – inline validation in UI
- **yaml-validation-service** – orchestrated for schema, entity, service checks

---

## 2. Deploy Response and Post-Deploy Verification

### Deploy Response Fields

When deploying a suggestion (e.g. `POST /api/v1/suggestions/{id}/deploy`), the response `data` may include:

| Field | Type | Description |
|-------|------|-------------|
| `suggestion_id` | string | Suggestion UUID |
| `automation_id` | string | Home Assistant automation entity ID |
| `status` | string | `"deployed"` |
| `state` | string \| omitted | Current HA automation state (`on`, `off`, `unavailable`) |
| `last_triggered` | string \| omitted | ISO timestamp of last trigger (from HA attributes) |
| `verification_warning` | string \| omitted | Warning when post-deploy state is `unavailable` |

### Post-Deploy Verification

After deployment, the HA client fetches the automation state via `GET /api/states/{entity_id}`. If the state is `unavailable`, it adds:

```
verification_warning: "Automation was deployed but state is 'unavailable'. Home Assistant may have failed to load it. Check HA logs for errors."
```

The UI (ConversationalDashboard, Deployed success toast) displays state, last triggered, and the verification warning when present.

---

## 3. Automation RAG Service

**Service:** ha-ai-agent-service  
**File:** `services/ha-ai-agent-service/src/services/automation_rag_service.py`

The RAG corpus includes:

- **Team Tracker reference** – Generic guide for all leagues (NFL, NBA, MLB, NHL, MLS, NCAA) and attributes (`team_score`, `opponent_score`, `trigger.from_state`, `trigger.to_state`, etc.)
- **Super Bowl guide** – Example patterns for score-increase lights

When prompts mention sports/Team Tracker (e.g. “Super Bowl lights when Seahawks score”), the RAG returns context with score-increase patterns and attribute usage.

### Reference Documents

- **Generic:** [implementation/teamtracker_automation_reference_guide.md](teamtracker_automation_reference_guide.md) – all attributes, all leagues
- **Example:** [implementation/superbowl_teamtracker_lights_guide.md](superbowl_teamtracker_lights_guide.md) – Seahawks Super Bowl lights

---

## References

- Unified validate router: `services/ai-automation-service-new/src/api/automation_yaml_validate_router.py`
- Deployment service: `services/ai-automation-service-new/src/services/deployment_service.py`
- HA client (post-deploy state): `services/ai-automation-service-new/src/clients/ha_client.py`
- Next steps plan: [implementation/AUTOMATION_IMPROVEMENTS_NEXT_STEPS_PLAN.md](AUTOMATION_IMPROVEMENTS_NEXT_STEPS_PLAN.md)
