"""
Automation Linter Client for AI Automation Service

Epic 67, Story 67.1: Validation Client Integration
Calls automation-linter POST /lint to validate generated YAML.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx
from homeiq_resilience import CircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)

# Shared circuit breaker for automation-linter calls
_linter_breaker = CircuitBreaker(name="automation-linter")


@dataclass
class LintFinding:
    """A single lint finding from the automation linter."""

    rule_id: str
    severity: str
    message: str
    path: str | None = None
    suggested_fix: dict[str, str] | None = None


@dataclass
class LintResult:
    """Result from automation linter validation."""

    passed: bool
    findings: list[LintFinding] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    raw_response: dict[str, Any] | None = None


class LinterClient:
    """Client for automation-linter POST /lint endpoint.

    Uses CircuitBreaker from homeiq-resilience to handle service unavailability.
    """

    def __init__(
        self,
        base_url: str = "http://automation-linter:8020",
        timeout: float = 2.0,
    ):
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        logger.info("LinterClient initialized: base_url=%s, timeout=%.1fs", self.base_url, timeout)

    async def lint(self, yaml_content: str) -> LintResult:
        """Lint automation YAML via automation-linter service.

        Args:
            yaml_content: The YAML string to validate.

        Returns:
            LintResult with pass/fail status and findings.

        Raises:
            CircuitOpenError: If the circuit breaker is open.
            Exception: On network/HTTP errors (after circuit breaker check).
        """
        try:
            async with _linter_breaker:
                response = await self._client.post(
                    f"{self.base_url}/lint",
                    json={"yaml": yaml_content},
                )
                response.raise_for_status()

                data = response.json()
                summary = data.get("summary", {})
                error_count = summary.get("errors_count", 0)
                warning_count = summary.get("warnings_count", 0)
                info_count = summary.get("info_count", 0)

                findings = [
                    LintFinding(
                        rule_id=f.get("rule_id", ""),
                        severity=f.get("severity", "info"),
                        message=f.get("message", ""),
                        path=f.get("path"),
                        suggested_fix=f.get("suggested_fix"),
                    )
                    for f in data.get("findings", [])
                ]

                passed = error_count == 0
                logger.info(
                    "Lint result: passed=%s, errors=%d, warnings=%d, info=%d",
                    passed, error_count, warning_count, info_count,
                )

                return LintResult(
                    passed=passed,
                    findings=findings,
                    error_count=error_count,
                    warning_count=warning_count,
                    info_count=info_count,
                    raw_response=data,
                )

        except CircuitOpenError:
            logger.warning("AI FALLBACK: automation-linter circuit open — skipping lint")
            raise
        except httpx.TimeoutException:
            logger.warning("AI FALLBACK: automation-linter timed out after %.1fs", self._timeout)
            raise
        except httpx.HTTPStatusError as e:
            logger.error("Linter HTTP error: %s %s", e.response.status_code, e.response.text[:200])
            raise
        except Exception as e:
            logger.error("Linter error: %s", e)
            raise

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
