# HYBRID_FLOW_IMPLEMENTATION.md
## HomeIQ Hybrid Automation Flow — Detailed Implementation Plan (2025+)

> Goal: Implement a **hybrid automation lifecycle** where **LLMs never author YAML directly**. Instead, the system:
> 1) uses APIs + models to reason and select a **template + parameters**, then  
> 2) uses a deterministic **compiler/validator** to generate **Home Assistant–valid YAML**, and  
> 3) deploys the resulting automation to Home Assistant with a clear approval/audit trail.

This document is intentionally detailed so it can be handed to an implementer and used as the build plan.

---

## 0) Outcomes and Success Criteria

### User outcomes
- User can use the **HA AI Agent** UI to:
  - ask for an automation (“When I walk into the office, turn on the lights”)
  - answer clarifying questions
  - preview a proposed automation in plain English
  - optionally view YAML (advanced)
  - approve, tweak, or cancel
  - see deployed automations in **Home Assistant UI**
- If HomeIQ is down, **persisted automations still run** in HA.

### System outcomes
- LLM output is **structured intent** (JSON), never YAML.
- YAML generation is **deterministic** (same inputs → same output).
- YAML is validated before deployment.
- All deployments are recorded with audit data (who/when/why/template/version).

### Engineering outcomes
- A small, versioned **Template Library** defines allowed automation shapes.
- A **YAML Compiler** converts templates + params + device graph → YAML.
- Clear contracts between services; minimal coupling.

---

## 1) Architecture Placement in HomeIQ

### Existing components (from repo/README)
- **HA AI Agent** (UI + chat entry)
- **AI Automation Service**
- **AI Core / ML / OpenVINO**
- **Data API** (Influx/SQLite access)
- **Device Intelligence** (capabilities, roles)
- **Admin API** (settings/ops)
- **Home Assistant** (execution runtime)

### New components to add (recommended)
You can implement these as modules inside `ai-automation-service` or as separate microservices; start as **modules** for speed, then split if needed.

1. **Template Library** (local, versioned)
2. **Intent → Template Planner** (LLM-facing, returns structured plan)
3. **Template Validator** (deterministic)
4. **YAML Compiler** (deterministic)
5. **Deployment Manager** (writes automation into HA + tracks state)
6. **Automation Registry** (SQLite tables for lifecycle + audit)

> Minimal footprint: implement (1–6) inside AI Automation Service and expose endpoints from there.

---

## 2) Non-Negotiable Design Rules

### Rule A — No LLM-authored YAML
- LLM must never output YAML to be deployed.
- LLM output is always a **structured plan**:
  - `template_id`
  - `parameters`
  - `confidence`
  - `clarifications_needed[]`
  - `safety_class`
  - `promotion_recommended`

### Rule B — YAML is compiled, not authored
- YAML is a **compiled artifact** produced only after:
  - template selection
  - parameter validation
  - safety checks
  - (optional) user approval

### Rule C — HA is the execution owner for persistent automations
- Persisted automations are installed in HA (YAML or HA automation config via API) so that:
  - HA restarts do not break behavior
  - the automation appears in HA UI
  - user can disable/edit in HA if desired

### Rule D — Templates are the “source code”
- Templates must be small in number, well-tested, and versioned.
- Template schemas must be strict; parameters are typed and bounded.

---

## 3) User Flow (UI → Deployed Automation)

### 3.1 Conversation lifecycle states
The UI should represent the lifecycle explicitly:

1. **Draft** (user request captured)
2. **Clarifying** (assistant asks questions)
3. **Planned** (template + params selected, not yet compiled)
4. **Compiled** (YAML produced, ready to preview)
5. **Approved** (user accepted)
6. **Deployed** (installed in HA)
7. **Monitoring** (outcomes tracked)
8. **Updated / Disabled / Deleted** (lifecycle changes)

### 3.2 UX behavior expectations
- “Create automation” should default to:
  - ask clarifying questions until confidence threshold met, OR
  - propose a best-guess plan with editable options.
- Provide an **English summary** always.
- Provide **View YAML** optionally.
- Always present “Approve / Modify / Cancel”.

---

## 4) API Contracts (No Code, Exact Payload Shapes)

> These endpoints can live under `ai-automation-service` (recommended) and be invoked by HA AI Agent UI.

### 4.1 Create/continue a conversation
**POST** `/agent/conversations`
- Creates a new conversation thread.

**POST** `/agent/conversations/{conversation_id}/messages`
- Adds a user message and returns agent response + next actions.

**Response must include:**
- `assistant_message` (human text)
- `conversation_state` (Draft/Clarifying/Planned/Compiled/...)
- `next_actions[]` (buttons or forms)
- `plan` (optional structured plan)
- `preview` (optional compiled preview)
- `errors` (optional)

---

### 4.2 Intent → Plan (LLM-facing)
**POST** `/automation/plan`
Input:
```json
{
  "conversation_id": "c_123",
  "user_text": "When I walk into the office, turn on the lights",
  "context": {
    "selected_device_ids": [],
    "selected_room": "office",
    "timezone": "America/Los_Angeles"
  }
}
```

Output (structured plan; never YAML):
```json
{
  "plan_id": "p_abc",
  "intent_type": "automation_request",
  "template_id": "room_entry_light_on",
  "template_version": 2,
  "parameters": {
    "room_type": "office",
    "brightness_pct": 100,
    "time_window": { "after": "08:00", "before": "18:00" }
  },
  "confidence": 0.92,
  "clarifications_needed": [],
  "safety_class": "low",
  "promotion_recommended": true,
  "explanation": "Office entry detected via presence; user wants lights on during work hours."
}
```

Notes:
- `clarifications_needed[]` is an array of question objects when required:
```json
{
  "key": "room_type",
  "question": "Which room should this apply to?",
  "options": ["office", "home_office", "guest_office"]
}
```

---

### 4.3 Validate plan (deterministic)
**POST** `/automation/validate`
Input:
```json
{
  "plan_id": "p_abc",
  "template_id": "room_entry_light_on",
  "template_version": 2,
  "parameters": { "...": "..." }
}
```

Output:
```json
{
  "valid": true,
  "validation_errors": [],
  "resolved_context": {
    "matched_room_id": "area.office",
    "presence_sensor_entity": "binary_sensor.office_presence",
    "lights_target": { "area_id": "office" }
  },
  "safety": {
    "allowed": true,
    "requires_confirmation": false,
    "reasons": []
  }
}
```

If invalid:
- return `valid=false` with actionable errors:
```json
{
  "valid": false,
  "validation_errors": [
    { "field": "room_type", "message": "No matching room found for 'office'." }
  ]
}
```

---

### 4.4 Compile YAML (deterministic)
**POST** `/automation/compile`
Input:
```json
{
  "plan_id": "p_abc",
  "template_id": "room_entry_light_on",
  "template_version": 2,
  "parameters": { "...": "..." },
  "resolved_context": { "...": "..." }
}
```

Output:
```json
{
  "compiled_id": "y_789",
  "yaml": "alias: ...\ntrigger: ...",
  "human_summary": "When presence is detected in Office during work hours, turn on Office lights to 100%.",
  "diff_summary": [
    "Trigger: Office presence -> on",
    "Condition: 08:00–18:00",
    "Action: Turn on Office area lights (100%)"
  ],
  "risk_notes": []
}
```

---

### 4.5 Approve + Deploy
**POST** `/automation/deploy`
Input:
```json
{
  "compiled_id": "y_789",
  "approval": {
    "approved": true,
    "approved_by": "user",
    "ui_source": "ha-agent"
  }
}
```

Output:
```json
{
  "deployment_id": "d_456",
  "ha_automation_id": "automation.office_entry_lights",
  "status": "deployed",
  "ha_link": "homeassistant://automation/automation.office_entry_lights",
  "version": 1
}
```

---

## 5) Template Library (Source of Truth)

### 5.1 Template requirements
Each template must define:
- `template_id` + `version`
- description and purpose
- required capabilities (device types, sensors)
- parameter schema (types, enums, bounds, defaults)
- safety class and forbidden targets
- compilation mapping (how to map params → HA trigger/condition/action shape)

### 5.2 Template structure (recommended schema)
Store templates in a local folder (e.g., `templates/`) as JSON/YAML *metadata*, not HA YAML.

### 5.3 Start with a small template set
Implement 10–20 “boring but high-value” templates first.

---

## 6) YAML Compiler (Deterministic)

### Responsibilities
- Accept validated plan + resolved context.
- Resolve device graph to HA entity IDs/area IDs.
- Emit minimal HA automation YAML.
- Never call LLM.

---

## 7) Deployment Manager (HA Integration)

### Deployment options
A) Create/update automations via HA APIs so they appear in HA UI (preferred).  
B) Write YAML into HA config + reload (fallback).

---

## 8) Automation Registry (SQLite)

Track:
- conversations, plans, compiled artifacts, deployments, feedback.

---

## 9) Promotion Logic (API vs Persisted Automation)

Promote to YAML only when:
- user requested automation OR
- repeated pattern + user approves.

---

## 10) Observability

- Debug view should show plan/validation/compile/deploy details.
- Use correlation IDs: conversation_id, plan_id, compiled_id, deployment_id.

---

## 11) Safety

Define low/medium/high safety classes and require explicit confirmation for high-risk automations.

---

## 12) Phased Delivery

1) Minimal flow with 1–2 templates end-to-end.  
2) Expand templates, validation.  
3) Add pattern-driven proactive suggestions.  
4) Add lifecycle reconciliation with HA UI edits.  
5) Add cloud capability packs.

---

## 13) Acceptance Tests

- Determinism: same plan → same YAML.
- HA resilience: automation still runs when HomeIQ down.
- Safety: locks/alarms require confirmation and defaults to suggestion.
