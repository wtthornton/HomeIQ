# Recommended Next Steps (After Epic 0)

**Epic 0:** Structure setup — Complete (Executed).  
**Epic 1:** Config schema and HomeIQ default — Complete (schema in `config/schema/`, example `config/example/homeiq-default.yaml`).  
**Epic 2:** Runner reads config and delegates — Complete (`runner/run.ps1` invokes script with `-ConfigPath`).  
**Epic 3:** Script reads config — Complete (`auto-bugfix.ps1 -ConfigPath` loads YAML for paths, manifest, runner, MCP, scan; backward compatible when omitted).  
**Epic 4:** Externalize prompts — Complete (templates in `config/prompts/` with placeholders; script loads when `config.prompts` is set; built-in prompts unchanged when omitted).  
**Goal:** Develop and test the generalized pipeline here, then move out to its own repo.

---

## 1. Epic 1: Config schema and HomeIQ default (Phase 1 — Extract config)

**Scope:** Define the pipeline config in the isolated project; keep existing script behavior unchanged.

- Add **config schema** in `auto-fix-pipeline/config/schema/` (e.g. JSON Schema or documented YAML shape for project, runner, scan, fix, mcp, paths, prompts).
- Add **example config** in `auto-fix-pipeline/config/example/` that matches current HomeIQ behavior (paths, manifest, MCP_DOCKER tool prefix, budget allocation).
- Optionally: add a **HomeIQ default** — either a copy at repo root (e.g. `auto-fix-pipeline/config/example/homeiq-default.yaml`) or document “current defaults” in the schema so the existing script can later be refactored to read from config.
- **Do not** change `scripts/auto-bugfix.ps1` behavior yet; this epic is config-only so the schema can be tested and reviewed.

**Outcome:** Config is the single source of truth for “what the pipeline supports”; HomeIQ’s current behavior is expressible as that config.

---

## 2. Epic 2: Runner reads config and delegates (Phase 1 completion + Phase 3 start)

**Scope:** Generic runner inside `auto-fix-pipeline/runner/` that reads config and invokes the existing pipeline.

- Implement a **runner entrypoint** (e.g. PowerShell or script) in `auto-fix-pipeline/runner/` that:
  - Loads config from a path (e.g. `auto-fix-pipeline/config/example/homeiq-default.yaml` or `$env:AUTO_FIX_CONFIG`).
  - Resolves project root, paths, and MCP server name from config.
  - Calls the **existing** `scripts/auto-bugfix.ps1` (or stream module) with parameters derived from config (or passes config path so the script can read it in a later epic).
- HomeIQ continues to work as today: `scripts/auto-bugfix.ps1` remains the main script; the new runner is an alternative entrypoint that “wires” config to the current script.
- Add a short **README** in `runner/` describing how to run via the runner and how it relates to `scripts/auto-bugfix.ps1`.

**Outcome:** Pipeline can be driven by config from the isolated project; behavior still implemented by existing script. Validates config shape and integration without refactoring the script yet.

---

## 3. Epic 3: Script reads config (Phase 1 — refactor script)

**Scope:** Refactor `scripts/auto-bugfix.ps1` to read paths, manifest, model, budget, and MCP tool prefix from config when a config path is provided (e.g. `-ConfigPath auto-fix-pipeline/config/example/homeiq-default.yaml`); fallback to current hardcoded defaults when no config.

- Add optional parameter `-ConfigPath` to `auto-bugfix.ps1`.
- When `-ConfigPath` is set, load YAML and use config for: project root (or keep script-path derivation), paths (dashboard, feedback, history, impl_dir), scan manifest path, runner (model, max_cost, budget_allocation), MCP (config_path, tapps_mcp_server → tool prefix), scan (retry_attempts, output_format).
- When `-ConfigPath` is not set, behavior is unchanged (backward compatible).
- Run at least one full pipeline with `-ConfigPath` against the HomeIQ default config and confirm identical behavior.

**Outcome:** Single repo (HomeIQ) runs the pipeline from config; no change for users who don’t pass `-ConfigPath`.

---

## 4. Epic 4: Externalize prompts (Phase 2)

**Scope:** Move find/retry/fix/refactor/test/feedback prompts from inline strings to template files under `auto-fix-pipeline/` (e.g. `docs/workflows/` or `config/prompts/`), with placeholders (`{{project_name}}`, `{{languages}}`, `{{scope_hint}}`, `{{allowed_tools}}`, `{{bug_count}}`). Runner or script loads templates and substitutes from config. Keep default templates so HomeIQ behavior is unchanged.

**Outcome:** Prompts are editable without changing script code; ready for multi-project reuse.

---

## 5. Later (after tested here)

- **Phase 4 (optional):** Multi-repo support — **Done.** `runner/run-multirepo.ps1` reads `repos.yaml` and runs the pipeline per repo with `-ProjectRootOverride` and `-ConfigPath`. Script supports `-ProjectRootOverride`. Schema: [config/repos-schema.md](../config/repos-schema.md); example: [config/example/repos-example.yaml](../config/example/repos-example.yaml).
- **Phase 5:** Document adoption and breakout — **Done.** See [docs/adoption-and-breakout.md](adoption-and-breakout.md): how to copy or reference the template, use with MCP_DOCKER/TappsMCP, customize, and move `auto-fix-pipeline/` to its own repo.

---

## Summary

| Order | Epic | Focus | Delivers |
|-------|------|--------|----------|
| 1 | **Epic 1** | Config schema + example | Config is the API; HomeIQ behavior expressible as config |
| 2 | **Epic 2** | Runner that delegates | Config-driven entrypoint; existing script unchanged |
| 3 | **Epic 3** | Script reads config | Optional `-ConfigPath`; backward compatible |
| 4 | **Epic 4** | Prompt templates | Prompts externalized; ready for reuse |

**Recommended next step:** Define and execute **Epic 1** (config schema and HomeIQ default) so Epic 2 and 3 have a concrete config to use.
