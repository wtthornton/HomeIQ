---
epic: auto-bugfix-cleanup-legacy
priority: high
status: open
estimated_duration: 2-3 days
risk_level: medium
source: Consolidate to config-driven framework; remove hardcoded legacy paths
type: cleanup
---

# Epic: Auto-Bugfix — Delete Legacy Code, Keep Config-Driven Framework Only

**Status:** Open  
**Priority:** P1 High  
**Duration:** 2–3 days  
**Risk Level:** Medium — breaking change for anyone running without `-ConfigPath`  
**Source:** Consolidate auto-bugfix pipeline to the config-driven framework; remove hardcoded legacy paths and deprecated entry points.

## Context

The auto-fix pipeline has two modes today:

1. **New (config-driven):** `.\auto-fix-pipeline\runner\run.ps1` or `.\scripts\auto-bugfix.ps1 -ConfigPath "auto-fix-pipeline/config/example/homeiq-default.yaml"`
2. **Old (legacy):** `.\scripts\auto-bugfix.ps1 -Bugs 3` (no `-ConfigPath` — uses hardcoded defaults)

Additionally, several alternate scripts exist (`auto-bugfix.sh`, `auto-bugfix.bat`, `auto-bugfix-overnight.ps1`, `auto-bugfix-parallel.ps1`, etc.) that may bypass the config framework or duplicate logic.

This epic removes the legacy path and deprecated scripts so only the config-driven framework remains.

## Goals

- Single entry point: runner or script with config (no hardcoded fallback).
- Remove alternate scripts that duplicate or bypass the config framework.
- Update all docs and references to use the new framework.

## Scope

- `scripts/auto-bugfix.ps1` — remove hardcoded fallback; require config (or default to homeiq-default.yaml).
- `scripts/auto-bugfix-stream.ps1` — **keep** (required by main script for streaming).
- Alternate entry points — remove or convert to thin wrappers that call the runner.
- Supporting scripts (scan-status, review-bugfix-pr, analyze-bug-history) — assess; keep if they don't duplicate pipeline logic.
- Documentation — update references to new entry points.

---

## Prerequisites

- Epic 50 (structure), Epics 1–4 (config, runner, script reads config, prompts) complete.
- **Story 0 must be complete before Story 2** — no deletion or replacement of alternate entry points until the config-driven framework is fully tested and verified.

---

## Stories

### Story 0: Full Testing of Config-Driven Framework (REQUIRED BEFORE Story 2)

**Priority:** P1 High | **Estimate:** 3h | **Risk:** Low  
**Prerequisite:** Must be complete before any deletion or replacement in Story 2.

**Problem:** The config-driven framework must be verified end-to-end before removing `auto-bugfix.sh` or other alternate scripts.

**Acceptance Criteria:**

- [ ] **Unit tests pass:** `python -m pytest tests/auto-fix-pipeline -v` — all 18 tests pass.
- [ ] **Config validation:** `homeiq-default.yaml` validates against `config-schema.json`; all prompt paths resolve to existing `.md` files.
- [ ] **Runner smoke test:** `.\auto-fix-pipeline\runner\run.ps1 -ConfigPath "auto-fix-pipeline/config/example/homeiq-default.yaml" -Bugs 1 -NoDashboard` completes without error (or exits cleanly if scan finds no bugs). Windows.
- [ ] **Script with -ConfigPath:** `.\scripts\auto-bugfix.ps1 -ConfigPath "auto-fix-pipeline/config/example/homeiq-default.yaml" -Bugs 1 -NoDashboard` completes without error. Windows.
- [ ] **End-to-end test (optional but recommended):** Run full pipeline with `-Bugs 1` or `-Bugs 3`; verify scan finds bugs (or retries correctly), fix phase runs, validation (TappsMCP) is invoked, PR created or pipeline completes. Document result in implementation notes.
- [ ] **Multi-repo runner (if used):** `.\auto-fix-pipeline\runner\run-multirepo.ps1 -ReposPath "auto-fix-pipeline/config/example/repos-example.yaml" -Bugs 1` completes without error.
- [ ] Test results and any failures documented in `implementation/`; blockers resolved before Story 2 proceeds.

---

### Story 1: Script Requires Config (No Hardcoded Fallback)

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Medium

**Problem:** `auto-bugfix.ps1` has ~60 lines of hardcoded defaults (lines 60–76) when `-ConfigPath` is omitted. This duplicates config and diverges from the schema.

**Acceptance Criteria:**

- [ ] When `-ConfigPath` is omitted, the script uses `$env:AUTO_FIX_CONFIG` if set; otherwise defaults to `auto-fix-pipeline/config/example/homeiq-default.yaml` (relative to project root).
- [ ] Remove the hardcoded fallback block (lines 60–76). All paths, manifest, budget, MCP, prompts come from config.
- [ ] If the default config path is used and the file does not exist, fail with a clear error (e.g., "Config not found: auto-fix-pipeline/config/example/homeiq-default.yaml. Set -ConfigPath or env:AUTO_FIX_CONFIG.").
- [ ] Existing `-ConfigPath` behavior unchanged.
- [ ] `.\scripts\auto-bugfix.ps1 -Bugs 3` runs using homeiq-default.yaml by default.

---

### Story 2: Remove Deprecated Alternate Entry Points

**Priority:** P1 High | **Estimate:** 1.5h | **Risk:** Low  
**Dependency:** Story 0 must be complete — full testing of config-driven framework verified before any deletion.

**Problem:** Several scripts provide alternate ways to run the pipeline without the config framework.

**Acceptance Criteria:**

- [ ] **Story 0 complete:** All config-driven framework tests pass; runner and script-with-config verified. Do not proceed until Story 0 is signed off.
- [ ] Remove or replace:
  - `scripts/auto-bugfix.sh` — Do not delete until Story 0 full testing is complete. Replace with a thin wrapper that invokes `scripts/auto-bugfix.ps1 -ConfigPath "auto-fix-pipeline/config/example/homeiq-default.yaml"` (or `pwsh -File scripts/auto-bugfix.ps1 -ConfigPath ...`) on Unix, or delete only after config-driven framework is verified equivalent; document decision.
  - `scripts/auto-bugfix.bat` — remove or replace with a wrapper that invokes the runner.
  - `scripts/auto-bugfix-overnight.ps1` — assess: if it’s a scheduling wrapper around the main script, refactor to use `-ConfigPath`; else remove if obsolete.
  - `scripts/auto-bugfix-parallel.ps1` and `scripts/auto-bugfix-parallel.sh` — assess: if multi-repo, use `run-multirepo.ps1`; otherwise remove.
- [ ] Document removals in CHANGELOG or implementation notes.
- [ ] No references in docs to deleted scripts.

---

### Story 3: Keep Runner as Preferred Entry Point

**Priority:** P2 Medium | **Estimate:** 1h | **Risk:** Low

**Problem:** Users may not know the runner exists; docs may favor the script directly.

**Acceptance Criteria:**

- [ ] README or auto-fix-pipeline docs state: preferred entry point is `.\auto-fix-pipeline\runner\run.ps1` (config-driven). Direct script `.\scripts\auto-bugfix.ps1` is supported with `-ConfigPath` or default config.
- [ ] `.\auto-fix-pipeline\runner\run.ps1 -Bugs 3` remains the primary documented example.
- [ ] `scripts/auto-bugfix.ps1` usage in docs includes `-ConfigPath` or mentions the default config path.

---

### Story 4: Update Documentation References

**Priority:** P1 High | **Estimate:** 1.5h | **Risk:** Low

**Problem:** Multiple docs reference old usage patterns.

**Acceptance Criteria:**

- [ ] Update these (or equivalents) to use the new framework:
  - `implementation/AGENT_HANDOFF_AUTO_FIX_PIPELINE.md`
  - `auto-fix-pipeline/docs/adoption-and-breakout.md`
  - `auto-fix-pipeline/runner/README.md`
  - `docs/workflows/auto-bugfix-subagents.md`
  - `.cursor/MCP_SETUP_INSTRUCTIONS.md`
  - Any CI or run scripts that invoke auto-bugfix.
- [ ] Remove or update references to `-Bugs 3` without `-ConfigPath` as the default usage.
- [ ] No doc suggests running `auto-bugfix.ps1` without config.

---

### Story 5: Supporting Scripts Assessment

**Priority:** P2 Medium | **Estimate:** 1h | **Risk:** Low

**Problem:** `scan-status.ps1`, `review-bugfix-pr.ps1`, `analyze-bug-history.ps1` may have hardcoded paths.

**Acceptance Criteria:**

- [ ] Review each script for hardcoded paths (dashboard state, history file, etc.).
- [ ] If they read pipeline artifacts (e.g., `scripts/.dashboard-state.json`, `docs/BUG_HISTORY.json`), ensure paths match `paths` in homeiq-default.yaml or accept a config path.
- [ ] Document any path assumptions; prefer reading from config when feasible.
- [ ] No removal required if they only consume outputs; update if they hardcode pipeline paths.

---

## Summary

| Story | Focus | Priority | Est. | Order |
|-------|--------|----------|------|-------|
| **0** | **Full testing of config-driven framework** (blocker for Story 2) | P1 | 3h | **First** |
| 1 | Script requires config; remove hardcoded fallback | P1 | 2h | After 0 |
| 2 | Remove deprecated alternate entry points | P1 | 1.5h | **After 0** (must pass full test) |
| 3 | Runner as preferred entry point in docs | P2 | 1h | After 1 |
| 4 | Update documentation references | P1 | 1.5h | After 2 |
| 5 | Supporting scripts assessment | P2 | 1h | After 4 |
| **Total** | | | **~10h** | |

## Execution Order

1. **Story 0** — Full testing of config-driven framework. Must complete and sign off before Story 2.
2. **Story 1** — Make script require config (remove hardcoded fallback).
3. **Story 2** — Remove/replace alternate entry points (blocked until Story 0 passes).
4. **Stories 3–5** — Docs, runner as preferred, supporting scripts.

## Dependencies

- Epic 50 (structure) complete.
- Epics 1–4 (config, runner, script reads config, prompts) complete.
- **Story 0 must pass before Story 2** — no deletion or replacement of auto-bugfix.sh until config-driven framework is fully tested and verified.

## References

- [auto-fix-pipeline/README.md](../auto-fix-pipeline/README.md)
- [auto-fix-pipeline/runner/README.md](../auto-fix-pipeline/runner/README.md)
- [implementation/AGENT_HANDOFF_AUTO_FIX_PIPELINE.md](../implementation/AGENT_HANDOFF_AUTO_FIX_PIPELINE.md)
