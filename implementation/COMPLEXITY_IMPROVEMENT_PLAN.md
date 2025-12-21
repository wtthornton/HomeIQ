# Complexity Metric Improvement Plan (HomeIQ)

**Date:** 2025-12-20  
**Source of truth:** `reports/quality/quality-report.json` (generated via `python -m tapps_agents.cli reviewer report . all --output-dir reports/quality`)

## Important clarification (what “increase complexity number” means)

In the quality report, **Complexity = 2.06/10** with a threshold of **< 5.0** (pass).  
That means **higher “complexity” is worse** (more cyclomatic complexity).  

So the way to *improve the complexity metric / “score”* is to **reduce** real code complexity hotspots and/or remove noise (generated/backup files) that inflate complexity.

If you truly meant “make the code more complex”, that would degrade quality and is not recommended.

## Current baseline

- **Complexity:** 2.06/10 ✅ (threshold < 5.0)
- **Overall:** 78.52/100 ✅
- **Files analyzed:** 500

## Primary targets (highest complexity from latest report)

From the report’s “Top by complexity” list:

- `tools/ask-ai-continuous-improvement.py` (10.00)
- `tools/ask-ai-continuous-improvement-unit-test.py` (10.00)
- `scripts/prepare_for_production.py` (10.00)
- `scripts/check_influxdb_quality.py` (10.00)
- `scripts/check_database_quality.py` (10.00)
- `TappsCodingAgents/tapps_agents/cli/main.py` (9.20)
- `simulation/cli.py` (8.80)
- `scripts/review_databases.py` (8.80)
- `scripts/fetch_suggestion_debug_data.py` (7.20)

Also present (likely noise):

- `TappsCodingAgents/test_feature.py` and many `TappsCodingAgents/test_feature.backup_*.py` (10.00)
  - These appear to be **temporary/backup artifacts** and are high-leverage to remove or exclude from quality analysis.

## Goal

Reduce complexity hotspots and analysis noise to push:

- **Complexity metric** from **2.06/10 → ≤ 1.75/10** (stretch)  
  (or at minimum: eliminate the 10.00 offenders that are not core product code)
- Keep **Overall score ≥ 78.5**, ideally improve it

## Strategy (fastest impact first)

### Phase 0 — Remove “analysis noise” (fastest win)

**Why:** Backup/experimental files can dominate “top offenders” without helping the product.

Actions:

- Identify any obviously-temporary Python artifacts in the repo:
  - `**/*.backup_*.py`
  - `**/test_feature*.py` (if not a real test)
  - one-off experiment scripts that aren’t part of supported tooling
- Decide one of:
  - **Delete** them (preferred if truly unused)
  - **Move** them under an archive or tooling sandbox (if you want to keep them)
  - **Exclude** them from quality analysis (if they must remain)

Acceptance criteria:

- Re-run report and confirm those files are no longer counted in “Top by complexity”.

Verification command (PowerShell):

```powershell
cd C:\cursor\HomeIQ
python -m tapps_agents.cli reviewer report . all --output-dir reports/quality
```

### Phase 1 — Refactor the 10.00 “operational scripts”

These scripts tend to accumulate:
- large functions
- deep `if/elif` chains
- repeated error handling + logging patterns
- mixed concerns (CLI parsing + orchestration + IO + business rules)

General refactor playbook (applies to each target file):

- **Extract phases into functions**:
  - e.g., `validate_env()`, `build()`, `deploy()`, `run_smoke_tests()`, `generate_data()`, etc.
- **Replace deep branching with dispatch tables**:
  - `dict[str, Callable]` mapping command/component → handler
- **Create small dataclasses for config/state**:
  - reduces “parameter soup” and clarifies intent
- **Pull repeated “run subprocess + handle errors” logic into helpers**
- **Limit function size**:
  - target ≤ ~60 lines per function for orchestration code

#### 1A. `scripts/prepare_for_production.py` (10.00)

Likely contributors:
- multi-step orchestration
- repeated validation logic
- complex flow control around “critical vs optional”

Concrete plan:

- Create `scripts/production_readiness/` package with:
  - `config.py` (thresholds, component lists)
  - `steps.py` (one function per step)
  - `runner.py` (orchestrates steps, handles timing/reporting)
- Keep `scripts/prepare_for_production.py` as a thin CLI wrapper calling `runner.run(args)`

#### 1B. `scripts/check_database_quality.py` and `scripts/check_influxdb_quality.py` (10.00)

Concrete plan:

- Consolidate shared DB-check utilities into `scripts/quality_checks/db_common.py`
- Extract individual checks into dedicated functions:
  - `check_indexes()`, `check_foreign_keys()`, `check_vacuum()`, etc.
- Add `--checks` filter with a dispatch table to run only selected checks (simplifies control flow)

#### 1C. `tools/ask-ai-continuous-improvement*.py` (10.00)

Concrete plan:

- Split into modules by concern:
  - API client
  - scoring/evaluation
  - prompt set definitions
  - reporting/output formatting
  - orchestration loop
- Move large constant lists (e.g., `TARGET_PROMPTS`) into separate data module

### Phase 2 — Refactor `TappsCodingAgents/tapps_agents/cli/main.py` (9.20)

Concrete plan:

- Reduce repetitive imports and parser wiring by using:
  - a single registry list of `(name, register_fn)` pairs
  - a loop to register parsers
- Move long `description`/`epilog` strings into a separate module or constants section

### Phase 3 — Re-measure and lock in improvements

After each phase:

- Re-run the report
- Compare complexity before/after
- Record the delta in a short note (optional)

Verification commands (PowerShell):

```powershell
cd C:\cursor\HomeIQ
python -m tapps_agents.cli reviewer analyze-project --format json
python -m tapps_agents.cli reviewer report . all --output-dir reports/quality
```

## Risks / gotchas

- Refactoring scripts can break “one-off” local workflows; mitigate by adding lightweight smoke tests or a `--dry-run` mode.
- Excluding files from analysis improves the metric but can hide real problems; only exclude **generated/backup** artifacts.

## Definition of done

- Complexity metric improves (lower is better) and remains **well under 5.0**.
- The “Top by complexity” list no longer contains obvious backup artifacts.
- Key operational scripts are split into smaller, testable functions/modules.
- Re-run `reviewer report` succeeds and produces updated `reports/quality/` artifacts.


