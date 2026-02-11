"""
Ask AI Pipeline Test Harness — Reusable E2E Testing, Scoring & Debugging

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

    Not tied to pytest — can be used from CLI, other tests, or scripts.
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

        Pipeline: Plan → Evaluate → Clarification → Compile → Validate → Analyse → Deploy

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

            # --- Step 4: YAML Compile (deterministic, no LLM) ---
            yaml_content: str | None = None
            if plan_data:
                compile_data = await self._step_yaml_compile(plan_data)
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
        Never raises — returns (0, None, duration) on connection error.
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
            logger.warning(f"API call timeout: {method} {url} — {exc}")
        except httpx.ConnectError as exc:
            error = f"Connection refused: {exc}"
            logger.warning(f"API connection error: {method} {url} — {exc}")
        except Exception as exc:
            error = f"Unexpected error: {exc}"
            logger.warning(f"API call error: {method} {url} — {exc}")

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
                # the plan data in the error message — extract what we can
                detail = str(body.get("detail", ""))
                step.status = StepStatus.FAIL
                step.errors.append(f"API returned 500: {_truncate(body)}")

                # Check if it's a known DB migration issue
                if "no such table" in detail.lower():
                    step.warnings.append(
                        "DB table missing — plan endpoint needs migration. "
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
    # Step 4: YAML Compile (deterministic)
    # ------------------------------------------------------------------

    async def _step_yaml_compile(self, plan_data: dict) -> dict | None:
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
            "resolved_context": {},
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

                # Validation score (0-100 → 0-10 contribution)
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
                # Validation endpoint may not be deployed — treat as warning
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
            score += 8  # Partial credit — simple automations often have no conditions
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
        ps.entity_extraction = self._dim_from_step(StepName.PLAN_EVALUATION)
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

    W = 72  # Report width

    @classmethod
    def format_report(cls, result: PipelineResult, verbose: bool = False) -> str:
        lines: list[str] = []
        w = cls.W

        lines.append("+" + "=" * (w - 2) + "+")
        lines.append(cls._row("ASK AI PIPELINE TEST RESULTS", w))
        lines.append("+" + "=" * (w - 2) + "+")

        # Prompt (wrap if long)
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

        # Score dimensions
        lines.append(cls._row("SCORES", w))
        for dim_name in [
            "entity_extraction", "suggestion_quality", "yaml_validity",
            "yaml_completeness", "pipeline_reliability",
        ]:
            dim: ScoreDimension = getattr(result.score, dim_name)
            label = dim_name.replace("_", " ").title()
            lines.append(cls._row(f"  {label:.<30s} {dim.score:>3d}/100", w))
        lines.append("+" + "-" * (w - 2) + "+")

        # Steps
        lines.append(cls._row("STEPS", w))
        for step in result.steps:
            icon = cls.STEP_ICONS.get(step.status, "[????]")
            name = step.name.value
            if step.status == StepStatus.SKIP:
                lines.append(cls._row(f"  {icon} {name}", w))
            else:
                dur = f"({step.duration_ms / 1000:.1f}s)" if step.duration_ms else ""
                sc = f"Score: {step.score}" if step.score is not None else ""
                lines.append(cls._row(
                    f"  {icon} {name:<24s} {dur:>7s}  {sc}", w
                ))
        lines.append("+" + "-" * (w - 2) + "+")

        # Entities
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

        # Entity Mapping (from YAML generation quality report)
        if result.debug.entity_mapping:
            lines.append(cls._row("ENTITY MAPPING (device -> entity_id)", w))
            for device, eid in result.debug.entity_mapping.items():
                lines.append(cls._row(f"  {device} -> {eid}", w))
            lines.append("+" + "-" * (w - 2) + "+")

        # Issues
        all_issues: list[str] = []
        for step in result.steps:
            for issue in getattr(step, "issues", []):
                all_issues.append(f"({step.name.value}) {issue}")
            for err in step.errors:
                all_issues.append(f"({step.name.value}) ERROR: {err}")
        if all_issues:
            lines.append(cls._row("ISSUES", w))
            for issue in all_issues[:20]:
                lines.append(cls._row(f"  (!) {issue[:w - 10]}", w))
            lines.append("+" + "-" * (w - 2) + "+")

        # Warnings
        all_warnings: list[str] = []
        for step in result.steps:
            for warn in step.warnings:
                all_warnings.append(f"({step.name.value}) {warn}")
        if all_warnings:
            lines.append(cls._row("WARNINGS", w))
            for warn in all_warnings[:10]:
                lines.append(cls._row(f"  (~) {warn[:w - 10]}", w))
            lines.append("+" + "-" * (w - 2) + "+")

        # Verbose sections
        if verbose:
            # Generated YAML
            if result.debug.generated_yaml:
                lines.append(cls._row("GENERATED YAML", w))
                yaml_lines = result.debug.generated_yaml.split("\n")
                for yl in yaml_lines[:80]:
                    lines.append(cls._row(f"  {yl[:w - 6]}", w))
                if len(yaml_lines) > 80:
                    lines.append(cls._row(
                        f"  ... ({len(yaml_lines) - 80} more lines)", w
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

        lines.append("+" + "=" * (w - 2) + "+")
        return "\n".join(lines)

    @staticmethod
    def _row(text: str, width: int) -> str:
        """Left-align text inside box borders."""
        inner = width - 4  # "| " + content + " |"
        return f"| {text:<{inner}s} |"


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
        """Negative tests — harness must not crash, result must be returned."""
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
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        report = PipelineReportFormatter.format_report(result, verbose=args.verbose)
        print(report)

    if args.min_score and result.score.overall < args.min_score:
        print(
            f"\nFAILED: Score {result.score.overall} < minimum {args.min_score}"
        )
        return 1

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_cli_main()))
