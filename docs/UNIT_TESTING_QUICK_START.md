# 🧪 Unit Testing Quick Start (In Transition)

The legacy HomeIQ unit testing framework was retired alongside the LangChain + PDL modernization (November 2025). This quick start guide now reflects the temporary gap while we build a leaner smoke/regression harness.

## 🚦 Current Reality

- Running `python scripts/simple-unit-tests.py` (or the shell/PowerShell wrappers) will simply exit after collecting **zero tests**.
- Historical coverage artefacts (`test-results/coverage/*`, `unit-test-report.html`) no longer exist.
- The massive `tests/` directory tree was deleted; only placeholder folders remain where Docker builds expect them.

## ✅ What You Can Do Today

1. **Manual Smoke Checks**
   - Launch the stack: `docker compose up -d`
   - Review service health: `docker compose ps` and the Health Dashboard (`http://localhost:3000`)
   - Exercise Ask AI / nightly analysis flows at `http://localhost:3001`

2. **Create Focused Scripts**
   - Place exploratory helpers under `scripts/` (e.g. `run_self_improvement_pilot.py`)
   - Document expected inputs/outputs inside the script

3. **Prototype New Tests**
   - Add service-specific tests next to the code they cover (e.g. `services/ai-automation-service/src/...`)
   - Include a TODO comment referencing the upcoming testing rebuild so they can be folded in later

## 🛠️ Rebuilding Roadmap

| Milestone | Description | Target |
|-----------|-------------|--------|
| **Smoke Harness** | Container health checks + critical HTTP endpoints | In progress |
| **LangChain/PDL Unit Tests** | Deterministic coverage for new pipelines | Planned |
| **Regression Fixtures** | YAML/PDL driven scenarios for nightly analysis | Planned |
| **Optional UI Smoke** | Minimal Playwright/Vitest checks | Deferred |

Progress will be tracked in [`docs/UNIT_TESTING_FRAMEWORK.md`](UNIT_TESTING_FRAMEWORK.md).

## 📣 Need Help?

- Open an issue using the “Testing Modernization” template.
- Ping the maintainers in Slack `#homeiq-dev`.
- Share manual test notes in `implementation/analysis/` (see `self_improvement_pilot_report.md` for a template).

---

Stay tuned—fresh testing instructions will return once the new harness lands. In the meantime, please avoid reviving the legacy framework; focus on targeted, high-signal checks instead.
