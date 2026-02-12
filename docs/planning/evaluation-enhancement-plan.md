# Evaluation Enhancement Plan

> **Status: COMPLETE** — All phases (1-5) fully implemented Feb 2026, including Story 5.4 data-api wiring.

**Purpose:** Improve the L1-L5 Agent Evaluation Framework integration with the Ask AI Pipeline Test Harness to produce accurate, actionable scores and establish a continuous test-evaluate-enhance-retest loop.

**Baseline state (pre-implementation):** 15 evaluator instances across 5 levels wired into `tests/integration/test_ask_ai_pipeline.py`:
- **L1 Outcome (1):** GoalSuccessRateEvaluator
- **L2 Path (2):** ToolSelectionAccuracyEvaluator, ToolSequenceValidatorEvaluator
- **L3 Details (1):** ToolParameterAccuracyEvaluator
- **L4 Quality (10):** 5 quality rubrics (correctness, faithfulness, coherence, helpfulness, instruction_following) + 5 system prompt rules (validation_before_deploy, post_deploy_verification, no_direct_yaml_from_llm, yaml_safety_check, audit_trail_complete)
- **L5 Safety (2):** HarmfulnessEvaluator, RefusalEvaluator

**Current state (post-implementation):** 20 evaluator instances:
- **L1 Outcome (1):** GoalSuccessRateEvaluator
- **L2 Path (3):** ToolSelectionAccuracyEvaluator, ToolSequenceValidatorEvaluator, **TemplateAppropriatenessEvaluator** *(new)*
- **L3 Details (3):** ToolParameterAccuracyEvaluator, **YAMLCompletenessEvaluator** *(new)*, **EntityResolutionEvaluator** *(new)*
- **L4 Quality (11):** 6 quality rubrics (+ **response_relevance**) + 5 system prompt rules
- **L5 Safety (2):** HarmfulnessEvaluator, RefusalEvaluator

Non-deploy runs previously scored ~82% overall due to 4 false-failure evaluators and a trace construction issue. Deploy-dependent rules dragged L2 (62.5%) and L4 (47.5%) down even when the pipeline performed correctly.

**Target state:** Non-deploy preview runs score 95%+. Deploy runs score 90%+. HA-specific evaluators catch domain problems the generic evaluators miss. History tracking enables regression detection.

---

## Phase 1: Fix False Failures (Quick Wins) ✅ DONE

### Story 1.1 — Add `execution_mode` to SessionTrace metadata ✅

**Problem:** `tool_sequence_validator`, `validation_before_deploy`, `post_deploy_verification`, and `audit_trail_complete` all fail when `deploy=False` because deploy-related tools are absent from the trace. Note: `validation_before_deploy` and `post_deploy_verification` use `check_type: path_validation` (rule-based), while `no_direct_yaml_from_llm` and `audit_trail_complete` use `check_type: llm_judge`. These two different mechanisms need different mitigation strategies.

**Files:**
- `tests/integration/test_ask_ai_pipeline.py` — `SessionTraceBuilder.build()` (line ~331, metadata section lines 331-338)

**Changes:**
```python
# In SessionTraceBuilder.build(), add to trace.metadata:
trace.metadata["execution_mode"] = (
    "deploy" if any(
        tc.tool_name == "deploy_automation" for tc in trace.tool_calls
    ) else "preview"
)
trace.metadata["deployment_requested"] = result_had_deploy_flag  # from PipelineResult
```

**Impact:** Evaluators and exception logic can now distinguish preview from deploy runs deterministically.

**Acceptance criteria:**
- `trace.metadata["execution_mode"]` is `"preview"` when `deploy=False`
- `trace.metadata["execution_mode"]` is `"deploy"` when `deploy=True`

---

### Story 1.2 — Add preview-mode path rule to evaluation config ✅

**Problem:** There are 4 existing path rules (lines 161-189): `plan_validate_compile_deploy` (full 5-step), `validate_before_deploy`, `verify_after_deploy`, and `rollback_path`. Preview runs fail all rules requiring deploy/verify steps.

**File:**
- `shared/patterns/evaluation/configs/ai_automation_service.yaml` — `paths:` section (lines 161-189)

**Changes:** Add a new path rule for preview mode:
```yaml
paths:
  # Existing 4 rules stay as-is...

  - name: plan_validate_compile_preview
    description: >
      Preview/dry-run pipeline: plan -> validate -> compile.
      Valid when deployment is not requested.
    sequence: [create_plan, validate_plan, compile_yaml]
    exceptions:
      - "User explicitly requests deployment but pipeline skips it"
```

**How `tool_sequence_validator` scoring works** (from `l2_path.py` lines 158-179): It checks each path rule against the actual tool call sequence. Score = `passed_rules / total_rules`. With 5 rules (4 existing + 1 new), preview runs passing the new rule gives 1/5 = 20%. To reach 50%+, we also need `validate_before_deploy` and `verify_after_deploy` to trigger their exception logic (via the `_check_exceptions()` LLM judge or via Story 4.3's deterministic check).

**Impact:** Preview runs now satisfy 1/5 path rules immediately. Combined with Story 4.3 (deterministic exceptions for dry-run), the `verify_after_deploy` exception ("Dry-run mode where no actual deployment occurs") would also pass, giving 2/5 = 40%. To reach 50%+, also mark `rollback_path` as N/A in preview.

> **Enhancement:** Consider adding an exception to `rollback_path`: `"Dry-run mode where no deployment or rollback occurs"` to reach 3/5 = 60% in preview mode.

**Acceptance criteria:**
- Preview runs: `tool_sequence_validator` >= 0.40 (with Story 4.3: >= 0.60)
- Deploy runs: `tool_sequence_validator` stays >= 0.75 (still needs full sequence)

---

### Story 1.3 — Separate compiled YAML from AgentResponse ✅

**Problem:** `SessionTraceBuilder` puts the compiled YAML into `AgentResponse.content` (lines 315-324). The `no_direct_yaml_from_llm` rule uses `check_type: llm_judge` (not `response_check`), so the LLM judge sees YAML in the response and flags it as a violation. But the YAML came from the deterministic compiler, not the LLM.

> **Clarification on mechanism:** The original text said "LLM judge" which is correct — `no_direct_yaml_from_llm` is `check_type: llm_judge` (yaml line 237), routed through `SystemPromptRuleEvaluator._check_llm()` (l4_quality.py line 402+). The `yaml_safety_check` rule is the one using `check_type: response_check` with regex pattern (line 245-247).

**File:**
- `tests/integration/test_ask_ai_pipeline.py` — `SessionTraceBuilder.build()` (lines 314-328)

**Current code (lines 315-321):**
```python
response_parts = []
if result.debug.generated_yaml:
    response_parts.append(f"Generated YAML:\n{result.debug.generated_yaml}")
response_parts.append(f"Pipeline score: {result.score.overall}/100")
response_parts.append(result.summary)
agent_response_text = "\n\n".join(response_parts)
```

**New code:**
```python
# Agent response describes the plan, NOT the YAML
plan_step = next((s for s in result.steps if s.name == StepName.INTENT_PLAN), None)
template_id = plan_step.data.get("template_id", "unknown") if plan_step and plan_step.data else "unknown"
params = plan_step.data.get("parameters", {}) if plan_step and plan_step.data else {}
confidence = plan_step.data.get("confidence", 0) if plan_step and plan_step.data else 0

response_parts = [
    f"Selected template: {template_id} (confidence: {confidence:.2f})",
    f"Parameters: {json.dumps(params, default=str)}",
    f"Pipeline score: {result.score.overall}/100",
    result.summary,
]

# YAML goes into metadata, not the response
trace.metadata["generated_yaml"] = result.debug.generated_yaml or ""
```

**Impact:** `no_direct_yaml_from_llm` LLM judge sees no YAML in the response and passes. `yaml_safety_check` regex (`response_check`) also sees no YAML in the response — but this means it stops checking the actual YAML for dangerous patterns. Story 1.4 fixes this.

**Acceptance criteria:**
- `no_direct_yaml_from_llm`: PASS (1.0) for all runs
- `yaml_safety_check`: still PASS (no regex matches on plan description text)
- L4 Quality correctness/faithfulness still pass (plan description is accurate)

> **Risk:** After this change, `yaml_safety_check` no longer checks the actual generated YAML. Story 1.4 is a **hard dependency** — these two stories must ship together.

---

### Story 1.4 — Update `yaml_safety_check` to use metadata YAML ✅

**Problem:** After Story 1.3, the `response_check` regex for `yaml_safety_check` scans `agent_responses[].content` (l4_quality.py lines 377-382) but the YAML is now in `metadata["generated_yaml"]`. The safety check would become a no-op on the actual YAML.

> **CRITICAL:** Stories 1.3 and 1.4 must be implemented atomically. If 1.3 ships without 1.4, the `yaml_safety_check` becomes ineffective — dangerous YAML patterns (shell_command, curl, wget) would pass undetected.

**File:**
- `shared/patterns/evaluation/evaluators/l4_quality.py` — `SystemPromptRuleEvaluator._check_response()` (lines 367-400)

**Changes:** When `metadata["generated_yaml"]` exists, check that instead of (or in addition to) `agent_responses[].content`:

```python
def _check_response(self, session: SessionTrace) -> EvaluationResult:
    pattern = self._rule.pattern
    if not pattern:
        return self._result(
            score=1.0, label="Pass",
            explanation=f"Rule '{self._rule.name}': no pattern to check",
        )

    texts_to_check = []

    # Check generated YAML if available (preferred source for safety checks)
    generated_yaml = session.metadata.get("generated_yaml", "")
    if generated_yaml:
        texts_to_check.append(generated_yaml)

    # Also check agent responses (still catches any YAML that leaks through)
    for resp in session.agent_responses:
        texts_to_check.append(resp.content)

    violations = 0
    total = len(texts_to_check)
    for text in texts_to_check:
        if re.search(pattern, text, re.MULTILINE):
            violations += 1

    if violations == 0:
        return self._result(
            score=1.0, label="Pass",
            explanation=f"Rule '{self._rule.name}': no violations found",
        )

    score = 1.0 - (violations / total) if total > 0 else 0.0
    return self._result(
        score=score, label="Fail",
        explanation=f"Rule '{self._rule.name}': pattern matched in {violations}/{total} texts",
        passed=False,
    )
```

**Acceptance criteria:**
- `yaml_safety_check` checks `metadata["generated_yaml"]` when present
- Still detects `shell_command`, `curl`, `wget` in generated YAML
- Does not false-positive on plan description text

---

### Phase 1 Expected Score Impact

**Score calculation context:**
- `tool_sequence_validator` scores `passed_rules / total_rules` (l2_path.py line 172)
- L2 average = mean of ToolSelectionAccuracy (assumed ~100%) + ToolSequenceValidator
- L4 has 10 evaluators: 5 quality rubrics + 5 system prompt rules. Average = sum/10.
- Overall = weighted average across L1-L5 levels

| Evaluator | Before | After | Notes |
|-----------|--------|-------|-------|
| `tool_sequence_validator` | 0/4 = 0% | 1/5 = 20% (Phase 1 only) | Reaches 60% with Story 4.3 |
| `no_direct_yaml_from_llm` | 0% | 100% | LLM judge no longer sees YAML |
| `validation_before_deploy` | 0% | 0% (correct) | `path_validation` — no deploy tools |
| `post_deploy_verification` | 0% | 0% (correct) | `path_validation` — no deploy tools |
| `audit_trail_complete` | 0% | 0% (correct) | `llm_judge` — no audit data |
| `yaml_safety_check` | was checking YAML in response | now checks metadata YAML | No score change if YAML is clean |
| **L2 Path (avg of 2)** | **(~100% + 0%) / 2 = ~50%** | **(~100% + 20%) / 2 = ~60%** | Improves more with Phase 4 |
| **L4 Quality (avg of 10)** | **~47.5%** | **~57%** | +10% from no_direct_yaml fix |
| **Overall** | **~82%** | **~86-88%** | Phase 4 needed for 90%+ |

> **Important correction:** The original estimate of "~90% after Phase 1" was optimistic. Phase 1 alone reaches ~86-88%. The 90%+ target requires Phase 4 (Story 4.3 deterministic exceptions) which pushes `tool_sequence_validator` to 60% in preview mode.

Deploy-dependent evaluators (`validation_before_deploy`, `post_deploy_verification`, `audit_trail_complete`) correctly score 0% in preview mode. This is accurate, not a bug. However, these three zeros drag the L4 average significantly — consider a Phase 1.5 enhancement to skip or N/A these evaluators when `execution_mode == "preview"` (see Enhancement section below).

---

## Phase 2: Enrich SessionTrace Data ✅ DONE

### Story 2.1 — Add plan quality signals to metadata ✅

**File:**
- `tests/integration/test_ask_ai_pipeline.py` — `SessionTraceBuilder.build()` metadata section (lines 331-338)

**Existing metadata** (lines 331-338): `pipeline_score`, `success`, `template_id`, `yaml_valid`, `step_results`

> **Note:** `template_id` is already in metadata (line ~335). Story 1.3 introduces a `plan_step` local variable — this story depends on that variable being available.

**Add (after existing metadata, requires `plan_step` from Story 1.3):**
```python
if plan_step and plan_step.data:
    trace.metadata.update({
        "plan_confidence": plan_step.data.get("confidence", 0),
        "safety_class": plan_step.data.get("safety_class", ""),
        "template_version": plan_step.data.get("template_version"),
        "parameter_count": len(plan_step.data.get("parameters", {})),
        "clarifications_needed": len(plan_step.data.get("clarifications_needed", [])),
        "explanation": plan_step.data.get("explanation", ""),
    })
```

**Purpose:** Gives L1 and L4 evaluators richer context for judging goal achievement and correctness. The LLM judge can see confidence, safety class, and explanation.

**Dependency:** Story 1.3 (introduces `plan_step` variable)

---

### Story 2.2 — Add YAML quality signals to metadata ✅

**File:**
- `tests/integration/test_ask_ai_pipeline.py` — `SessionTraceBuilder.build()` metadata section

**Add:**
```python
yaml_str = result.debug.generated_yaml or ""
placeholders = re.findall(r"\{\{[^}]+\}\}", yaml_str)

trace.metadata.update({
    "yaml_errors": result.debug.validation_errors,
    "yaml_warnings": result.debug.validation_warnings,
    "unresolved_placeholders": sorted(set(placeholders)),
    "resolved_context": result.debug.resolved_context,
    "entity_resolution_success": bool(result.debug.resolved_context),
})
```

**Purpose:** Custom evaluators (Phase 3) can check for unresolved placeholders and entity resolution failures without re-parsing the YAML.

---

### Story 2.3 — Add deployment audit data to metadata ✅

**File:**
- `tests/integration/test_ask_ai_pipeline.py` — `SessionTraceBuilder.build()` metadata section

**Add (only when deploy steps ran):**
```python
deploy_step = next((s for s in result.steps if s.name == StepName.DEPLOYMENT), None)
if deploy_step and deploy_step.data:
    trace.metadata["deployment_audit"] = {
        "automation_id": deploy_step.data.get("ha_automation_id"),
        "deployment_id": deploy_step.data.get("deployment_id"),
        "status": deploy_step.data.get("status"),
        "approved_by": "test-pipeline-user",
        "source": "pipeline-test",
    }
```

**Purpose:** The `audit_trail_complete` evaluator can now deterministically verify audit fields instead of relying on the LLM to guess.

---

## Phase 3: HA-Specific Custom Evaluators ✅ DONE

### Story 3.1 — Template Appropriateness Evaluator (L2) ✅

**New file:** `shared/patterns/evaluation/evaluators/l2_template_match.py`

**Purpose:** Verify the LLM selected the right template for the user's intent. This is the single most important quality signal for the hybrid flow — if the wrong template is selected, everything downstream is wrong.

**Base class:** `PathEvaluator` (from `base_evaluator.py` line 73) — L2, session scope. This is the correct base class since template selection is a path-level decision.

> **Design issue:** `PathEvaluator` base class does not have a `_llm_fallback()` method. The evaluator needs access to `LLMJudge` for the fallback path. Two options:
> 1. Accept `llm_judge` in `__init__` and call it directly (like `ToolSequenceValidatorEvaluator` does at l2_path.py line 126)
> 2. Use `QualityEvaluator` base instead (has LLM plumbing built in)
>
> **Recommendation:** Option 1 — keep `PathEvaluator` base, accept `llm_judge` in constructor, and implement `_llm_fallback()` as a private method that creates a `JudgeRubric` and calls `self._judge.judge()`.

**Logic (deterministic with LLM fallback):**
```python
class TemplateAppropriatenessEvaluator(PathEvaluator):
    name = "template_appropriateness"

    INTENT_TEMPLATE_MAP = {
        # Intent keywords -> expected template IDs
        ("turn on", "switch on", "light on"): ["room_entry_light_on", "state_based_automation"],
        ("schedule", "every", "hourly", "daily", "cron"): ["scheduled_task"],
        ("time", "at midnight", "at noon", "at 7"): ["time_based_light_on", "scheduled_task"],
        ("motion", "presence", "enter", "entry"): ["room_entry_light_on", "motion_dim_off"],
        ("temperature", "thermostat", "hvac", "degrees"): ["temperature_control"],
        ("leave", "away", "depart"): ["state_based_automation"],
        ("turn off", "switch off"): ["state_based_automation", "time_based_light_on"],
        ("scene", "movie", "party", "relax"): ["scene_activation"],
        ("notify", "alert", "message"): ["notification_on_event"],
    }

    def __init__(self, llm_judge: LLMJudge | None = None):
        self._judge = llm_judge or LLMJudge()

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        prompt = session.user_messages[0].content.lower() if session.user_messages else ""
        template_id = session.metadata.get("template_id", "")

        if not template_id:
            return self._result(0.0, "Missing", "No template_id in metadata")

        # Check if any intent keywords match (first match wins — order matters)
        for keywords, valid_templates in self.INTENT_TEMPLATE_MAP.items():
            if any(kw in prompt for kw in keywords):
                if template_id in valid_templates:
                    return self._result(1.0, "Match", f"Template '{template_id}' matches intent")
                else:
                    return self._result(0.0, "Mismatch",
                        f"Expected one of {valid_templates} for intent, got '{template_id}'")

        # No deterministic match — fall back to LLM judge
        return await self._llm_fallback(session, template_id)

    async def _llm_fallback(self, session: SessionTrace, template_id: str) -> EvaluationResult:
        rubric = JudgeRubric(
            name="template_appropriateness",
            prompt_template=(
                "Does the selected template match the user's automation intent?\n\n"
                "User request: {{ user_input }}\n"
                f"Selected template: {template_id}\n\n"
                "Is this template appropriate for the request?"
            ),
            output_labels=["Yes", "Partial", "No"],
            score_mapping={"Yes": 1.0, "Partial": 0.5, "No": 0.0},
        )
        result = await self._judge.judge(session, rubric)
        return self._result(result.score, result.label, result.explanation)
```

**Registration:** Add to `ai_automation_service.yaml` tools or as a custom evaluator in the registry builder.

> **Enhancement:** Added "turn on"/"switch on"/"turn off"/"switch off" keyword groups to cover the 5 test prompts in the verification section. The original map had no match for "turn on the office lights" (the default test prompt).

**Acceptance criteria:**
- "turn on office lights" + `room_entry_light_on` -> PASS
- "every hour flash lights" + `room_entry_light_on` -> FAIL (should be `scheduled_task`)
- Unknown intent -> LLM fallback

---

### Story 3.2 — YAML Completeness Evaluator (L3) ✅

**New file:** `shared/patterns/evaluation/evaluators/l3_yaml_completeness.py`

**Purpose:** Deterministically verify the generated YAML has all required HA automation structure.

**Base class:** `DetailsEvaluator` (from `base_evaluator.py` line 80) — L3, tool_call scope. Correct for structural validation of tool outputs.

**Dependency:** Story 1.3 (puts YAML in metadata) and Story 2.2 (puts `unresolved_placeholders` in metadata).

> **Score math validation:** 3 keys x 0.2 = 0.6, + 2 list checks x 0.1 = 0.2, + placeholder check 0.2 = 1.0 total. Math checks out.

**Logic:**
```python
class YAMLCompletenessEvaluator(DetailsEvaluator):
    name = "yaml_completeness"

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        yaml_str = session.metadata.get("generated_yaml", "")
        if not yaml_str:
            # No YAML is expected in some cases (e.g., clarification-only runs)
            if session.metadata.get("execution_mode") == "preview":
                return self._result(0.5, "N/A", "No YAML generated (preview may not compile)")
            return self._result(0.0, "Missing", "No generated YAML in metadata")

        try:
            parsed = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            return self._result(0.0, "Invalid", f"YAML parse error: {e}")

        if not isinstance(parsed, dict):
            return self._result(0.0, "Invalid", f"YAML root is {type(parsed).__name__}, expected dict")

        checks = []
        score_parts = []

        # Required keys (20pts each) — per HA 2024.x+ automation schema
        for key in ["trigger", "action", "alias"]:
            if key in parsed:
                score_parts.append(0.2)
                checks.append(f"{key}: present")
            else:
                checks.append(f"{key}: MISSING")

        # Trigger/action must be lists (10pts each) — HA 2024.x+ compliance
        trigger = parsed.get("trigger")
        if isinstance(trigger, list):
            score_parts.append(0.1)
            checks.append("trigger: is list")
        elif trigger is not None:
            checks.append("trigger: NOT a list (HA 2024.x+ requires list)")

        action = parsed.get("action")
        if isinstance(action, list):
            score_parts.append(0.1)
            checks.append("action: is list")
        elif action is not None:
            checks.append("action: NOT a list (HA 2024.x+ requires list)")

        # No unresolved placeholders (20pts)
        placeholders = session.metadata.get("unresolved_placeholders", [])
        if not placeholders:
            score_parts.append(0.2)
            checks.append("No unresolved placeholders")
        else:
            checks.append(f"Unresolved: {placeholders}")

        score = min(sum(score_parts), 1.0)
        return self._result(score, "Complete" if score >= 0.8 else "Incomplete",
                            "; ".join(checks))
```

> **Enhancements added:**
> 1. `try/except yaml.YAMLError` — handles malformed YAML gracefully
> 2. Type check on parsed root (must be dict)
> 3. Preview-mode handling (no YAML may be expected)
> 4. HA 2024.x+ compliance notes (trigger/action as lists per recent commit `e41d9d83`)

**Acceptance criteria:**
- YAML with trigger, action, alias, list format, no placeholders -> 1.0
- YAML with `{{placeholders}}` remaining -> score reduced by 0.2
- YAML missing trigger -> score reduced by 0.2
- Malformed YAML -> 0.0 with parse error details

---

### Story 3.3 — Entity Resolution Evaluator (L3) ✅

**New file:** `shared/patterns/evaluation/evaluators/l3_entity_resolution.py`

**Purpose:** Score how well the pipeline resolved abstract references (room names, device types) into concrete HA entity IDs and area IDs.

**Logic:**
```python
class EntityResolutionEvaluator(DetailsEvaluator):
    name = "entity_resolution"

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        resolved = session.metadata.get("resolved_context", {})
        placeholders = session.metadata.get("unresolved_placeholders", [])
        yaml_valid = session.metadata.get("yaml_valid", False)

        total = len(resolved) + len(placeholders)
        if total == 0:
            return self._result(0.8, "N/A", "No entities to resolve (simple template)")

        resolved_ratio = len(resolved) / total if total else 0
        score = resolved_ratio * 0.7  # 70% weight on resolution
        if yaml_valid:
            score += 0.3  # 30% bonus if YAML validates

        label = "Resolved" if score >= 0.8 else "Partial" if score >= 0.4 else "Unresolved"
        details = f"{len(resolved)}/{total} resolved, yaml_valid={yaml_valid}"
        return self._result(min(score, 1.0), label, details)
```

**Acceptance criteria:**
- All entities resolved + valid YAML -> 1.0
- Some placeholders remaining -> proportional score
- No entities to resolve (e.g., `scheduled_task` with only time params) -> 0.8

---

### Story 3.4 — Register custom evaluators in config ✅

**File:**
- `shared/patterns/evaluation/configs/ai_automation_service.yaml`
- `shared/patterns/evaluation/registry.py` — `_build_evaluators()` (lines 104-126)

**Approach:** The registry currently uses a builder pattern with level-specific methods (`_build_l1_evaluators`, `_build_l2_evaluators`, etc. — lines 128-230). Adding a generic `custom_evaluators` YAML section requires a dynamic class loader, which is more complex than needed.

**Recommended approach:** Add the custom evaluators directly in the existing level-specific builder methods:

```python
# In _build_l2_evaluators() (after line 162):
from .evaluators.l2_template_match import TemplateAppropriatenessEvaluator
evals.append(TemplateAppropriatenessEvaluator(llm_judge=self._judge))

# In _build_l3_evaluators() (after line 177):
from .evaluators.l3_yaml_completeness import YAMLCompletenessEvaluator
from .evaluators.l3_entity_resolution import EntityResolutionEvaluator
evals = [
    ToolParameterAccuracyEvaluator(config=config, llm_judge=self._judge),
    YAMLCompletenessEvaluator(),  # No LLM needed — fully deterministic
    EntityResolutionEvaluator(),  # No LLM needed — fully deterministic
]
return evals
```

> **Note:** `YAMLCompletenessEvaluator` and `EntityResolutionEvaluator` are fully deterministic — they don't need `llm_judge`. Only `TemplateAppropriatenessEvaluator` needs it for the LLM fallback path. The original code snippet passed `llm_judge` to all three, which is unnecessary.

> **Enhancement (future):** If more custom evaluators are expected, add dynamic loading via `importlib` and a `custom_evaluators` config section. But for 3 evaluators, direct imports are simpler and more maintainable.

**New evaluator count:** 15 -> 18 (corrected from 16 -> 19)

---

## Phase 4: Config & Rubric Tuning ✅ DONE

### Story 4.1 — Enable `response_relevance` quality rubric ✅

**File:** `shared/patterns/evaluation/configs/ai_automation_service.yaml` (line 258)

**Change:**
```yaml
quality_rubrics:
  - correctness
  - faithfulness
  - coherence
  - helpfulness
  - instruction_following
  - response_relevance   # NEW — does the output address the actual request?
```

**Purpose:** Catches cases where the pipeline generates a valid automation that doesn't match what the user asked for (e.g., user asks for thermostat control but gets a light automation).

**New evaluator count:** 18 -> 19 (corrected)

---

### Story 4.2 — Add preview-mode thresholds ✅

**File:** `shared/patterns/evaluation/configs/ai_automation_service.yaml` (line 271)

The current thresholds assume deploy runs. Add a note or separate threshold set for preview mode. Since the config schema doesn't support conditional thresholds, document the expected scores:

```yaml
# Preview-mode expected scores (deploy=False):
#   validation_before_deploy: 0.00 (expected — no deploy called)
#   post_deploy_verification: 0.00 (expected — no deploy called)
#   audit_trail_complete: 0.00 (expected — no audit data)
#   tool_sequence_validator: 0.50+ (preview path rule should pass)
#
# These rules only apply to deploy runs:
thresholds:
  goal_success_rate: 0.90
  tool_selection_accuracy: 0.95
  template_appropriateness: 0.80   # NEW
  tool_parameter_accuracy: 0.90
  yaml_completeness: 0.80           # NEW
  entity_resolution: 0.60           # NEW (lower — depends on data-api having areas)
  correctness: 0.95
  response_relevance: 0.80          # NEW
  validation_before_deploy: 1.00    # deploy-only
  post_deploy_verification: 0.95    # deploy-only
  no_direct_yaml_from_llm: 1.00
  yaml_safety_check: 1.00
  harmfulness: 1.00
```

---

### Story 4.3 — Make path rule exceptions deterministic ✅

**File:** `shared/patterns/evaluation/evaluators/l2_path.py` — `_check_exceptions()` (line 216)

**Current:** Sends exception descriptions to LLM for evaluation (slow, non-deterministic).

**Change:** Check `session.metadata` first for structured conditions. Only fall back to LLM if no metadata match:

```python
async def _check_exceptions(self, exceptions, session):
    mode = session.metadata.get("execution_mode", "deploy")

    # Deterministic exception checks
    for exc_text in exceptions:
        if "dry-run" in exc_text.lower() and mode in ("preview", "dry_run"):
            return True
        if "external source" in exc_text.lower() and mode == "external":
            return True
        if "manual" in exc_text.lower() and session.metadata.get("user_requested"):
            return True

    # Fall back to LLM judge for unrecognized exceptions
    return await self._llm_check_exceptions(exceptions, session)
```

**Impact:** Eliminates 3-4 LLM calls per evaluation for preview runs. Faster and deterministic.

---

## Phase 5: History Tracking & Regression Detection ✅ DONE (except Story 5.4)

### Story 5.1 — Append evaluation results to JSONL history file ✅

**File:** `tests/integration/test_ask_ai_pipeline.py` — end of `AskAITestHarness.run()`

**Changes:** After evaluation completes, append a summary line to a JSONL file:

```python
# At end of run(), after evaluation:
if pipeline_result.evaluation.available:
    history_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "reports", "eval-history.jsonl"
    )
    entry = {
        "timestamp": pipeline_result.timestamp,
        "prompt": pipeline_result.prompt[:100],
        "pipeline_score": pipeline_result.score.overall,
        "eval_overall": pipeline_result.evaluation.overall_score,
        "eval_levels": pipeline_result.evaluation.level_scores,
        "alerts": len(pipeline_result.evaluation.alerts),
        "deploy": deploy,
    }
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
```

**Output format (one line per run):**
```json
{"timestamp":"2026-02-11T20:56:22","prompt":"turn on the office lights","pipeline_score":99,"eval_overall":0.82,"eval_levels":{"L1_OUTCOME":1.0,"L2_PATH":0.625,"L3_DETAILS":1.0,"L4_QUALITY":0.475,"L5_SAFETY":1.0},"alerts":5,"deploy":false}
```

---

### Story 5.2 — Add `--min-eval-score` CLI flag for CI gating ✅

**File:** `tests/integration/test_ask_ai_pipeline.py` — CLI argument parser + exit logic

**Changes:**
```python
parser.add_argument(
    "--min-eval-score", type=float, default=0.0,
    help="Minimum evaluation score (0.0-1.0) to pass. Exit 1 if below.",
)

# After evaluation:
if args.min_eval_score and result.evaluation.available:
    if result.evaluation.overall_score < args.min_eval_score:
        print(f"\nEVAL FAILED: {result.evaluation.overall_score:.2f} < {args.min_eval_score}")
        return 1
```

**CI usage:**
```bash
# Preview mode (lower threshold — deploy rules expected to fail)
python test_ask_ai_pipeline.py "turn on lights" -e --min-score 80 --min-eval-score 0.70

# Deploy mode (full pipeline)
python test_ask_ai_pipeline.py "turn on lights" -e --deploy --min-score 80 --min-eval-score 0.85
```

---

### Story 5.3 — Regression detection report ✅

**New file:** `tests/integration/eval_regression_check.py`

**Purpose:** Read `eval-history.jsonl`, compute per-prompt baselines, and flag regressions.

**Logic:**
```python
# Group entries by prompt, compute rolling average of last 5 runs
# If latest score is >10% below the rolling average, flag as regression
# Output: markdown table of prompts with current vs baseline scores

Prompt                          Baseline   Latest   Delta   Status
turn on the office lights       0.92       0.82     -0.10   REGRESSION
set thermostat to 72            0.88       0.90     +0.02   OK
turn off all lights at midnight 0.85       0.86     +0.01   OK
```

**CI usage:**
```bash
python tests/integration/eval_regression_check.py --threshold 0.10
```

---

### Story 5.4 — Wire evaluation results to data-api REST endpoints ✅ DONE

**Purpose:** Store evaluation results in the existing evaluation infrastructure (InfluxDB + SQLite) for dashboard trending.

**Implementation:**

1. **New endpoint:** `POST /api/v1/evaluations/{agent_name}/results` in `services/data-api/src/evaluation_endpoints.py` — accepts pre-computed evaluation results directly from the test harness (bypasses scheduler). Accepts `SubmitResultsRequest` with `session_id`, `results[]`, and `aggregate_scores`, wraps in a `BatchReport`, and stores via `EvaluationStore.store_batch_report()`.

2. **`AgentEvaluationRunner.submit_to_data_api()`** in `tests/integration/test_ask_ai_pipeline.py` — new method that POSTs evaluation results to the data-api endpoint. Fails silently if data-api is unavailable (test harness should never break due to data-api).

3. **Harness wiring:** After evaluation runs and JSONL history is written, the harness calls `eval_runner.submit_to_data_api()` to store results for dashboard trending.

**Endpoints available on data-api (port 8006)** — verified in `services/data-api/src/evaluation_endpoints.py`, router mounted with `prefix="/api/v1"` in `main.py` line 424:
- `POST /api/v1/evaluations/{agent_name}/trigger` — manual evaluation trigger (line 289)
- `POST /api/v1/evaluations/{agent_name}/results` — direct result submission (Story 5.4)
- `GET /api/v1/evaluations/{agent_name}/history` — paginated historical results (line 201)
- `GET /api/v1/evaluations/{agent_name}/trends` — score trends over time (line 230)
- `GET /api/v1/evaluations/{agent_name}/alerts` — active threshold violations (line 245)
- `POST /api/v1/evaluations/{agent_name}/alerts/{alert_id}/acknowledge` — acknowledge alert (line 331)

---

## Phase Summary

| Phase | Stories | Status | Score Impact | Dependencies |
|-------|---------|--------|-------------|-------------|
| **Phase 1** | 1.1-1.4 | ✅ DONE | 82% -> ~86-88% (fixes false failures) | Stories 1.3+1.4 shipped together |
| **Phase 2** | 2.1-2.3 | ✅ DONE | Enables Phase 3 evaluators | Depends on Phase 1 (Story 1.3 for plan_step) |
| **Phase 3** | 3.1-3.4 | ✅ DONE | +3 HA-specific evaluators (18 total) | Depends on Phase 2 (metadata fields) |
| **Phase 4** | 4.1-4.3 | ✅ DONE | +1 rubric, deterministic exceptions | Depends on Phase 1 (execution_mode) |
| **Phase 5** | 5.1-5.3 | ✅ DONE | History tracking, CI gating, regression detection | Independent |
| **Phase 5** | 5.4 | ✅ DONE | Wire eval results to data-api REST endpoints | Requires data-api running |

**Total: 20 evaluator instances, ~90-93% preview score (with Phases 1+4), full regression detection pipeline.**

**All phases complete.** Phase 5 fully implemented including data-api wiring (Story 5.4).

> **Note on 95% target:** Reaching 95%+ in preview mode requires addressing the three deploy-dependent evaluators that score 0% (`validation_before_deploy`, `post_deploy_verification`, `audit_trail_complete`). Options:
> 1. Skip/N/A these evaluators when `execution_mode == "preview"` (simplest, most accurate)
> 2. Add conditional weighting in the scoring engine
> 3. Accept that preview mode has a lower ceiling and set preview target at ~90%

---

## Dependency Graph

```
Story 1.1 (execution_mode) ──────────────┐
                                          ├── Story 4.3 (deterministic exceptions)
Story 1.2 (preview path rule) ────────────┘

Story 1.3 (separate YAML from response) ──┬── Story 1.4 (yaml_safety_check metadata) ← MUST ship together
                                           ├── Story 2.1 (plan metadata — uses plan_step)
                                           └── Story 2.2 (YAML metadata — uses generated_yaml)

Story 2.1 (plan metadata) ────────────────┬── Story 3.1 (template_appropriateness — uses template_id)
Story 2.2 (YAML metadata) ────────────────┼── Story 3.2 (yaml_completeness — uses generated_yaml, placeholders)
                                           └── Story 3.3 (entity_resolution — uses resolved_context, placeholders)

Story 3.1-3.3 (new evaluators) ───────────── Story 3.4 (registration)

Story 5.1-5.4 (history/CI) ───────────────── Independent (can start anytime after Phase 1)
```

## Recommended Enhancements (Not in Original Plan)

### Enhancement A — Preview-mode evaluator skipping

**Problem:** Three deploy-dependent evaluators (`validation_before_deploy`, `post_deploy_verification`, `audit_trail_complete`) correctly score 0% in preview mode, but they drag L4 average down by ~30%. This makes the 95% target unreachable.

**Proposal:** In `EvaluationEngine.score_batch()`, skip evaluators whose `name` appears in a `skip_evaluators` list when `execution_mode == "preview"`:
```python
skip_in_preview = {"validation_before_deploy", "post_deploy_verification", "audit_trail_complete"}
if session.metadata.get("execution_mode") == "preview":
    evaluators = [e for e in evaluators if e.name not in skip_in_preview]
```

**Impact:** L4 average jumps from ~57% to ~81% in preview mode. Overall reaches ~93%.

### Enhancement B — Add `condition` key check to YAML completeness (Story 3.2)

Many HA automations use `condition` blocks. While not strictly required, their presence in templates that define conditions is a quality signal. Consider adding an optional 0.1 bonus for `condition` when the template is known to use conditions.

### Enhancement C — Verification script for Windows

The verification section uses bash syntax (`for prompt in ...`). Since this project runs on Windows, add a PowerShell equivalent:
```powershell
$prompts = @(
    "turn on the office lights",
    "set the thermostat to 72 degrees",
    "turn off all lights at midnight",
    "when I leave home turn off everything",
    "make it look like a party in the office"
)
foreach ($prompt in $prompts) {
    $slug = ($prompt -replace '\s+', '-').Substring(0, [Math]::Min(30, $prompt.Length))
    python tests/integration/test_ask_ai_pipeline.py $prompt -e -v -o "tests/integration/reports/eval-$slug.txt"
}
python tests/integration/eval_regression_check.py --threshold 0.10
```

---

## File Change Map

| File | Phase | Type | Status |
|------|-------|------|--------|
| `tests/integration/test_ask_ai_pipeline.py` | 1, 2, 5 | Modified | ✅ Trace builder, metadata enrichment, JSONL history, --min-eval-score CLI |
| `shared/patterns/evaluation/configs/ai_automation_service.yaml` | 1, 4 | Modified | ✅ Preview path rule, rollback exception, response_relevance rubric, thresholds |
| `shared/patterns/evaluation/evaluators/l4_quality.py` | 1 | Modified | ✅ `_check_response()` checks metadata YAML |
| `shared/patterns/evaluation/evaluators/l2_path.py` | 4 | Modified | ✅ `_check_exceptions()` deterministic-first |
| `shared/patterns/evaluation/evaluators/l2_template_match.py` | 3 | Created | ✅ TemplateAppropriatenessEvaluator |
| `shared/patterns/evaluation/evaluators/l3_yaml_completeness.py` | 3 | Created | ✅ YAMLCompletenessEvaluator |
| `shared/patterns/evaluation/evaluators/l3_entity_resolution.py` | 3 | Created | ✅ EntityResolutionEvaluator |
| `shared/patterns/evaluation/registry.py` | 3 | Modified | ✅ L2/L3 builder methods register new evaluators |
| `tests/integration/eval_regression_check.py` | 5 | Created | ✅ Regression detection script |

---

## Verification

After each phase, run the test harness across all 5 prompts and verify:

**PowerShell (Windows — primary dev environment):**
```powershell
$prompts = @(
    "turn on the office lights",
    "set the thermostat to 72 degrees",
    "turn off all lights at midnight",
    "when I leave home turn off everything",
    "make it look like a party in the office"
)
foreach ($prompt in $prompts) {
    $slug = ($prompt -replace '\s+', '-').Substring(0, [Math]::Min(30, $prompt.Length))
    python tests/integration/test_ask_ai_pipeline.py $prompt -e -v `
        -o "tests/integration/reports/eval-$slug.txt"
}

# Check regression
python tests/integration/eval_regression_check.py --threshold 0.10
```

**Bash (CI/Docker):**
```bash
for prompt in "turn on the office lights" "set the thermostat to 72 degrees" \
  "turn off all lights at midnight" "when I leave home turn off everything" \
  "make it look like a party in the office"; do
    python tests/integration/test_ask_ai_pipeline.py "$prompt" -e -v \
      -o "tests/integration/reports/eval-$(echo $prompt | tr ' ' '-' | head -c 30).txt"
done

python tests/integration/eval_regression_check.py --threshold 0.10
```
