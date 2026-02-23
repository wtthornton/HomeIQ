---
epic: deploy-pipeline-root-cause-fixes
priority: high
status: implemented
estimated_duration: 1-2 weeks
risk_level: medium
source: End-to-end deploy testing (2026-02-12)
---

# Epic: Deploy Pipeline Root Cause Fixes

**Status:** Implemented
**Priority:** High
**Duration:** 1-2 weeks
**Risk Level:** Medium
**Predecessor:** Evaluation sweep fixes (R1-R6), Story 5.4 data-api integration

## Context

End-to-end deploy testing (2026-02-12) revealed that while the pipeline
can produce valid YAML and score 95-99/100 in preview mode, actual
deployment to Home Assistant fails for 3 of 5 test prompts. The
immediate blockers (auth, missing `/api/areas` endpoint, FastAPI
decorator bug) were patched, and a `_strip_unresolved()` safety net was
added to remove `{{placeholders}}` that HA rejects. But the safety net
masks deeper issues:

| Prompt | Pipeline | Deploy | Root Cause |
|--------|----------|--------|------------|
| turn on office lights at 7pm | 99/100 | **PASS** | `time_based_light_on` resolves cleanly |
| turn on the office lights | 97/100 | **FAIL** | `room_entry_light_on` needs presence sensor; none in office area |
| turn off all lights at midnight | 97/100 | **FAIL** | `scheduled_task` uses wrong HA trigger type (`time_pattern` vs `time`) |
| make it look like a party | 97/100 | untested | Likely FAIL; unresolved scene entity |
| when I leave home turn off everything | 97/100 | untested | Likely FAIL; unresolved device_tracker entity |

The `_strip_unresolved()` and `_remove_incomplete_entries()` methods
silently remove critical YAML fields, producing triggers with no
`entity_id` and conditions with no time bounds. HA rightly rejects these.

## Root Causes

### RC1. LLM returns `null` for optional parameters

The plan endpoint LLM prompt says "fill in parameters based on user text
and context" but gives no guidance on what to do when context is missing.
Result: `target_entity: null`, `target_area: null`, `time_window: null`.

**File:** `domains/automation-core/ai-automation-service-new/src/services/intent_planner.py` (~line 96)

### RC2. Templates lack defaults for optional parameters

Template parameter schemas declare `required: false` but provide no
`default` values. When the LLM returns null and no default exists, the
placeholder stays as `{{param_name}}`.

**Files:** `domains/automation-core/ai-automation-service-new/src/templates/templates/*.json`

### RC3. Template selection ignores available hardware

The LLM picks `room_entry_light_on` for "turn on the office lights"
because the keywords match. It has no awareness that the office area
has zero presence/motion sensors, making the template impossible to
compile into valid YAML.

**File:** `domains/automation-core/ai-automation-service-new/src/services/intent_planner.py`

### RC4. `scheduled_task` template uses wrong trigger platform

The template uses `platform: time_pattern` with `minutes: {{schedule_pattern}}`,
but `time_pattern` expects integer values for hours/minutes/seconds, not
a time string like `"00:00:00"`. For fixed-time schedules (midnight, 7am),
the correct HA platform is `time` with `at: "HH:MM:SS"`.

**File:** `domains/automation-core/ai-automation-service-new/src/templates/templates/scheduled_task.json`

### RC5. No automation update capability

Every deploy generates a new random `automation_id`
(`automation.{uuid4()[:8]}`). There is no way to say "update the
existing office-lights automation from 7pm to 9pm". The deploy endpoint
always creates, never updates.

**File:** `domains/automation-core/ai-automation-service-new/src/api/deployment_router.py` (~line 234)

### RC6. Placeholder stripping is silent and indiscriminate

`_strip_unresolved()` treats all unresolved placeholders equally. A
missing optional `color_temp` is stripped the same as a missing required
`entity_id`, producing structurally invalid YAML with no warning.

**File:** `domains/automation-core/ai-automation-service-new/src/services/yaml_compiler.py`

---

## Stories

### Story 1: Template Parameter Defaults & Validation (RC2 + RC4)

**Goal:** Every template compiles into valid HA YAML even when the LLM
returns null for optional params.

#### 1.1 Add defaults to all template parameter schemas

For each template in `templates/templates/*.json`, add sensible `default`
values for optional parameters:

| Template | Parameter | Default |
|----------|-----------|---------|
| `room_entry_light_on` | `time_window` | `{"after": "06:00:00", "before": "23:00:00"}` |
| `room_entry_light_on` | `brightness_pct` | `100` |
| `scheduled_task` | `target_entity` | `"all"` |
| `scheduled_task` | `target_area` | (omit from YAML if null) |
| `scheduled_task` | `action_data` | `{}` |
| `scene_activation` | `trigger_state` | `"on"` |
| `state_based_automation` | `action_data` | `{}` |
| `time_based_light_on` | `color_temp` | (omit from YAML if null) |
| `temperature_control` | `hvac_mode` | `"heat"` |

**Files:** `domains/automation-core/ai-automation-service-new/src/templates/templates/*.json`

#### 1.2 Fix `scheduled_task` trigger platform

Split the template into two trigger variants based on the
`schedule_pattern` value:

- If pattern is a time string (e.g., `"00:00:00"`, `"07:00"`) ->
  use `platform: time` with `at: "{{schedule_pattern}}"`
- If pattern contains `/` (e.g., `"/15"`) ->
  use `platform: time_pattern` with `minutes: "{{schedule_pattern}}"`

**Implementation:** Either:
- (A) Split into two templates: `scheduled_task_at` and
  `scheduled_task_interval`
- (B) Add compile-time logic in `yaml_compiler.py` to detect the
  pattern and switch platform

Option A is simpler and keeps templates declarative.

**Files:**
- `domains/automation-core/ai-automation-service-new/src/templates/templates/scheduled_task.json` (rename to `scheduled_task_interval.json`)
- New: `domains/automation-core/ai-automation-service-new/src/templates/templates/scheduled_task_at.json`
- `domains/automation-core/ai-automation-service-new/src/services/intent_planner.py` (update template list)

#### 1.3 Apply defaults during validation

In `template_validator.py`, after parameter schema validation, apply
defaults from the schema before resolving context:

```python
# In validate_plan(), after Step 2:
for param_name, param_schema in template.parameter_schema.items():
    if parameters.get(param_name) is None and param_schema.default is not None:
        parameters[param_name] = param_schema.default
```

This already exists at line 105-107 but only runs during type
validation. Move it to run unconditionally for all params before
`_resolve_context()`.

**Files:** `domains/automation-core/ai-automation-service-new/src/services/template_validator.py`

**Acceptance Criteria:**
- [ ] All templates have defaults for optional params
- [ ] `scheduled_task` "at midnight" produces `platform: time, at: "00:00:00"`
- [ ] `room_entry_light_on` compiles with default time_window when LLM returns null
- [ ] Existing tests still pass

---

### Story 2: Hardware-Aware Template Selection (RC3)

**Goal:** The plan endpoint considers available hardware when selecting a
template, avoiding templates that require entities that don't exist.

#### 2.1 Pass available entity summary to LLM prompt

Before calling the LLM, query data-api for a summary of available
entities per area. Include this context in the system prompt so the LLM
can make informed template choices:

```
Available entities in your HA instance:
- office: scene.office_work, scene.office_work_lights (no motion sensors)
- laundry_room: (entities...)

When selecting a template, ensure the area has the required sensors.
If the area lacks motion/presence sensors, prefer time_based_light_on
or scene_activation over room_entry_light_on.
```

**Implementation:**
- In `intent_planner.py`, call `data_api_client.fetch_areas()` +
  `fetch_entities_in_area()` before building the LLM prompt
- Build a compact entity summary (domain counts per area)
- Append to system prompt

**Files:**
- `domains/automation-core/ai-automation-service-new/src/services/intent_planner.py`
- `domains/automation-core/ai-automation-service-new/src/clients/data_api_client.py`
  (may need a `fetch_entity_summary()` method for efficiency)

#### 2.2 Add `required_entities` to template schema

Extend the template schema to explicitly declare what entity types
a template requires in the target area:

```json
{
  "required_entities": {
    "binary_sensor.motion": "required",
    "light": "optional"
  }
}
```

The planner can then filter templates before passing them to the LLM,
removing templates that can't possibly work.

**Files:**
- `domains/automation-core/ai-automation-service-new/src/templates/template_schema.py`
- `domains/automation-core/ai-automation-service-new/src/templates/templates/*.json`
- `domains/automation-core/ai-automation-service-new/src/services/intent_planner.py`

**Acceptance Criteria:**
- [ ] "turn on office lights" picks `time_based_light_on` (not
  `room_entry_light_on`) because office has no motion sensor
- [ ] LLM prompt includes entity summary
- [ ] Templates with missing required entities are filtered out

---

### Story 3: LLM Plan Prompt Improvements (RC1)

**Goal:** The LLM returns complete, non-null parameter values by
following explicit instructions for optional params.

#### 3.1 Update system prompt with parameter guidelines

Add explicit rules to the plan prompt in `intent_planner.py`:

```
Parameter Rules:
- ALWAYS fill in ALL parameters, both required and optional
- For target_entity: use "all" if the user says "all lights" / "everything"
- For target_area: use the area name from the user's request (e.g., "office")
- For time_window: default to {"after": "06:00:00", "before": "23:00:00"} if not specified
- For action_data: use {} if no extra data needed
- NEVER return null for a parameter — use the default value instead
- If you don't have enough information, add a clarification question
```

#### 3.2 Add few-shot examples to prompt

Include 2-3 worked examples showing correct parameter filling:

```
Example 1:
User: "turn off all lights at midnight"
Plan: {
  "template_id": "scheduled_task_at",
  "parameters": {
    "schedule_pattern": "00:00:00",
    "action_service": "light.turn_off",
    "target_entity": "all"
  }
}
```

**Files:** `domains/automation-core/ai-automation-service-new/src/services/intent_planner.py`

**Acceptance Criteria:**
- [ ] LLM returns non-null values for all params
- [ ] "turn off all lights" returns `target_entity: "all"`
- [ ] Clarification is requested when info is genuinely missing

---

### Story 4: Smarter Placeholder Handling (RC6)

**Goal:** Replace silent stripping with an informed compilation strategy
that distinguishes required vs optional fields.

#### 4.1 Classify placeholders as required vs optional

In `yaml_compiler.py`, instead of blindly stripping all `{{...}}`
placeholders, check whether the placeholder maps to a required or
optional parameter in the template schema:

```python
def _handle_unresolved(self, key, placeholder, template):
    param_name = placeholder.strip("{} ")
    schema = template.parameter_schema.get(param_name)

    if schema and not schema.required:
        # Optional: safe to strip
        logger.debug(f"Stripping optional {key}={placeholder}")
        return None
    else:
        # Required: this is a compilation error
        logger.error(f"REQUIRED placeholder unresolved: {key}={placeholder}")
        raise CompilationError(
            f"Cannot compile: required parameter '{param_name}' is unresolved"
        )
```

#### 4.2 Return compilation errors to the caller

When a required placeholder can't be resolved, the compile endpoint
should return a 422 with details instead of producing invalid YAML:

```json
{
  "error": "compilation_incomplete",
  "unresolved_required": ["presence_sensor_entity"],
  "unresolved_optional": ["color_temp"],
  "suggestion": "The office area has no motion sensors. Consider using time_based_light_on template instead."
}
```

#### 4.3 Keep `_strip_unresolved` as safety net for optional-only

The existing strip logic stays but only runs on confirmed-optional
placeholders. Required-unresolved placeholders fail fast.

**Files:**
- `domains/automation-core/ai-automation-service-new/src/services/yaml_compiler.py`
- `domains/automation-core/ai-automation-service-new/src/api/automation_compile_router.py`
- `domains/automation-core/ai-automation-service-new/src/templates/template_schema.py`
  (ensure `required` field is accessible)

**Acceptance Criteria:**
- [ ] Missing required placeholder -> 422 error with clear message
- [ ] Missing optional placeholder -> stripped silently (existing behavior)
- [ ] No structurally invalid YAML reaches the deploy endpoint

---

### Story 5: Automation Update Flow (RC5)

**Goal:** Enable updating an existing automation's parameters without
creating a duplicate.

#### 5.1 Track deployed automations by alias + area

Add a lookup mechanism to find existing HomeIQ-managed automations:

```python
# In deployment_service.py:
async def find_existing_automation(
    self, template_id: str, area_id: str
) -> str | None:
    """Find existing automation matching template + area."""
    query = select(DeployedAutomation).where(
        DeployedAutomation.template_id == template_id,
        DeployedAutomation.area_id == area_id,
        DeployedAutomation.status == "deployed"
    )
    result = await self.db.execute(query)
    existing = result.scalar_one_or_none()
    return existing.ha_automation_id if existing else None
```

#### 5.2 Add `ha_automation_id` field to deploy request

Allow the caller to specify an existing `ha_automation_id` to update:

```python
class DeployCompiledRequest(BaseModel):
    compiled_id: str
    approved_by: str = "system"
    ha_automation_id: str | None = None  # If set, update instead of create
    # ...
```

When `ha_automation_id` is provided, POST to
`/api/config/automation/config/{ha_automation_id}` (same endpoint, HA
overwrites). When null, generate a new UUID as today.

#### 5.3 Add version tracking for updates

When updating an existing automation:
1. Save the current YAML as a version before overwriting
2. Increment the version counter
3. Record the diff between old and new YAML

**Files:**
- `domains/automation-core/ai-automation-service-new/src/api/deployment_router.py`
- `domains/automation-core/ai-automation-service-new/src/services/deployment_service.py`
- `domains/automation-core/ai-automation-service-new/src/models/` (DeployedAutomation
  model may need `template_id`, `area_id` columns)

#### 5.4 Wire into test harness

Add `--update` flag to `test_ask_ai_pipeline.py` that:
1. Looks up existing automation by template + area
2. Passes `ha_automation_id` to the deploy endpoint
3. Verifies HA has the updated config

**Files:** `tests/integration/test_ask_ai_pipeline.py`

**Acceptance Criteria:**
- [ ] Deploy "office lights at 7pm" -> creates `automation.abc123`
- [ ] Deploy "office lights at 9pm" -> updates `automation.abc123` (same ID)
- [ ] Version history shows both 7pm and 9pm configs
- [ ] Rollback from 9pm to 7pm works via existing rollback endpoint

---

## Implementation Order

| Priority | Story | Risk | Rationale |
|----------|-------|------|-----------|
| **P0** | Story 1 (Templates + Defaults) | Low | Highest impact, simplest change. Fixes 2 of 3 failing prompts. |
| **P0** | Story 3 (LLM Prompt) | Low | Complementary to Story 1. Together they eliminate most null params. |
| **P1** | Story 4 (Smart Placeholders) | Medium | Prevents invalid YAML from reaching HA. Safety improvement. |
| **P1** | Story 2 (Hardware-Aware Selection) | Medium | Requires data-api round-trip in plan step. Fixes the hardest cases. |
| **P2** | Story 5 (Update Flow) | Medium | New capability, not a fix. Important for UX but not blocking deploy. |

## Testing Strategy

After implementing Stories 1-4, re-run the 5-prompt deploy sweep:

```bash
for prompt in \
  "turn on the office lights" \
  "turn off all lights at midnight" \
  "turn on the office lights at 7pm" \
  "make it look like a party in the office" \
  "when I leave home turn off everything"; do
    python tests/integration/test_ask_ai_pipeline.py "$prompt" --deploy -v
done
```

**Target:** All 5 prompts deploy successfully (currently 1/5).

## Files Modified (Summary)

| File | Stories |
|------|---------|
| `templates/templates/*.json` | 1 |
| `services/intent_planner.py` | 2, 3 |
| `services/template_validator.py` | 1 |
| `services/yaml_compiler.py` | 4 |
| `api/deployment_router.py` | 5 |
| `services/deployment_service.py` | 5 |
| `clients/data_api_client.py` | 2 |
| `templates/template_schema.py` | 2, 4 |
| `tests/integration/test_ask_ai_pipeline.py` | 5 |
