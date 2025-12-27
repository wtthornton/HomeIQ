# HomeIQ Testing Status (November 2025)

> **Important:** The legacy unit testing framework and its accompanying multi-language suites were retired during the LangChain + PDL modernization work. This document now tracks the temporary gap and the plan for reinstating automated coverage.

## 🎯 Current State

- ✅ Legacy Python and TypeScript test trees have been removed from the repository.
- ✅ Docker images that previously copied `tests/` now use lightweight placeholders (for example `services/ai-automation-service/tests/` exists but is empty).
- ❌ `scripts/run-unit-tests.py`, `run-unit-tests.sh`, `run-unit-tests.ps1`, and historical coverage artifacts no longer reflect the codebase and should be considered deprecated.
- ❌ No automated regression, smoke, or unit suites are available at this time.

## 🤔 Why the Change?

1. **Stale Coverage:** The old suites referenced modules, mocks, and dependency graphs that no longer exist after the LangChain/PDL refactor.
2. **False Confidence:** Maintaining broken tests masked real integration issues and slowed local development.
3. **Simplification:** Deleting obsolete scaffolding unblocked Docker builds, reduced repository size, and clarified the path toward targeted modern tests.

## 🗺️ Rebuild Plan

| Phase | Goal | Notes |
|-------|------|-------|
| **1. Smoke Tests** | Verify containers start, health checks respond, and feature flags toggle correctly. | Uses `docker compose` plus lightweight HTTP assertions. |
| **2. Critical Path Unit Tests** | Cover Ask AI prompt building, LangChain chains, and PDL interpreter helpers. | Focus on pure functions and deterministic behaviours. |
| **3. Regression & Fixtures** | Reintroduce data-driven scenarios for nightly analysis and synergy detectors. | Leverage new fixtures that mirror YAML/PDL inputs. |
| **4. Optional UI Checks** | Small number of Playwright/Vitest smoke checks for the dashboard and automation UI. | Scope intentionally limited to keep CI fast. |

## 🧪 Working With Tests Today

- **Manual Verification:** Use the Health Dashboard (`http://localhost:3000`) and AI Automation UI (`http://localhost:3001`) as the primary validation surfaces after changes.
- **Targeted Scripts:** For exploratory testing, create ad-hoc utilities under `scripts/` (e.g. `run_self_improvement_pilot.py`) rather than reviving the removed harness.
- **Prototyping New Tests:** If you build new tests, place them alongside the relevant module (for example `services/ai-automation-service/src/...`) and document the new structure so it can be lifted into the upcoming framework.
- **Coverage Tools:** Do **not** rely on the historical `test-results/` directory; it will be regenerated once the new suites land.

## 📌 Interim Guidelines

- Prefer **functional smoke checks** over broad snapshot tests; keep runtime under one minute.
- Guard new LangChain/PDL functionality with **feature flags** and, where practical, add locally runnable assertions before pushing changes.
- When adding a test file, include a short comment block explaining the expected future location in the rebuilt hierarchy.
- Update this document as soon as new automated coverage is introduced so downstream contributors stay aligned.

## 📚 Related Resources

- [`docs/current/operations/langchain-pdl-runtime.md`](../docs/current/operations/langchain-pdl-runtime.md) – operational guidance for LangChain/PDL rollouts.
- [`implementation/analysis/self_improvement_pilot_report.md`](../implementation/analysis/self_improvement_pilot_report.md) – example of manual verification output.
- [`docker-compose.yml`](../docker-compose.yml) – reference for service health checks that future smoke tests can reuse.

---

Need clarity on where to start when rebuilding the test suite? Message the maintainers in Slack `#homeiq-dev` or open an issue using the “Testing Modernization” template.