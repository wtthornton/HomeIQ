"""
Ask AI Pipeline Test Harness --Reusable E2E Testing, Scoring & Debugging

A comprehensive test harness for the Ask AI automation creation pipeline.
Uses the Hybrid Flow: Plan -> Evaluate -> Clarification -> Compile -> YAML
Validation -> Content Analysis -> Deployment -> Verification -> Cleanup.

Services:
    - ai-automation-service-new (port 8036): Plan, Validate, Compile, Deploy
    - yaml-validation-service (port 8037): YAML validation

Provides multi-dimensional scoring, detailed diagnostics, and structured results
that can be consumed by pytest, CLI, or other test files.

Usage:
    # CLI
    python test_ask_ai_pipeline.py "turn on the office lights" --verbose
    python test_ask_ai_pipeline.py "party mode" --deploy --min-score 60
    python test_ask_ai_pipeline.py "set thermostat" --json > result.json

    # Pytest
    pytest test_ask_ai_pipeline.py -v -s --log-cli-level=INFO

    # Import from other tests
    from tests.integration.test_ask_ai_pipeline import AskAITestHarness
    harness = AskAITestHarness(client)
    result = await harness.run("turn on the office lights")
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator

import httpx
import pytest
import pytest_asyncio
import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_BASE_URL = os.environ.get("AI_AUTOMATION_API_URL", "http://localhost:8036")
DEFAULT_API_KEY = os.environ.get(
    "AI_AUTOMATION_API_KEY", "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"
)
DEFAULT_TIMEOUT = 300.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger("AskAIPipeline")

# Known HA entity domains for validation
KNOWN_DOMAINS = {
    "light", "switch", "sensor", "binary_sensor", "input_boolean",
    "input_number", "input_select", "input_text", "scene", "script",
    "automation", "counter", "group", "media_player", "climate",
    "cover", "fan", "lock", "vacuum", "camera", "device_tracker",
    "weather", "person", "zone", "number", "select", "button",
    "text", "event", "notify", "timer", "schedule",
}


# =========================================================================
# Enums
# =========================================================================

class StepStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class StepName(str, Enum):
    INTENT_PLAN = "Intent Plan"
    PLAN_EVALUATION = "Plan Evaluation"
    CLARIFICATION = "Clarification"
    PLAN_VALIDATION = "Plan Validation"
    YAML_COMPILE = "YAML Compile"
    YAML_VALIDATION = "YAML Validation"
    YAML_CONTENT_ANALYSIS = "YAML Content Analysis"
    DEPLOYMENT = "Deployment"
    POST_DEPLOY_VERIFICATION = "Post-Deploy Verification"
    CLEANUP = "Cleanup"


# =========================================================================
# Data Classes
# =========================================================================

@dataclass
class APICallRecord:
    """Record of a single API call for debugging."""
    method: str
    url: str
    request_body: dict | None
    response_status: int
    response_body: dict | None
    duration_ms: float
    error: str | None = None


@dataclass
class ScoreDimension:
    """A single scoring dimension with details and issues."""
    score: int = 0
    details: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


@dataclass
class PipelineScore:
    """Multi-dimensional pipeline quality score."""
    entity_extraction: ScoreDimension = field(default_factory=ScoreDimension)
    suggestion_quality: ScoreDimension = field(default_factory=ScoreDimension)
    yaml_validity: ScoreDimension = field(default_factory=ScoreDimension)
    yaml_completeness: ScoreDimension = field(default_factory=ScoreDimension)
    pipeline_reliability: ScoreDimension = field(default_factory=ScoreDimension)
    overall: int = 0

    # Dimension weights for overall score
    _WEIGHTS = {
        "entity_extraction": 0.15,
        "suggestion_quality": 0.20,
        "yaml_validity": 0.25,
        "yaml_completeness": 0.20,
        "pipeline_reliability": 0.20,
    }

    def compute_overall(self) -> int:
        """Compute weighted average of all dimensions."""
        total = 0.0
        for name, weight in self._WEIGHTS.items():
            dim: ScoreDimension = getattr(self, name)
            total += dim.score * weight
        self.overall = round(total)
        return self.overall


@dataclass
class StepResult:
    """Result of a single pipeline step."""
    name: StepName
    status: StepStatus
    duration_ms: float = 0.0
    score: int | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)


@dataclass
class PipelineDebugData:
    """Full debug capture for the pipeline run."""
    api_calls: list[APICallRecord] = field(default_factory=list)
    extracted_entities: list[dict] = field(default_factory=list)
    suggestions: list[dict] = field(default_factory=list)
    generated_yaml: str | None = None
    parsed_yaml: dict | None = None
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    quality_report: dict | None = None
    entity_mapping: dict[str, str] = field(default_factory=dict)
    clarification_questions: list[dict] = field(default_factory=list)
    clarification_answers: list[dict] = field(default_factory=list)
    resolved_context: dict[str, Any] = field(default_factory=dict)
    deployment_result: dict | None = None
    automation_id: str | None = None


@dataclass
class PipelineResult:
    """Complete result of a pipeline test run."""
    prompt: str
    success: bool
    score: PipelineScore
    steps: list[StepResult]
    debug: PipelineDebugData
    summary: str
    duration_ms: float
    timestamp: str


# =========================================================================
# AskAITestHarness
# =========================================================================

class AskAITestHarness:
    """
    Reusable test harness for the Ask AI automation creation pipeline.

    Not tied to pytest --can be used from CLI, other tests, or scripts.
    Instantiate with an httpx.AsyncClient and call ``run(prompt)``.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str | None = None,
        user_id: str = "test-pipeline-user",
    ):
        self.client = client
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.hybrid_url = f"{self.base_url}/automation"
        self.deploy_url = f"{self.base_url}/api/deploy"
        self.validate_url = f"{self.base_url}/api/v1/automations"
        self.user_id = user_id

        # Per-run state (reset in run())
        self._steps: list[StepResult] = []
        self._debug = PipelineDebugData()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        prompt: str,
        deploy: bool = False,
        clarification_strategy: str = "first_option",
        expected_entities: list[str] | None = None,
        expected_domains: list[str] | None = None,
    ) -> PipelineResult:
        """
        Run the full Hybrid Flow pipeline for *prompt* and return a structured result.

        Pipeline: Plan -> Evaluate -> Clarification -> Compile -> Validate -> Analyse -> Deploy

        Args:
            prompt: Natural language automation request.
            deploy: If True, deploy to HA then clean up.
            clarification_strategy: "first_option" or "skip".
            expected_entities: Optional list of entity names/ids to look for.
            expected_domains: Optional list of HA domains (e.g. ["light"]).
        """
        # Reset per-run state
        self._steps = []
        self._debug = PipelineDebugData()
        start = time.perf_counter()
        deployed_automation_id: str | None = None
        compiled_id: str | None = None

        try:
            # --- Step 1: Intent Plan (LLM selects template + parameters) ---
            plan_data = await self._step_intent_plan(prompt)

            # --- Step 2: Plan Evaluation (score quality of plan) ---
            if plan_data:
                self._step_plan_evaluation(
                    plan_data, expected_entities, expected_domains
                )
            else:
                self._skip_step(StepName.PLAN_EVALUATION, "Plan creation failed")

            # --- Step 3: Clarification (if plan needs it) ---
            if plan_data:
                clarifications = plan_data.get("clarifications_needed", [])
                if clarifications and clarification_strategy != "skip":
                    # Answer clarifications and re-plan
                    plan_data = await self._step_clarification_hybrid(
                        prompt, plan_data, clarification_strategy
                    )
                elif clarifications:
                    self._skip_step(StepName.CLARIFICATION, "Strategy set to skip")
                else:
                    self._skip_step(StepName.CLARIFICATION, "Not needed")
            else:
                self._skip_step(StepName.CLARIFICATION, "Plan creation failed")

            # --- Step 3.5: Plan Validation (resolve context) ---
            resolved_context: dict | None = None
            if plan_data:
                validate_result = await self._step_plan_validation(plan_data)
                if validate_result:
                    resolved_context = validate_result.get("resolved_context", {})
            else:
                self._skip_step(StepName.PLAN_VALIDATION, "No plan available")

            # --- Step 4: YAML Compile (deterministic, no LLM) ---
            yaml_content: str | None = None
            if plan_data:
                compile_data = await self._step_yaml_compile(plan_data, resolved_context)
                if compile_data:
                    yaml_content = compile_data.get("yaml")
                    compiled_id = compile_data.get("compiled_id")
            else:
                self._skip_step(StepName.YAML_COMPILE, "No plan available")

            # --- Step 5: YAML Validation ---
            if yaml_content:
                await self._step_yaml_validation(yaml_content)
            else:
                self._skip_step(StepName.YAML_VALIDATION, "No YAML to validate")

            # --- Step 6: YAML Content Analysis ---
            if yaml_content:
                self._step_yaml_content_analysis(yaml_content, expected_domains)
            else:
                self._skip_step(StepName.YAML_CONTENT_ANALYSIS, "No YAML to analyse")

            # --- Steps 7-9: Deployment (opt-in) ---
            if deploy and compiled_id:
                deploy_result = await self._step_deployment_compiled(compiled_id)
                if deploy_result:
                    deployed_automation_id = deploy_result.get(
                        "ha_automation_id",
                        deploy_result.get("automation_id"),
                    )
                    if deployed_automation_id:
                        await self._step_post_deploy_verification(
                            deployed_automation_id
                        )
                    else:
                        self._skip_step(
                            StepName.POST_DEPLOY_VERIFICATION,
                            "No automation_id from deployment",
                        )
                else:
                    self._skip_step(
                        StepName.POST_DEPLOY_VERIFICATION, "Deployment failed"
                    )
            elif deploy:
                self._skip_step(StepName.DEPLOYMENT, "No compiled_id available")
                self._skip_step(
                    StepName.POST_DEPLOY_VERIFICATION, "Deployment skipped"
                )
            else:
                self._skip_step(StepName.DEPLOYMENT, "Deploy not requested")
                self._skip_step(
                    StepName.POST_DEPLOY_VERIFICATION, "Deploy not requested"
                )

        except Exception as exc:
            logger.error(f"Pipeline run error: {exc}", exc_info=True)
        finally:
            # Cleanup always runs if we deployed
            if deployed_automation_id:
                await self._step_cleanup(deployed_automation_id)
            elif deploy:
                self._skip_step(StepName.CLEANUP, "Nothing to clean up")
            else:
                self._skip_step(StepName.CLEANUP, "Deploy not requested")

        duration_ms = (time.perf_counter() - start) * 1000
        score = self._build_score()
        success = all(
            s.status in (StepStatus.PASS, StepStatus.SKIP) for s in self._steps
        )
        summary = self._build_summary(prompt, score, duration_ms)

        return PipelineResult(
            prompt=prompt,
            success=success,
            score=score,
            steps=list(self._steps),
            debug=self._debug,
            summary=summary,
            duration_ms=round(duration_ms, 1),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Central API helper
    # ------------------------------------------------------------------

    async def _api_call(
        self,
        method: str,
        url: str,
        json_body: dict | None = None,
    ) -> tuple[int, dict | None, float]:
        """
        Make an HTTP call, record it, and return (status, body, duration_ms).
        Never raises --returns (0, None, duration) on connection error.
        """
        start = time.perf_counter()
        status = 0
        body: dict | None = None
        error: str | None = None

        try:
            if method.upper() == "GET":
                resp = await self.client.get(url)
            else:
                resp = await self.client.post(url, json=json_body)
            status = resp.status_code
            try:
                body = resp.json()
            except Exception:
                body = {"_raw": resp.text[:2000]}
        except httpx.TimeoutException as exc:
            error = f"Timeout: {exc}"
            logger.warning(f"API call timeout: {method} {url} --{exc}")
        except httpx.ConnectError as exc:
            error = f"Connection refused: {exc}"
            logger.warning(f"API connection error: {method} {url} --{exc}")
        except Exception as exc:
            error = f"Unexpected error: {exc}"
            logger.warning(f"API call error: {method} {url} --{exc}")

        duration_ms = (time.perf_counter() - start) * 1000
        self._debug.api_calls.append(
            APICallRecord(
                method=method.upper(),
                url=url,
                request_body=json_body,
                response_status=status,
                response_body=body,
                duration_ms=round(duration_ms, 1),
                error=error,
            )
        )
        return status, body, duration_ms

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    def _add_step(self, step: StepResult) -> None:
        self._steps.append(step)

    def _skip_step(self, name: StepName, reason: str) -> None:
        self._steps.append(
            StepResult(
                name=name,
                status=StepStatus.SKIP,
                warnings=[reason],
            )
        )

    # ------------------------------------------------------------------
    # Step 1: Intent Plan (LLM generates structured plan)
    # ------------------------------------------------------------------

    async def _step_intent_plan(self, prompt: str) -> dict | None:
        step = StepResult(name=StepName.INTENT_PLAN, status=StepStatus.PASS)
        start = time.perf_counter()

        import uuid
        conversation_id = f"test-{uuid.uuid4().hex[:8]}"
        url = f"{self.hybrid_url}/plan"
        payload = {
            "user_text": prompt,
            "conversation_id": conversation_id,
            "context": {},
        }
        status, body, call_ms = await self._api_call("POST", url, payload)

        score = 0
        try:
            if status == 200 and body:
                score += 40
                step.details.append(f"API returned 200 ({call_ms:.0f}ms)")

                plan_id = body.get("plan_id")
                template_id = body.get("template_id")
                confidence = body.get("confidence", 0)
                parameters = body.get("parameters", {})
                explanation = body.get("explanation", "")

                if plan_id:
                    score += 15
                    step.details.append(f"plan_id: {plan_id}")
                else:
                    step.issues.append("Response missing plan_id")

                if template_id:
                    score += 15
                    step.details.append(f"template: {template_id}")
                else:
                    step.issues.append("Response missing template_id")

                if parameters:
                    score += 15
                    step.details.append(f"parameters: {len(parameters)} keys")
                else:
                    step.issues.append("Empty parameters")

                if confidence >= 0.5:
                    score += 15
                    step.details.append(f"confidence: {confidence:.2f}")
                elif confidence > 0:
                    score += round(15 * confidence / 0.5)
                    step.warnings.append(f"Low confidence: {confidence:.2f}")

                # Capture debug data
                self._debug.suggestions = [body]  # Reuse suggestions field for plan
                step.data = {
                    "plan_id": plan_id,
                    "template_id": template_id,
                    "template_version": body.get("template_version"),
                    "confidence": confidence,
                    "safety_class": body.get("safety_class"),
                    "clarifications_needed": body.get("clarifications_needed", []),
                    "explanation": explanation,
                    "parameters": parameters,
                    "conversation_id": conversation_id,
                }

                if explanation:
                    step.details.append(f"Explanation: {explanation[:80]}...")

            elif status == 500 and body:
                # The plan endpoint may 500 on DB save but still have generated
                # the plan data in the error message --extract what we can
                detail = str(body.get("detail", ""))
                step.status = StepStatus.FAIL
                step.errors.append(f"API returned 500: {_truncate(body)}")

                # Check if it's a known DB migration issue
                if "no such table" in detail.lower():
                    step.warnings.append(
                        "DB table missing --plan endpoint needs migration. "
                        "The LLM may have generated the plan but it could not be saved."
                    )
            elif status == 0:
                step.status = StepStatus.ERROR
                step.errors.append("Could not connect to API")
            else:
                step.status = StepStatus.FAIL
                step.errors.append(f"API returned {status}: {_truncate(body, 500)}")
        except Exception as exc:
            step.status = StepStatus.ERROR
            step.errors.append(f"Exception: {exc}")

        step.score = score
        step.duration_ms = (time.perf_counter() - start) * 1000
        self._add_step(step)
        return body if step.status == StepStatus.PASS else None

    # ------------------------------------------------------------------
    # Step 2: Plan Evaluation (score quality of structured plan)
    # ------------------------------------------------------------------

    def _step_plan_evaluation(
        self,
        plan_data: dict,
        expected_entities: list[str] | None,
        expected_domains: list[str] | None,
    ) -> None:
        step = StepResult(name=StepName.PLAN_EVALUATION, status=StepStatus.PASS)
        score = 0

        template_id = plan_data.get("template_id", "")
        parameters = plan_data.get("parameters", {})
        safety_class = plan_data.get("safety_class", "")
        explanation = plan_data.get("explanation", "")

        # 25pts: template_id is non-empty and reasonable
        if template_id:
            score += 25
            step.details.append(f"Template: {template_id}")
        else:
            step.issues.append("No template_id selected")

        # 25pts: parameters are populated
        if parameters and len(parameters) >= 2:
            score += 25
            step.details.append(f"Parameters: {list(parameters.keys())}")
        elif parameters:
            score += 15
            step.warnings.append(f"Only {len(parameters)} parameter(s)")
        else:
            step.issues.append("No parameters generated")

        # 25pts: safety class is assigned
        if safety_class in ("low", "medium", "high", "critical"):
            score += 25
            step.details.append(f"Safety: {safety_class}")
        elif safety_class:
            score += 15
            step.warnings.append(f"Unknown safety_class: {safety_class}")
        else:
            step.issues.append("No safety_class assigned")

        # 25pts: explanation is meaningful
        if explanation and len(explanation) > 20:
            score += 25
            step.details.append(f"Explanation: {explanation[:60]}...")
        elif explanation:
            score += 10
            step.warnings.append("Short explanation")
        else:
            step.issues.append("No explanation provided")

        # Check expected domains against parameter values
        if expected_domains:
            param_str = json.dumps(parameters).lower()
            found = sum(1 for d in expected_domains if d.lower() in param_str)
            if found > 0:
                step.details.append(f"Found {found}/{len(expected_domains)} expected domains in parameters")
            else:
                step.warnings.append(f"Expected domains {expected_domains} not found in parameters")

        step.score = score
        step.data = {
            "template_id": template_id,
            "parameter_count": len(parameters),
            "safety_class": safety_class,
        }
        if score < 40:
            step.status = StepStatus.FAIL
        self._add_step(step)

    # ------------------------------------------------------------------
    # Step 3: Clarification (re-plan with context if clarifications needed)
    # ------------------------------------------------------------------

    async def _step_clarification_hybrid(
        self, prompt: str, plan_data: dict, strategy: str
    ) -> dict | None:
        """Answer clarifications by re-planning with extra context."""
        step = StepResult(name=StepName.CLARIFICATION, status=StepStatus.PASS)
        start = time.perf_counter()
        score = 0

        clarifications = plan_data.get("clarifications_needed", [])
        self._debug.clarification_questions = clarifications

        # Build context from clarifications (answer with defaults)
        extra_context: dict[str, Any] = {}
        answers = []
        for c in clarifications:
            question = c.get("question", c.get("text", ""))
            options = c.get("options", [])
            if strategy == "first_option" and options:
                answer = options[0] if isinstance(options[0], str) else str(options[0])
            else:
                answer = "Yes, proceed with default"
            extra_context[f"clarification_{len(answers)}"] = answer
            answers.append({"question": question, "answer": answer})
        self._debug.clarification_answers = answers

        # Re-plan with extra context
        import uuid
        url = f"{self.hybrid_url}/plan"
        payload = {
            "user_text": f"{prompt} (Context: {json.dumps(extra_context)})",
            "conversation_id": f"test-clarify-{uuid.uuid4().hex[:8]}",
            "context": extra_context,
        }
        status, body, call_ms = await self._api_call("POST", url, payload)

        try:
            if status == 200 and body:
                score += 50
                step.details.append(f"Re-plan returned 200 ({call_ms:.0f}ms)")
                new_clarifications = body.get("clarifications_needed", [])
                if not new_clarifications:
                    score += 50
                    step.details.append("No further clarifications needed")
                else:
                    score += 25
                    step.warnings.append(f"Still {len(new_clarifications)} clarifications")
            elif status == 0:
                step.status = StepStatus.ERROR
                step.errors.append("Could not connect to API")
                body = plan_data  # Fall back to original plan
            else:
                step.status = StepStatus.FAIL
                step.errors.append(f"API returned {status}: {_truncate(body)}")
                body = plan_data  # Fall back to original plan
        except Exception as exc:
            step.status = StepStatus.ERROR
            step.errors.append(f"Exception: {exc}")
            body = plan_data

        step.score = score
        step.duration_ms = (time.perf_counter() - start) * 1000
        step.data = {"clarifications_count": len(clarifications), "answers": len(answers)}
        self._add_step(step)
        return body

    # ------------------------------------------------------------------
    # Step 3.5: Plan Validation (resolves context: room -> area_id, etc.)
    # ------------------------------------------------------------------

    async def _step_plan_validation(self, plan_data: dict) -> dict | None:
        """
        Call POST /automation/validate to resolve context.

        This step resolves room_type -> area_id, finds presence/motion sensors,
        and returns resolved_context that the compile step needs to substitute
        {{placeholders}} with real entity/area IDs.
        """
        step = StepResult(name=StepName.PLAN_VALIDATION, status=StepStatus.PASS)
        start = time.perf_counter()
        score = 0

        plan_id = plan_data.get("plan_id", "unknown")
        template_id = plan_data.get("template_id", "")
        template_version = plan_data.get("template_version", 1)
        parameters = plan_data.get("parameters", {})

        url = f"{self.hybrid_url}/validate"
        payload = {
            "plan_id": plan_id,
            "template_id": template_id,
            "template_version": template_version,
            "parameters": parameters,
        }
        status, body, call_ms = await self._api_call("POST", url, payload)

        try:
            if status == 200 and body:
                score += 30
                step.details.append(f"API returned 200 ({call_ms:.0f}ms)")

                is_valid = body.get("valid", False)
                if is_valid:
                    score += 25
                    step.details.append("Validation: VALID")
                else:
                    step.warnings.append("Validation: INVALID (may still have resolved context)")

                # Validation errors from template schema
                v_errors = body.get("validation_errors", [])
                if v_errors:
                    for ve in v_errors:
                        field_name = ve.get("field", "unknown")
                        msg = ve.get("message", "unknown")
                        step.warnings.append(f"Param error: {field_name} - {msg}")
                else:
                    score += 15
                    step.details.append("No parameter validation errors")

                # Resolved context -- the key output
                resolved = body.get("resolved_context", {})
                if resolved:
                    score += 20
                    self._debug.resolved_context = resolved
                    step.details.append(f"Resolved context: {len(resolved)} keys")
                    for rk, rv in resolved.items():
                        step.details.append(f"  {rk}: {rv!r}")
                else:
                    score += 5  # Partial credit -- some templates need no context
                    step.warnings.append("Empty resolved_context (template may not need external context)")

                # Safety
                safety = body.get("safety", {})
                if safety:
                    allowed = safety.get("allowed", True)
                    requires_confirm = safety.get("requires_confirmation", False)
                    if allowed:
                        score += 10
                        step.details.append("Safety: allowed")
                    else:
                        step.issues.append("Safety: NOT allowed")
                    if requires_confirm:
                        step.warnings.append("Safety: requires user confirmation")

                step.data = {
                    "valid": is_valid,
                    "validation_errors": v_errors,
                    "resolved_context": resolved,
                    "safety": safety,
                }
            elif status == 0:
                step.status = StepStatus.ERROR
                step.errors.append("Could not connect to API")
            else:
                step.status = StepStatus.FAIL
                step.errors.append(f"API returned {status}: {_truncate(body)}")
        except Exception as exc:
            step.status = StepStatus.ERROR
            step.errors.append(f"Exception: {exc}")

        step.score = score
        step.duration_ms = (time.perf_counter() - start) * 1000
        self._add_step(step)
        return body if step.status == StepStatus.PASS else None

    # ------------------------------------------------------------------
    # Step 4: YAML Compile (deterministic)
    # ------------------------------------------------------------------

    async def _step_yaml_compile(self, plan_data: dict, resolved_context: dict | None = None) -> dict | None:
        step = StepResult(name=StepName.YAML_COMPILE, status=StepStatus.PASS)
        start = time.perf_counter()
        score = 0

        plan_id = plan_data.get("plan_id", "unknown")
        template_id = plan_data.get("template_id", "")
        template_version = plan_data.get("template_version", 1)
        parameters = plan_data.get("parameters", {})

        url = f"{self.hybrid_url}/compile"
        payload = {
            "plan_id": plan_id,
            "template_id": template_id,
            "template_version": template_version,
            "parameters": parameters,
            "resolved_context": resolved_context or {},
        }
        status, body, call_ms = await self._api_call("POST", url, payload)

        try:
            if status == 200 and body:
                score += 30
                step.details.append(f"API returned 200 ({call_ms:.0f}ms)")

                yaml_content = body.get("yaml", "")
                if yaml_content:
                    score += 25
                    step.details.append(f"YAML: {len(yaml_content)} chars")
                    self._debug.generated_yaml = yaml_content
                else:
                    step.issues.append("Empty yaml in compile response")

                # Try parsing
                if yaml_content:
                    try:
                        parsed = yaml.safe_load(yaml_content)
                        score += 20
                        step.details.append("YAML parses successfully")
                        self._debug.parsed_yaml = parsed
                    except yaml.YAMLError as exc:
                        step.issues.append(f"YAML parse error: {exc}")

                # Human summary
                summary = body.get("human_summary", "")
                if summary:
                    score += 15
                    step.details.append(f"Summary: {summary[:60]}...")

                # Risk notes
                risk_notes = body.get("risk_notes", [])
                if risk_notes:
                    score += 10
                    step.details.append(f"{len(risk_notes)} risk note(s)")
                    for rn in risk_notes[:3]:
                        step.warnings.append(f"Risk: {rn}")
                else:
                    score += 10  # No risks is fine

                step.data = {
                    "compiled_id": body.get("compiled_id"),
                    "yaml_length": len(yaml_content),
                    "human_summary": summary,
                    "risk_note_count": len(risk_notes),
                }
            elif status == 0:
                step.status = StepStatus.ERROR
                step.errors.append("Could not connect to API")
            else:
                step.status = StepStatus.FAIL
                step.errors.append(f"API returned {status}: {_truncate(body)}")
        except Exception as exc:
            step.status = StepStatus.ERROR
            step.errors.append(f"Exception: {exc}")

        step.score = score
        step.duration_ms = (time.perf_counter() - start) * 1000
        self._add_step(step)
        return body if step.status == StepStatus.PASS else None

    # ------------------------------------------------------------------
    # Step 6: YAML Validation
    # ------------------------------------------------------------------

    async def _step_yaml_validation(self, yaml_content: str) -> dict | None:
        step = StepResult(name=StepName.YAML_VALIDATION, status=StepStatus.PASS)
        start = time.perf_counter()
        score = 0

        url = f"{self.validate_url}/validate"
        payload = {
            "yaml_content": yaml_content,
            "normalize": True,
            "validate_entities": True,
            "validate_services": True,
        }
        status, body, call_ms = await self._api_call("POST", url, payload)

        try:
            if status == 200 and body:
                score += 30
                step.details.append(f"API returned 200 ({call_ms:.0f}ms)")

                is_valid = body.get("valid", False)
                if is_valid:
                    score += 30
                    step.details.append("Validation: VALID")
                else:
                    step.issues.append("Validation: INVALID")

                errors = body.get("errors", [])
                if not errors:
                    score += 20
                    step.details.append("No validation errors")
                else:
                    self._debug.validation_errors = errors
                    step.issues.append(f"{len(errors)} validation errors: {errors[:3]}")

                warnings = body.get("warnings", [])
                if warnings:
                    self._debug.validation_warnings = warnings
                    step.warnings.extend(warnings[:5])

                # Validation score (0-100 -> 0-10 contribution)
                val_score = body.get("score", 0)
                if isinstance(val_score, (int, float)) and val_score > 0:
                    score += min(10, round(val_score / 10))
                    step.details.append(f"Validation score: {val_score:.0f}/100")

                # Entity validation subsection
                ev = body.get("entity_validation", {})
                if ev.get("passed"):
                    score += 10
                    step.details.append("Entity validation passed")
                elif ev.get("performed"):
                    step.issues.append(
                        f"Entity validation failed: {ev.get('errors', [])}"
                    )

                step.data = {
                    "valid": is_valid,
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                    "score": val_score,
                }
            elif status == 0:
                step.status = StepStatus.ERROR
                step.errors.append("Could not connect to validation API")
            else:
                # Validation endpoint may not be deployed --treat as warning
                step.status = StepStatus.FAIL
                step.errors.append(f"Validation API returned {status}: {_truncate(body)}")
        except Exception as exc:
            step.status = StepStatus.ERROR
            step.errors.append(f"Exception: {exc}")

        step.score = score
        step.duration_ms = (time.perf_counter() - start) * 1000
        self._add_step(step)
        return body if step.status == StepStatus.PASS else None

    # ------------------------------------------------------------------
    # Step 7: YAML Content Analysis
    # ------------------------------------------------------------------

    def _step_yaml_content_analysis(
        self, yaml_content: str, expected_domains: list[str] | None
    ) -> None:
        step = StepResult(name=StepName.YAML_CONTENT_ANALYSIS, status=StepStatus.PASS)
        score = 0

        try:
            parsed = yaml.safe_load(yaml_content)
        except yaml.YAMLError as exc:
            step.status = StepStatus.FAIL
            step.errors.append(f"YAML parse error: {exc}")
            step.score = 0
            self._add_step(step)
            return

        if not isinstance(parsed, dict):
            step.status = StepStatus.FAIL
            step.errors.append(f"YAML root is {type(parsed).__name__}, expected dict")
            step.score = 0
            self._add_step(step)
            return

        # 20pts: has triggers
        has_triggers = "trigger" in parsed or "triggers" in parsed
        if has_triggers:
            score += 20
            step.details.append("Has trigger(s)")
        else:
            step.issues.append("Missing trigger/triggers key")

        # 20pts: has actions
        has_actions = "action" in parsed or "actions" in parsed
        if has_actions:
            score += 20
            step.details.append("Has action(s)")
        else:
            step.issues.append("Missing action/actions key")

        # 15pts: has alias
        if parsed.get("alias"):
            score += 15
            step.details.append(f"Alias: {parsed['alias']}")
        else:
            step.warnings.append("No alias set")

        # 15pts: entity references in content
        yaml_str = yaml_content.lower()
        entity_refs = re.findall(
            r"\b(" + "|".join(KNOWN_DOMAINS) + r")\.\w+", yaml_str
        )
        if entity_refs:
            score += 15
            unique_refs = set(entity_refs)
            step.details.append(f"{len(unique_refs)} unique entity references")
        else:
            step.issues.append("No entity references found in YAML")

        # 15pts: expected domains appear in YAML
        if expected_domains:
            found = sum(1 for d in expected_domains if d.lower() in yaml_str)
            ratio = found / len(expected_domains)
            score += round(15 * ratio)
            if ratio < 1.0:
                missing = [d for d in expected_domains if d.lower() not in yaml_str]
                step.issues.append(f"Expected domains not in YAML: {missing}")
            else:
                step.details.append("All expected domains found in YAML")
        else:
            score += 15

        # 15pts: has conditions (warn-only if absent)
        has_conditions = "condition" in parsed or "conditions" in parsed
        if has_conditions:
            score += 15
            step.details.append("Has condition(s)")
        else:
            score += 8  # Partial credit --simple automations often have no conditions
            step.warnings.append("No conditions in YAML (may be intentional)")

        step.score = score
        step.data = {
            "has_triggers": has_triggers,
            "has_actions": has_actions,
            "has_conditions": has_conditions,
            "has_alias": bool(parsed.get("alias")),
            "entity_ref_count": len(set(entity_refs)) if entity_refs else 0,
        }
        self._add_step(step)

    # ------------------------------------------------------------------
    # Step 7: Deployment (compiled artifact)
    # ------------------------------------------------------------------

    async def _step_deployment_compiled(self, compiled_id: str) -> dict | None:
        step = StepResult(name=StepName.DEPLOYMENT, status=StepStatus.PASS)
        start = time.perf_counter()
        score = 0

        url = f"{self.deploy_url}/automation/deploy"
        payload = {
            "compiled_id": compiled_id,
            "approved_by": self.user_id,
            "ui_source": "pipeline-test",
        }
        status, body, call_ms = await self._api_call("POST", url, payload)

        try:
            if status == 200 and body:
                score += 40
                step.details.append(f"API returned 200 ({call_ms:.0f}ms)")

                ha_automation_id = body.get("ha_automation_id", body.get("automation_id"))
                deploy_status = body.get("status", "")

                if ha_automation_id:
                    score += 30
                    step.details.append(f"ha_automation_id: {ha_automation_id}")
                    self._debug.automation_id = ha_automation_id
                else:
                    step.issues.append("No automation_id in response")

                if deploy_status in ("deployed", "success"):
                    score += 30
                    step.details.append(f"Status: {deploy_status}")
                else:
                    step.issues.append(f"Unexpected deploy status: {deploy_status}")

                self._debug.deployment_result = body
                step.data = {
                    "ha_automation_id": ha_automation_id,
                    "deployment_id": body.get("deployment_id"),
                    "status": deploy_status,
                    "state": body.get("state"),
                    "verification_warning": body.get("verification_warning"),
                }
            elif status == 0:
                step.status = StepStatus.ERROR
                step.errors.append("Could not connect to deploy API")
            else:
                step.status = StepStatus.FAIL
                step.errors.append(f"API returned {status}: {_truncate(body)}")
        except Exception as exc:
            step.status = StepStatus.ERROR
            step.errors.append(f"Exception: {exc}")

        step.score = score
        step.duration_ms = (time.perf_counter() - start) * 1000
        self._add_step(step)
        return body if step.status == StepStatus.PASS else None

    # ------------------------------------------------------------------
    # Step 9: Post-Deploy Verification
    # ------------------------------------------------------------------

    async def _step_post_deploy_verification(self, automation_id: str) -> None:
        step = StepResult(
            name=StepName.POST_DEPLOY_VERIFICATION, status=StepStatus.PASS
        )
        start = time.perf_counter()
        score = 0

        url = f"{self.deploy_url}/automations/{automation_id}"
        status, body, call_ms = await self._api_call("GET", url)

        try:
            if status == 200 and body:
                score += 50
                step.details.append(f"API returned 200 ({call_ms:.0f}ms)")

                state = body.get("state", body.get("status", ""))
                if state in ("on", "deployed", "enabled"):
                    score += 25
                    step.details.append(f"State: {state}")
                else:
                    step.issues.append(f"Unexpected state: {state}")

                resp_id = body.get("automation_id", body.get("entity_id", ""))
                if automation_id in str(resp_id):
                    score += 25
                    step.details.append("Automation ID matches")
                else:
                    step.issues.append(
                        f"ID mismatch: expected {automation_id}, got {resp_id}"
                    )

                step.data = {"state": state, "response_id": resp_id}
            elif status == 0:
                step.status = StepStatus.ERROR
                step.errors.append("Could not connect to API")
            else:
                step.status = StepStatus.FAIL
                step.errors.append(f"API returned {status}: {_truncate(body)}")
        except Exception as exc:
            step.status = StepStatus.ERROR
            step.errors.append(f"Exception: {exc}")

        step.score = score
        step.duration_ms = (time.perf_counter() - start) * 1000
        self._add_step(step)

    # ------------------------------------------------------------------
    # Step 10: Cleanup
    # ------------------------------------------------------------------

    async def _step_cleanup(self, automation_id: str) -> None:
        step = StepResult(name=StepName.CLEANUP, status=StepStatus.PASS)
        start = time.perf_counter()

        try:
            url = f"{self.deploy_url}/automations/{automation_id}/disable"
            status, body, call_ms = await self._api_call("POST", url)

            if status == 200:
                step.details.append(f"Disabled {automation_id} ({call_ms:.0f}ms)")
            else:
                step.status = StepStatus.FAIL
                step.warnings.append(
                    f"Failed to disable {automation_id}: status {status}"
                )
        except Exception as exc:
            step.status = StepStatus.FAIL
            step.warnings.append(f"Cleanup error: {exc}")

        step.duration_ms = (time.perf_counter() - start) * 1000
        self._add_step(step)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _build_score(self) -> PipelineScore:
        ps = PipelineScore()

        # Map steps to dimensions (Hybrid Flow)
        # Entity extraction = blend of plan evaluation + plan validation (context resolution)
        eval_dim = self._dim_from_step(StepName.PLAN_EVALUATION)
        ctx_dim = self._dim_from_step(StepName.PLAN_VALIDATION)
        if ctx_dim.score > 0:
            # Weighted: 40% evaluation + 60% context resolution (entities are the key deliverable)
            blended_score = round(eval_dim.score * 0.4 + ctx_dim.score * 0.6)
            ps.entity_extraction = ScoreDimension(
                score=blended_score,
                details=eval_dim.details + ctx_dim.details,
                issues=eval_dim.issues + ctx_dim.issues,
            )
        else:
            ps.entity_extraction = eval_dim

        ps.suggestion_quality = self._dim_from_step(StepName.INTENT_PLAN)

        # YAML validity = average of compile + validation
        gen = self._dim_from_step(StepName.YAML_COMPILE)
        val = self._dim_from_step(StepName.YAML_VALIDATION)
        ps.yaml_validity = ScoreDimension(
            score=round((gen.score + val.score) / 2) if (gen.score + val.score) else 0,
            details=gen.details + val.details,
            issues=gen.issues + val.issues,
        )

        ps.yaml_completeness = self._dim_from_step(StepName.YAML_CONTENT_ANALYSIS)

        # Pipeline reliability
        non_skip = [s for s in self._steps if s.status != StepStatus.SKIP]
        failed = [
            s for s in non_skip
            if s.status in (StepStatus.ERROR, StepStatus.FAIL)
        ]
        if non_skip:
            penalty = min(100 / len(non_skip), 25)
            reliability_score = max(0, round(100 - len(failed) * penalty))
        else:
            reliability_score = 0
        ps.pipeline_reliability = ScoreDimension(
            score=reliability_score,
            details=[f"{len(non_skip) - len(failed)}/{len(non_skip)} steps passed"],
            issues=[f"Failed: {s.name.value}" for s in failed],
        )

        ps.compute_overall()
        return ps

    def _dim_from_step(self, name: StepName) -> ScoreDimension:
        step = next((s for s in self._steps if s.name == name), None)
        if not step or step.status == StepStatus.SKIP:
            return ScoreDimension(score=0, details=["Skipped"], issues=[])
        return ScoreDimension(
            score=step.score or 0,
            details=getattr(step, "details", []),
            issues=getattr(step, "issues", []),
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _build_summary(
        self, prompt: str, score: PipelineScore, duration_ms: float
    ) -> str:
        passed = sum(1 for s in self._steps if s.status == StepStatus.PASS)
        total = sum(1 for s in self._steps if s.status != StepStatus.SKIP)
        all_issues = []
        for s in self._steps:
            all_issues.extend(getattr(s, "issues", []))
            all_issues.extend(s.errors)
        issue_str = f" | Issues: {', '.join(all_issues[:3])}" if all_issues else ""
        return (
            f'Prompt: "{prompt[:60]}" | '
            f"Score: {score.overall}/100 | "
            f"Steps: {passed}/{total} passed | "
            f"Duration: {duration_ms / 1000:.1f}s"
            f"{issue_str}"
        )


# =========================================================================
# Report Formatter
# =========================================================================

class PipelineReportFormatter:
    """Formats a PipelineResult into a human-readable ASCII report."""

    STEP_ICONS = {
        StepStatus.PASS: "[PASS]",
        StepStatus.FAIL: "[FAIL]",
        StepStatus.SKIP: "[SKIP]",
        StepStatus.ERROR: "[ERR!]",
    }

    W = 72  # Report width (standard)
    DW = 100  # Diagnostic width (wider for full data)

    @classmethod
    def format_report(
        cls,
        result: PipelineResult,
        verbose: bool = False,
        diagnostic: bool = False,
    ) -> str:
        """
        Format a pipeline result as an ASCII report.

        Modes:
            default:    Summary with scores, steps, issues, warnings.
            verbose:    + YAML, API timings, quality report.
            diagnostic: Full forensic output --every API request/response body,
                        prompt-vs-plan analysis, YAML deep inspection, entity
                        resolution audit, validation details, and an action
                        items summary. Use this for debugging the pipeline.
        """
        # Diagnostic implies verbose
        if diagnostic:
            verbose = True
        w = cls.DW if diagnostic else cls.W

        lines: list[str] = []

        lines.append("+" + "=" * (w - 2) + "+")
        title = "ASK AI PIPELINE - DIAGNOSTIC REPORT" if diagnostic else "ASK AI PIPELINE TEST RESULTS"
        lines.append(cls._row(title, w))
        lines.append("+" + "=" * (w - 2) + "+")

        # Prompt (full in diagnostic mode)
        if diagnostic:
            lines.append(cls._row("PROMPT (full):", w))
            for chunk in cls._wrap(result.prompt, w - 6):
                lines.append(cls._row(f"  {chunk}", w))
        else:
            prompt_display = result.prompt[:w - 16]
            if len(result.prompt) > w - 16:
                prompt_display += "..."
            lines.append(cls._row(f'Prompt: "{prompt_display}"', w))

        lines.append(cls._row(
            f"Overall Score: {result.score.overall}/100   "
            f"Success: {'YES' if result.success else 'NO'}",
            w,
        ))
        lines.append(cls._row(
            f"Duration: {result.duration_ms / 1000:.1f}s   "
            f"Time: {result.timestamp[:19]}",
            w,
        ))
        lines.append("+" + "-" * (w - 2) + "+")

        # ── Score dimensions ──────────────────────────────────────────
        lines.append(cls._row("SCORES", w))
        for dim_name in [
            "entity_extraction", "suggestion_quality", "yaml_validity",
            "yaml_completeness", "pipeline_reliability",
        ]:
            dim: ScoreDimension = getattr(result.score, dim_name)
            label = dim_name.replace("_", " ").title()
            lines.append(cls._row(f"  {label:.<30s} {dim.score:>3d}/100", w))
            if diagnostic:
                for d in dim.details:
                    lines.append(cls._row(f"      + {d[:w - 12]}", w))
                for i in dim.issues:
                    lines.append(cls._row(f"      ! {i[:w - 12]}", w))
        lines.append("+" + "-" * (w - 2) + "+")

        # ── Steps ─────────────────────────────────────────────────────
        lines.append(cls._row("STEPS", w))
        for step in result.steps:
            icon = cls.STEP_ICONS.get(step.status, "[????]")
            name = step.name.value
            if step.status == StepStatus.SKIP:
                reason = step.warnings[0] if step.warnings else ""
                lines.append(cls._row(f"  {icon} {name}  ({reason})", w))
            else:
                dur = f"({step.duration_ms / 1000:.1f}s)" if step.duration_ms else ""
                sc = f"Score: {step.score}" if step.score is not None else ""
                lines.append(cls._row(
                    f"  {icon} {name:<24s} {dur:>7s}  {sc}", w
                ))
            if diagnostic and step.status != StepStatus.SKIP:
                for d in step.details:
                    lines.append(cls._row(f"         + {d[:w - 16]}", w))
                for i in step.issues:
                    lines.append(cls._row(f"         ! {i[:w - 16]}", w))
                for e in step.errors:
                    lines.append(cls._row(f"         X {e[:w - 16]}", w))
                for wr in step.warnings:
                    lines.append(cls._row(f"         ~ {wr[:w - 16]}", w))
        lines.append("+" + "-" * (w - 2) + "+")

        # ── Entities ──────────────────────────────────────────────────
        if result.debug.extracted_entities:
            lines.append(cls._row("ENTITIES", w))
            for e in result.debug.extracted_entities[:15]:
                eid = e.get("entity_id", "N/A")
                name = e.get("name", e.get("friendly_name", ""))
                valid = "[valid]" if "." in eid and eid.split(".")[0] in KNOWN_DOMAINS else "[????]"
                display = f"  {eid:<35s} {valid}"
                if name:
                    display += f"  ({name})"
                lines.append(cls._row(display[:w - 4], w))
            if len(result.debug.extracted_entities) > 15:
                lines.append(cls._row(
                    f"  ... and {len(result.debug.extracted_entities) - 15} more",
                    w,
                ))
            lines.append("+" + "-" * (w - 2) + "+")

        # ── Entity Mapping ────────────────────────────────────────────
        if result.debug.entity_mapping:
            lines.append(cls._row("ENTITY MAPPING (device -> entity_id)", w))
            for device, eid in result.debug.entity_mapping.items():
                lines.append(cls._row(f"  {device} -> {eid}", w))
            lines.append("+" + "-" * (w - 2) + "+")

        # ── Issues ────────────────────────────────────────────────────
        all_issues: list[str] = []
        for step in result.steps:
            for issue in step.issues:
                all_issues.append(f"({step.name.value}) {issue}")
            for err in step.errors:
                all_issues.append(f"({step.name.value}) ERROR: {err}")
        if all_issues:
            lines.append(cls._row("ISSUES", w))
            for issue in all_issues[:30]:
                # No truncation in diagnostic mode
                limit = w - 10 if not diagnostic else w - 10
                for chunk in cls._wrap(f"(!) {issue}", limit):
                    lines.append(cls._row(f"  {chunk}", w))
            lines.append("+" + "-" * (w - 2) + "+")

        # ── Warnings ─────────────────────────────────────────────────
        all_warnings: list[str] = []
        for step in result.steps:
            for warn in step.warnings:
                all_warnings.append(f"({step.name.value}) {warn}")
        if all_warnings:
            lines.append(cls._row("WARNINGS", w))
            for warn in all_warnings[:15]:
                for chunk in cls._wrap(f"(~) {warn}", w - 10):
                    lines.append(cls._row(f"  {chunk}", w))
            lines.append("+" + "-" * (w - 2) + "+")

        # ── Verbose sections ──────────────────────────────────────────
        if verbose:
            # Generated YAML
            if result.debug.generated_yaml:
                lines.append(cls._row("GENERATED YAML", w))
                yaml_lines = result.debug.generated_yaml.split("\n")
                for yl in yaml_lines[:120]:
                    lines.append(cls._row(f"  {yl[:w - 6]}", w))
                if len(yaml_lines) > 120:
                    lines.append(cls._row(
                        f"  ... ({len(yaml_lines) - 120} more lines)", w
                    ))
                lines.append("+" + "-" * (w - 2) + "+")

            # API call timings
            lines.append(cls._row("API CALLS", w))
            for call in result.debug.api_calls:
                status_str = str(call.response_status) if call.response_status else "ERR"
                lines.append(cls._row(
                    f"  {call.method:4s} {status_str:>3s} "
                    f"{call.duration_ms:>7.0f}ms  {call.url[:w - 26]}",
                    w,
                ))
                if call.error:
                    lines.append(cls._row(f"       Error: {call.error[:w - 18]}", w))
            lines.append("+" + "-" * (w - 2) + "+")

            # Quality report
            if result.debug.quality_report:
                lines.append(cls._row("QUALITY REPORT", w))
                checks = result.debug.quality_report.get("checks", [])
                for chk in checks[:20]:
                    status = chk.get("status", "?")
                    name = chk.get("name", chk.get("check", "unnamed"))
                    lines.append(cls._row(f"  {status:>6s}  {name}", w))
                lines.append("+" + "-" * (w - 2) + "+")

        # ── Diagnostic-only sections ──────────────────────────────────
        if diagnostic:
            # --- PLAN RESPONSE ANALYSIS ---
            plan_step = next(
                (s for s in result.steps if s.name == StepName.INTENT_PLAN), None
            )
            if plan_step and plan_step.data:
                lines.append(cls._row("PLAN RESPONSE (full)", w))
                lines.append(cls._row(
                    f"  template_id: {plan_step.data.get('template_id', 'N/A')}", w
                ))
                lines.append(cls._row(
                    f"  template_version: {plan_step.data.get('template_version', 'N/A')}", w
                ))
                lines.append(cls._row(
                    f"  plan_id: {plan_step.data.get('plan_id', 'N/A')}", w
                ))
                lines.append(cls._row(
                    f"  confidence: {plan_step.data.get('confidence', 'N/A')}", w
                ))
                lines.append(cls._row(
                    f"  safety_class: {plan_step.data.get('safety_class', 'N/A')}", w
                ))
                clarifications = plan_step.data.get("clarifications_needed", [])
                lines.append(cls._row(
                    f"  clarifications_needed: {len(clarifications)}", w
                ))
                lines.append(cls._row(
                    f"  conversation_id: {plan_step.data.get('conversation_id', 'N/A')}", w
                ))
                lines.append(cls._row("  parameters:", w))
                params = plan_step.data.get("parameters", {})
                for pk, pv in params.items():
                    lines.append(cls._row(f"    {pk}: {pv!r}", w))
                lines.append(cls._row("  explanation:", w))
                explanation = plan_step.data.get("explanation", "")
                for chunk in cls._wrap(explanation, w - 10):
                    lines.append(cls._row(f"    {chunk}", w))
                lines.append("+" + "-" * (w - 2) + "+")

            # --- CONTEXT RESOLUTION ---
            validate_step = next(
                (s for s in result.steps if s.name == StepName.PLAN_VALIDATION), None
            )
            if validate_step and validate_step.data:
                lines.append(cls._row("CONTEXT RESOLUTION", w))
                vd = validate_step.data
                lines.append(cls._row(f"  valid: {vd.get('valid', 'N/A')}", w))
                resolved = vd.get("resolved_context", {})
                if resolved:
                    lines.append(cls._row(f"  resolved_context ({len(resolved)} keys):", w))
                    for rk, rv in resolved.items():
                        lines.append(cls._row(f"    {rk}: {rv!r}", w))
                else:
                    lines.append(cls._row("  resolved_context: (empty)", w))
                v_errs = vd.get("validation_errors", [])
                if v_errs:
                    lines.append(cls._row(f"  parameter_errors ({len(v_errs)}):", w))
                    for ve in v_errs:
                        lines.append(cls._row(
                            f"    {ve.get('field','?')}: {ve.get('message','?')}", w
                        ))
                safety = vd.get("safety", {})
                if safety:
                    lines.append(cls._row(f"  safety: allowed={safety.get('allowed', '?')}, "
                                          f"confirm={safety.get('requires_confirmation', '?')}", w))
                lines.append("+" + "-" * (w - 2) + "+")
            elif result.debug.resolved_context:
                lines.append(cls._row("CONTEXT RESOLUTION", w))
                for rk, rv in result.debug.resolved_context.items():
                    lines.append(cls._row(f"  {rk}: {rv!r}", w))
                lines.append("+" + "-" * (w - 2) + "+")

            # --- PROMPT vs PLAN ANALYSIS ---
            lines.append(cls._row("PROMPT vs PLAN ANALYSIS", w))
            cls._analyze_prompt_vs_plan(lines, result, w)
            lines.append("+" + "-" * (w - 2) + "+")

            # --- YAML DEEP INSPECTION ---
            if result.debug.parsed_yaml:
                lines.append(cls._row("YAML DEEP INSPECTION", w))
                cls._inspect_yaml(lines, result, w)
                lines.append("+" + "-" * (w - 2) + "+")

            # --- VALIDATION DETAIL ---
            if result.debug.validation_errors or result.debug.validation_warnings:
                lines.append(cls._row("VALIDATION DETAIL", w))
                if result.debug.validation_errors:
                    lines.append(cls._row("  Errors:", w))
                    for i, err in enumerate(result.debug.validation_errors, 1):
                        for chunk in cls._wrap(f"{i}. {err}", w - 10):
                            lines.append(cls._row(f"    {chunk}", w))
                if result.debug.validation_warnings:
                    lines.append(cls._row("  Warnings:", w))
                    for i, wrn in enumerate(result.debug.validation_warnings, 1):
                        for chunk in cls._wrap(f"{i}. {wrn}", w - 10):
                            lines.append(cls._row(f"    {chunk}", w))
                lines.append("+" + "-" * (w - 2) + "+")

            # --- FULL API REQUEST/RESPONSE BODIES ---
            lines.append(cls._row("API REQUEST/RESPONSE BODIES", w))
            for idx, call in enumerate(result.debug.api_calls, 1):
                lines.append(cls._row(f"  --- Call {idx}: {call.method} {call.url} ---", w))
                lines.append(cls._row(f"  Status: {call.response_status}  Duration: {call.duration_ms:.0f}ms", w))
                if call.request_body:
                    lines.append(cls._row("  Request:", w))
                    req_str = json.dumps(call.request_body, indent=2, default=str)
                    for rl in req_str.split("\n")[:40]:
                        lines.append(cls._row(f"    {rl[:w - 10]}", w))
                if call.response_body:
                    lines.append(cls._row("  Response:", w))
                    resp_str = json.dumps(call.response_body, indent=2, default=str)
                    resp_lines = resp_str.split("\n")
                    for rl in resp_lines[:60]:
                        lines.append(cls._row(f"    {rl[:w - 10]}", w))
                    if len(resp_lines) > 60:
                        lines.append(cls._row(f"    ... ({len(resp_lines) - 60} more lines)", w))
                lines.append(cls._row("", w))
            lines.append("+" + "-" * (w - 2) + "+")

            # --- ACTION ITEMS ---
            lines.append(cls._row("FINDINGS & ACTION ITEMS", w))
            cls._build_action_items(lines, result, w)
            lines.append("+" + "-" * (w - 2) + "+")

        lines.append("+" + "=" * (w - 2) + "+")
        return "\n".join(lines)

    @classmethod
    def _analyze_prompt_vs_plan(
        cls, lines: list[str], result: PipelineResult, w: int
    ) -> None:
        """Compare what the user asked for vs what the plan produced."""
        prompt_lower = result.prompt.lower()

        # Extract intent keywords from prompt
        intent_keywords: list[str] = []
        keyword_map = {
            "time/schedule": ["every hour", "at midnight", "every day", "schedule",
                              "at night", "in the morning", "top of", "hourly",
                              "daily", "weekly"],
            "flash/blink": ["flash", "blink", "strobe", "flicker", "pulse"],
            "color": ["color", "rgb", "random color", "red", "blue", "green",
                       "warm", "cool", "colorful"],
            "brightness": ["bright", "dim", "brightness", "percent"],
            "count/repeat": ["times", "count", "repeat", "number of"],
            "duration": ["seconds", "secs", "minutes", "for 10", "for 5",
                          "for 30", "duration"],
            "presence/zone": ["leave", "arrive", "home", "away", "enter",
                               "presence", "zone"],
            "temperature": ["degrees", "thermostat", "temperature", "heat",
                             "cool", "hvac"],
            "light": ["light", "lamp", "bulb", "hue", "wled", "led"],
            "group/all": ["all lights", "all devices", "everything",
                           "each light", "every light"],
            "conditional": ["if", "when", "only when", "unless", "based on",
                             "depending", "24 hour", "hour clock", "am", "pm"],
        }

        for category, keywords in keyword_map.items():
            matches = [k for k in keywords if k in prompt_lower]
            if matches:
                intent_keywords.append(f"{category} ({', '.join(matches)})")

        lines.append(cls._row("  Detected intent keywords:", w))
        if intent_keywords:
            for ik in intent_keywords:
                lines.append(cls._row(f"    - {ik}", w))
        else:
            lines.append(cls._row("    (none detected)", w))

        # Check what the plan captured
        plan_step = next(
            (s for s in result.steps if s.name == StepName.INTENT_PLAN), None
        )
        if plan_step and plan_step.data:
            template_id = plan_step.data.get("template_id", "")
            params = plan_step.data.get("parameters", {})
            param_str = json.dumps(params, default=str).lower()

            lines.append(cls._row(f"  Template selected: {template_id}", w))
            lines.append(cls._row(f"  Parameters: {list(params.keys())}", w))

            # Gap analysis
            gaps: list[str] = []
            if any("flash" in k or "blink" in k for k in intent_keywords):
                if "flash" not in param_str and "blink" not in param_str:
                    gaps.append("Flash/blink intent detected but not in parameters")
            if any("color" in k for k in intent_keywords):
                if "color" not in param_str and "rgb" not in param_str:
                    gaps.append("Color intent detected but not in parameters")
            if any("count" in k or "repeat" in k for k in intent_keywords):
                if "count" not in param_str and "repeat" not in param_str and "times" not in param_str:
                    gaps.append("Count/repeat intent detected but not in parameters")
            if any("duration" in k for k in intent_keywords):
                if "duration" not in param_str and "second" not in param_str:
                    gaps.append("Duration intent detected but not in parameters")
            if any("conditional" in k for k in intent_keywords):
                if "condition" not in param_str and "hour" not in param_str:
                    gaps.append("Conditional/time-based logic detected but not in parameters")
            if any("time" in k or "schedule" in k for k in intent_keywords):
                if "schedule" not in param_str and "cron" not in param_str and "time" not in template_id:
                    gaps.append("Schedule intent detected but template may not be schedule-based")
            if any("presence" in k or "zone" in k for k in intent_keywords):
                if "presence" not in param_str and "zone" not in param_str and "presence" not in template_id:
                    gaps.append("Presence intent detected but not captured in plan")
            if any("group" in k or "all" in k for k in intent_keywords):
                if "group" not in param_str and "all" not in param_str:
                    gaps.append("Group/all-devices intent detected but not in parameters")
            if any("temperature" in k for k in intent_keywords):
                if "temperature" not in param_str and "degree" not in param_str:
                    gaps.append("Temperature value detected in prompt but not in parameters")

            if gaps:
                lines.append(cls._row("  GAPS (prompt intent not captured in plan):", w))
                for g in gaps:
                    lines.append(cls._row(f"    >> {g}", w))
            else:
                lines.append(cls._row("  No obvious gaps between prompt and plan.", w))
        else:
            lines.append(cls._row("  (No plan data available)", w))

    @classmethod
    def _inspect_yaml(
        cls, lines: list[str], result: PipelineResult, w: int
    ) -> None:
        """Deep inspection of generated YAML structure."""
        parsed = result.debug.parsed_yaml
        if not parsed or not isinstance(parsed, dict):
            lines.append(cls._row("  (No parseable YAML)", w))
            return

        # Top-level keys
        lines.append(cls._row(f"  Top-level keys: {list(parsed.keys())}", w))
        lines.append(cls._row(f"  mode: {parsed.get('mode', 'N/A')}", w))
        lines.append(cls._row(f"  alias: {parsed.get('alias', 'N/A')}", w))
        lines.append(cls._row(f"  description: {str(parsed.get('description', 'N/A'))[:w-20]}", w))

        # Trigger analysis
        trigger = parsed.get("trigger") or parsed.get("triggers")
        if trigger:
            triggers_list = trigger if isinstance(trigger, list) else [trigger]
            lines.append(cls._row(f"  Triggers ({len(triggers_list)}):", w))
            for i, t in enumerate(triggers_list):
                if isinstance(t, dict):
                    platform = t.get("platform", "unknown")
                    lines.append(cls._row(f"    [{i}] platform: {platform}", w))
                    for tk, tv in t.items():
                        if tk != "platform":
                            lines.append(cls._row(f"        {tk}: {tv!r}", w))
                else:
                    lines.append(cls._row(f"    [{i}] {t!r}", w))
        else:
            lines.append(cls._row("  Triggers: MISSING", w))

        # Action analysis
        action = parsed.get("action") or parsed.get("actions")
        if action:
            actions_list = action if isinstance(action, list) else [action]
            lines.append(cls._row(f"  Actions ({len(actions_list)}):", w))
            for i, a in enumerate(actions_list):
                if isinstance(a, dict):
                    service = a.get("service", a.get("action", "unknown"))
                    lines.append(cls._row(f"    [{i}] service: {service}", w))
                    target = a.get("target", {})
                    if target:
                        lines.append(cls._row(f"        target: {target}", w))
                    data = a.get("data", {})
                    if data:
                        lines.append(cls._row(f"        data: {data}", w))
                else:
                    lines.append(cls._row(f"    [{i}] {a!r}", w))
        else:
            lines.append(cls._row("  Actions: MISSING", w))

        # Condition analysis
        condition = parsed.get("condition") or parsed.get("conditions")
        if condition:
            conds_list = condition if isinstance(condition, list) else [condition]
            lines.append(cls._row(f"  Conditions ({len(conds_list)}):", w))
            for i, c in enumerate(conds_list):
                if isinstance(c, dict):
                    cond_type = c.get("condition", "unknown")
                    lines.append(cls._row(f"    [{i}] type: {cond_type}", w))
                    for ck, cv in c.items():
                        if ck != "condition":
                            lines.append(cls._row(f"        {ck}: {cv!r}", w))
                else:
                    lines.append(cls._row(f"    [{i}] {c!r}", w))
        else:
            lines.append(cls._row("  Conditions: none", w))

        # Unresolved placeholders
        yaml_str = result.debug.generated_yaml or ""
        placeholders = re.findall(r"\{\{[^}]+\}\}", yaml_str)
        if placeholders:
            unique_ph = sorted(set(placeholders))
            lines.append(cls._row(f"  Unresolved placeholders ({len(unique_ph)}):", w))
            for ph in unique_ph:
                lines.append(cls._row(f"    {ph}", w))

        # Entity references
        entity_refs = re.findall(
            r"\b(" + "|".join(KNOWN_DOMAINS) + r")\.\w+",
            yaml_str.lower(),
        )
        if entity_refs:
            unique_refs = sorted(set(entity_refs))
            lines.append(cls._row(f"  Entity references ({len(unique_refs)}):", w))
            for er in unique_refs:
                lines.append(cls._row(f"    {er}", w))
        else:
            lines.append(cls._row("  Entity references: NONE (uses placeholders only)", w))

    @classmethod
    def _build_action_items(
        cls, lines: list[str], result: PipelineResult, w: int
    ) -> None:
        """Build categorized action items from all findings."""
        findings: list[tuple[str, str, str]] = []  # (severity, category, finding)

        # --- Plan quality ---
        plan_step = next(
            (s for s in result.steps if s.name == StepName.INTENT_PLAN), None
        )
        if plan_step:
            if plan_step.status == StepStatus.FAIL:
                findings.append(("CRITICAL", "Plan", f"Plan endpoint failed: {plan_step.errors}"))
            elif plan_step.status == StepStatus.ERROR:
                findings.append(("CRITICAL", "Plan", f"Plan endpoint unreachable: {plan_step.errors}"))
            elif plan_step.data:
                conf = plan_step.data.get("confidence", 0)
                if conf < 0.5:
                    findings.append(("MEDIUM", "Plan", f"Low confidence ({conf}) --LLM unsure about template"))

        # --- Plan-vs-prompt gaps ---
        prompt_lower = result.prompt.lower()
        if plan_step and plan_step.data:
            params = plan_step.data.get("parameters", {})
            param_str = json.dumps(params, default=str).lower()
            template_id = plan_step.data.get("template_id", "")

            if "flash" in prompt_lower and "flash" not in param_str:
                findings.append(("HIGH", "Template", "Flash intent lost --template doesn't support flash parameters"))
            if ("every hour" in prompt_lower or "top of" in prompt_lower) and "hour" not in param_str:
                findings.append(("HIGH", "Template", "Hourly schedule intent not captured in parameters"))
            if ("number of times" in prompt_lower or "times of the hour" in prompt_lower) and "count" not in param_str:
                findings.append(("HIGH", "Template", "Dynamic count (based on hour) not captured --needs Jinja2 template logic"))
            if "24 hour" in prompt_lower and "24" not in param_str:
                findings.append(("HIGH", "Template", "24-hour clock logic not captured in parameters"))

            # Check for overly simple templates
            param_count = len(params)
            prompt_word_count = len(result.prompt.split())
            if prompt_word_count > 20 and param_count <= 3:
                findings.append(("MEDIUM", "Template",
                    f"Complex prompt ({prompt_word_count} words) mapped to simple template "
                    f"'{template_id}' with only {param_count} parameters"))

        # --- Compile quality ---
        compile_step = next(
            (s for s in result.steps if s.name == StepName.YAML_COMPILE), None
        )
        if compile_step and compile_step.status == StepStatus.FAIL:
            findings.append(("CRITICAL", "Compile", f"YAML compilation failed: {compile_step.errors}"))

        # --- Validation issues ---
        if result.debug.validation_errors:
            for err in result.debug.validation_errors:
                severity = "HIGH" if "must be" in err.lower() else "MEDIUM"
                findings.append((severity, "Validation", err))

        # --- YAML placeholders ---
        yaml_str = result.debug.generated_yaml or ""
        placeholders = set(re.findall(r"\{\{[^}]+\}\}", yaml_str))
        if placeholders:
            findings.append(("HIGH", "YAML",
                f"Unresolved placeholders ({len(placeholders)}): {', '.join(sorted(placeholders))} "
                "— compile step should resolve these to real entity/area IDs"))

        # --- Invalid entities ---
        if result.debug.validation_warnings:
            for wrn in result.debug.validation_warnings:
                if "invalid entity" in wrn.lower() or "unknown" in wrn.lower():
                    findings.append(("MEDIUM", "Entities", wrn))

        # --- Trigger/action format ---
        if result.debug.parsed_yaml:
            trigger = result.debug.parsed_yaml.get("trigger")
            action = result.debug.parsed_yaml.get("action")
            if trigger and not isinstance(trigger, list):
                findings.append(("HIGH", "YAML Format",
                    "trigger is a dict --HA 2024.x+ requires trigger to be a list"))
            if action and not isinstance(action, list):
                findings.append(("HIGH", "YAML Format",
                    "action is a dict --HA 2024.x+ requires action to be a list"))

        # --- Data as string instead of dict ---
        if result.debug.parsed_yaml:
            actions = result.debug.parsed_yaml.get("action") or result.debug.parsed_yaml.get("actions")
            if actions:
                a_list = actions if isinstance(actions, list) else [actions]
                for a in a_list:
                    if isinstance(a, dict) and isinstance(a.get("data"), str):
                        findings.append(("HIGH", "YAML Format",
                            f"action.data is a string '{a['data'][:60]}' --must be a YAML mapping"))

        # --- Missing action items if no findings ---
        if not findings:
            lines.append(cls._row("  No issues found --pipeline working correctly!", w))
            return

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        findings.sort(key=lambda f: severity_order.get(f[0], 99))

        # Group by category
        prev_severity = ""
        for i, (severity, category, finding) in enumerate(findings, 1):
            if severity != prev_severity:
                lines.append(cls._row(f"  [{severity}]", w))
                prev_severity = severity
            for chunk in cls._wrap(f"{i}. [{category}] {finding}", w - 10):
                lines.append(cls._row(f"    {chunk}", w))

    @staticmethod
    def _row(text: str, width: int) -> str:
        """Left-align text inside box borders."""
        inner = width - 4  # "| " + content + " |"
        return f"| {text:<{inner}s} |"

    @staticmethod
    def _wrap(text: str, max_width: int) -> list[str]:
        """Simple word-wrap for long text."""
        if len(text) <= max_width:
            return [text]
        chunks = []
        while text:
            if len(text) <= max_width:
                chunks.append(text)
                break
            # Find last space before max_width
            cut = text.rfind(" ", 0, max_width)
            if cut <= 0:
                cut = max_width
            chunks.append(text[:cut])
            text = text[cut:].lstrip()
        return chunks


# =========================================================================
# Utility
# =========================================================================

def _truncate(obj: Any, limit: int = 200) -> str:
    """Truncate a dict/string for error messages."""
    s = str(obj)
    return s[:limit] + "..." if len(s) > limit else s


# =========================================================================
# Pytest Tests
# =========================================================================

@pytest.mark.asyncio
class TestAskAIPipeline:
    """Parametrized pipeline tests using AskAITestHarness."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncGenerator[httpx.AsyncClient, None]:
        headers = {"X-HomeIQ-API-Key": DEFAULT_API_KEY}
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers) as c:
            yield c

    @pytest_asyncio.fixture
    async def harness(self, client: httpx.AsyncClient) -> AskAITestHarness:
        return AskAITestHarness(client=client)

    # -- Positive test cases -----------------------------------------------

    PROMPTS = [
        # (prompt, min_score, expected_domains, description)
        (
            "turn on the office lights",
            60,
            ["light"],
            "simple light control",
        ),
        (
            "set the thermostat to 72 degrees",
            50,
            ["climate"],
            "climate control",
        ),
        (
            "make it look like a party in the office by randomly flashing each "
            "lights quickly in random colors. Also include the Wled lights and "
            "pick fireworks. Do this for 10 secs",
            40,
            ["light"],
            "complex multi-device party mode",
        ),
        (
            "turn off all lights at midnight",
            50,
            ["light"],
            "time-based trigger",
        ),
        (
            "when I leave home turn off everything",
            40,
            None,
            "presence-based automation",
        ),
    ]

    @pytest.mark.parametrize(
        "prompt,min_score,expected_domains,description",
        PROMPTS,
        ids=[p[3] for p in PROMPTS],
    )
    async def test_pipeline(
        self,
        harness: AskAITestHarness,
        prompt: str,
        min_score: int,
        expected_domains: list[str] | None,
        description: str,
    ):
        result = await harness.run(
            prompt=prompt,
            deploy=False,
            expected_domains=expected_domains,
        )

        report = PipelineReportFormatter.format_report(result, verbose=True)
        logger.info("\n" + report)

        # Overall score meets minimum
        assert result.score.overall >= min_score, (
            f"Pipeline score {result.score.overall} < minimum {min_score} "
            f"for: {prompt!r}\n{result.summary}"
        )

        # Intent plan must succeed
        plan_step = next(
            (s for s in result.steps if s.name == StepName.INTENT_PLAN), None
        )
        assert plan_step is not None, "Intent plan step missing"
        assert plan_step.status == StepStatus.PASS, (
            f"Intent plan failed: {plan_step.errors}"
        )

    # -- Negative test cases -----------------------------------------------

    NEGATIVE_PROMPTS = [
        ("", "empty prompt"),
        ("asdfghjkl random nonsense xyz", "gibberish input"),
        ("what is the weather today?", "non-automation query"),
    ]

    @pytest.mark.parametrize(
        "prompt,description",
        NEGATIVE_PROMPTS,
        ids=[p[1] for p in NEGATIVE_PROMPTS],
    )
    async def test_pipeline_negative(
        self,
        harness: AskAITestHarness,
        prompt: str,
        description: str,
    ):
        """Negative tests --harness must not crash, result must be returned."""
        result = await harness.run(prompt=prompt, deploy=False)
        report = PipelineReportFormatter.format_report(result)
        logger.info("\n" + report)

        assert result is not None
        assert result.duration_ms > 0
        assert isinstance(result.score.overall, int)

    # -- Deployment test (opt-in) ------------------------------------------

    @pytest.mark.deploy
    async def test_pipeline_with_deploy(self, harness: AskAITestHarness):
        """Full pipeline with deployment. Run with: pytest -m deploy"""
        result = await harness.run(
            prompt="turn on the office lights",
            deploy=True,
        )
        report = PipelineReportFormatter.format_report(result, verbose=True)
        logger.info("\n" + report)

        assert result.score.overall >= 50, (
            f"Deploy pipeline score {result.score.overall} < 50\n{result.summary}"
        )

        # Cleanup must have run
        cleanup = next(
            (s for s in result.steps if s.name == StepName.CLEANUP), None
        )
        if cleanup:
            assert cleanup.status in (StepStatus.PASS, StepStatus.SKIP), (
                f"Cleanup failed: {cleanup.errors}"
            )


# =========================================================================
# CLI Entry Point
# =========================================================================

async def _cli_main() -> int:
    parser = argparse.ArgumentParser(
        description="Ask AI Pipeline Test Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python test_ask_ai_pipeline.py "turn on office lights" -v\n'
            '  python test_ask_ai_pipeline.py "party mode" --deploy --min-score 60\n'
            '  python test_ask_ai_pipeline.py "set thermostat" --json > result.json\n'
        ),
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="turn on the office lights",
        help='Prompt to test (default: "turn on the office lights")',
    )
    parser.add_argument("--deploy", action="store_true", help="Enable deployment step")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--diag", action="store_true",
        help="Full diagnostic report --API bodies, prompt-vs-plan analysis, YAML inspection, action items",
    )
    parser.add_argument("--base-url", default=None, help="API base URL override")
    parser.add_argument("--api-key", default=None, help="API key override")
    parser.add_argument(
        "--min-score", type=int, default=0, help="Minimum overall score to pass (exit 1 if below)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output result as JSON"
    )
    parser.add_argument(
        "--expected-domains",
        nargs="*",
        default=None,
        help='Expected HA domains (e.g. light climate)',
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Save report to file (e.g. reports/office-lights.txt)",
    )

    args = parser.parse_args()

    api_key = args.api_key or DEFAULT_API_KEY
    headers = {"X-HomeIQ-API-Key": api_key}
    base = args.base_url

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers) as client:
        harness = AskAITestHarness(client=client, base_url=base)
        result = await harness.run(
            prompt=args.prompt,
            deploy=args.deploy,
            expected_domains=args.expected_domains,
        )

    if args.json_output:
        output = json.dumps(asdict(result), indent=2, default=str)
    else:
        output = PipelineReportFormatter.format_report(
            result, verbose=args.verbose, diagnostic=args.diag,
        )

    # Save to file if --output specified
    if args.output:
        from pathlib import Path
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Report saved to: {out_path.resolve()}")
    else:
        # Ensure output is ASCII-safe for Windows cp1252 terminals
        try:
            print(output)
        except UnicodeEncodeError:
            print(output.encode("ascii", errors="replace").decode("ascii"))

    if args.min_score and result.score.overall < args.min_score:
        print(
            f"\nFAILED: Score {result.score.overall} < minimum {args.min_score}"
        )
        return 1

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_cli_main()))
