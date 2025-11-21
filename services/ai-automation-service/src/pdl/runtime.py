"""
Minimal PDL (Procedure Description Language) interpreter.

The interpreter reads YAML scripts that define guards and informational steps.
It does not attempt to replace the existing Python orchestration; instead, it
provides an auditable checklist that runs in parallel, confirming that required
preconditions hold before the scheduler executes critical logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class StepResult:
    step_id: str
    status: str
    message: str


class PDLExecutionError(RuntimeError):
    """Raised when a guard configured with `on_failure=error` fails."""


class PDLInterpreter:
    """Load and execute lightweight PDL scripts."""

    def __init__(self, script: dict[str, Any], logger: logging.Logger):
        self._script = script
        self._logger = logger

    @classmethod
    def from_file(cls, path: Path, logger: logging.Logger) -> PDLInterpreter:
        if not path.exists():
            msg = f"PDL script not found: {path}"
            raise FileNotFoundError(msg)
        with path.open("r", encoding="utf-8") as handle:
            script = yaml.safe_load(handle) or {}
        return cls(script, logger)

    async def run(self, context: dict[str, Any]) -> list[StepResult]:
        steps = self._script.get("steps", [])
        name = self._script.get("name", "unnamed")
        self._logger.info("📜 Executing PDL script '%s' (%d steps)", name, len(steps))

        results: list[StepResult] = []
        for step in steps:
            step_id = step.get("id", "unknown-step")
            step_type = step.get("type", "info")
            message = step.get("message", "")
            on_failure = step.get("on_failure", "warn")

            if step_type == "info":
                self._logger.info("📝 [%s] %s", step_id, message)
                results.append(StepResult(step_id, "info", message))
                continue

            if step_type == "guard":
                condition = step.get("condition")
                ok, reason = self._evaluate_condition(condition, context)

                if ok:
                    self._logger.info("✅ [%s] Guard satisfied%s", step_id, f": {reason}" if reason else "")
                    results.append(StepResult(step_id, "passed", reason or message))
                    continue

                failure_msg = reason or message or "Guard condition failed."
                if on_failure == "error":
                    self._logger.error("❌ [%s] %s", step_id, failure_msg)
                    msg = f"{step_id}: {failure_msg}"
                    raise PDLExecutionError(msg)
                self._logger.warning("⚠️ [%s] %s", step_id, failure_msg)
                results.append(StepResult(step_id, "warn", failure_msg))
                continue

            # Default fall-through (unknown step type)
            self._logger.debug("ℹ️ [%s] Skipping unsupported step type '%s'", step_id, step_type)
            results.append(StepResult(step_id, "skipped", f"Unsupported type {step_type}"))

        return results

    def _evaluate_condition(self, condition: Any, context: dict[str, Any]) -> tuple[bool, str | None]:
        """Evaluate guard condition using a restricted set of operators."""
        if condition is None:
            return False, "Guard missing condition."

        if isinstance(condition, str):
            value = context.get(condition)
            return bool(value), f"{condition}={value}"

        if isinstance(condition, dict):
            if "all_of" in condition:
                results = [self._evaluate_condition(item, context)[0] for item in condition["all_of"]]
                return all(results), "all_of check"
            if "any_of" in condition:
                results = [self._evaluate_condition(item, context)[0] for item in condition["any_of"]]
                return any(results), "any_of check"
            if "equals" in condition:
                left, right = condition["equals"]
                return self._resolve(left, context) == self._resolve(right, context), "equals check"
            if "less_or_equal" in condition:
                left, right = condition["less_or_equal"]
                return self._resolve(left, context) <= self._resolve(right, context), "less_or_equal check"
            if "greater_or_equal" in condition:
                left, right = condition["greater_or_equal"]
                return self._resolve(left, context) >= self._resolve(right, context), "greater_or_equal check"

        return False, "Unsupported condition structure."

    def _resolve(self, value: Any, context: dict[str, Any]) -> Any:
        if isinstance(value, str) and value in context:
            return context[value]
        return value


