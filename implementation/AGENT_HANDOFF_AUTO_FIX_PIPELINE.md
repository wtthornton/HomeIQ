# Handoff: Auto-Fix Pipeline (Isolated Project)

**Date:** March 2026  
**Purpose:** Prompt to give a **new agent** so they can continue work on the auto-fix pipeline isolated project without losing context.

---

## Copy-paste prompt for the new agent

```
You are continuing work on the **auto-fix pipeline isolated project** inside HomeIQ. Read this handoff first, then follow the task I give you.

## Context

- **Epic 0 (structure setup) is complete and executed.** A dedicated directory `auto-fix-pipeline/` exists at repo root. It is intended to hold the config-driven, generalized auto-fix pipeline and MCP design. One day this folder will be split into its own repo; for now we develop and test here.
- **Epic 52 (config cleanup) complete.** Config is required. Preferred entry: `.\auto-fix-pipeline\runner\run.ps1 -Bugs 3`. Script `scripts/auto-bugfix.ps1` defaults to `homeiq-default.yaml` or `$env:AUTO_FIX_CONFIG`. Do not move or delete `scripts/auto-bugfix.ps1` or `scripts/auto-bugfix-stream.ps1`.
- **MCP:** TappsMCP and docs-mcp are provided by **MCP_DOCKER** (Docker MCP Toolkit). Tool prefix is `mcp__MCP_DOCKER__` (e.g. `mcp__MCP_DOCKER__tapps_quick_check`). Config lives at `.cursor/mcp.json` (IDE) and `.mcp.json` at project root (headless). See `.cursor/MCP_SETUP_INSTRUCTIONS.md`.

## Where things live

- **Isolated project:** `auto-fix-pipeline/`  
  - `README.md` — purpose, links, "next: Epic 1"  
  - `docs/` — NEXT_STEPS.md (recommended Epics 1–4), architecture/workflows/reference (placeholders)  
  - `config/` — schema/ and example/ (empty; Epic 1 will add config schema and HomeIQ example)  
  - `runner/` — placeholder only; Epic 2 will add runner that delegates to existing script  
  - `stories/` — EPIC-00-INDEX.md (Epic 0 done); Epic 1+ will be defined in parent `stories/` or here  
- **Epic 0 (done):** `stories/epic-50-auto-fix-isolated-project-structure.md`  
- **Architecture:** `docs/architecture/auto-fix-mcp-architecture.md` (MCP_DOCKER, TappsMCP, docs-mcp, pipeline phases, config model)  
- **Generalization plan:** `implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md` (phased rollout, config YAML shape)  
- **Recommended next steps:** `auto-fix-pipeline/docs/NEXT_STEPS.md` (Epic 1: config schema; Epic 2: runner; Epic 3: script reads config; Epic 4: prompts)

## Recommended next work

**Epic 1 (recommended first):** Config schema and HomeIQ default. Add config schema under `auto-fix-pipeline/config/schema/` and an example config under `auto-fix-pipeline/config/example/` that matches current HomeIQ behavior. Do **not** change `scripts/auto-bugfix.ps1` in Epic 1. Schema should cover: project (name, languages, root), runner (cli, model, max_cost, budget_allocation), scan (manifest_path, selector, output_format, retry_attempts), fix (chain_phases, validation_required), mcp (config_path, tapps_mcp_server, scan_tools, fix_tools, expert_domains, docs_lookup), paths (dashboard_state, feedback_dir, history_file, impl_dir). Reference the YAML example in `implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md` section 4.1.

## Rules

1. Do not move or delete `scripts/auto-bugfix.ps1` or `scripts/auto-bugfix-stream.ps1`.  
2. Do not change existing HomeIQ behavior unless the handoff task explicitly asks for it (and then keep backward compatibility).  
3. New pipeline code and config belong under `auto-fix-pipeline/` or, when integrating, as optional parameters to existing scripts.  
4. Follow project structure: implementation notes and handoffs in `implementation/`; reference docs in `docs/`; epics/stories in `stories/`.  
5. TappsMCP is via MCP_DOCKER; use tool prefix `mcp__MCP_DOCKER__` in any new config or docs that reference tool names.

Proceed with the task I give you.
```

---

## Short version (if the agent has limited context)

```
Continue the auto-fix pipeline isolated project. Epic 0 is done (structure under `auto-fix-pipeline/`). Do not change `scripts/auto-bugfix.ps1` behavior; do not break HomeIQ. Next: Epic 1 — add config schema in `auto-fix-pipeline/config/schema/` and HomeIQ example in `auto-fix-pipeline/config/example/`. See `auto-fix-pipeline/docs/NEXT_STEPS.md` and `implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md` section 4.1 for config shape. TappsMCP/docs-mcp are via MCP_DOCKER (prefix `mcp__MCP_DOCKER__`). [Then add your specific task.]
```

---

## File reference table

| Need | Path |
|------|------|
| Next steps (Epics 1–4) | `auto-fix-pipeline/docs/NEXT_STEPS.md` |
| Epic 0 (structure) | `stories/epic-50-auto-fix-isolated-project-structure.md` |
| Architecture (MCP, pipeline) | `docs/architecture/auto-fix-mcp-architecture.md` |
| Config example (YAML §4.1) | `implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md` §4.1 |
| MCP setup | `.cursor/MCP_SETUP_INSTRUCTIONS.md` |
| Current script | `scripts/auto-bugfix.ps1` |
| Scan format | `docs/workflows/auto-bugfix-scan-format.md` |
| Open epics index | `stories/OPEN-EPICS-INDEX.md` (Epic 50 = complete) |

---

## How to use it

- **New agent, full context:** Open `implementation/AGENT_HANDOFF_AUTO_FIX_PIPELINE.md`, copy the full **Copy-paste prompt for the new agent** block (the entire fenced block under that heading), paste it into the new chat, then add your instruction (e.g. “Create Epic 1 and its stories” or “Implement Epic 1”).
- **New agent, short:** Copy the **Short version** paragraph and append your task.
