# High-Level Plan: Generalize Auto-Bugfix for Cross-Project / Multi-Repo Use

**Created:** 2026-03-11  
**Status:** Plan  
**Purpose:** Leverage 2026 research, Context7 MCP, TappsMCP, and expert patterns to design a portable “auto-fix” pipeline usable across projects and/or repositories.

---

## 1. Executive Summary

The current auto-bugfix pipeline (`scripts/auto-bugfix.ps1` + stream + scan manifest) is effective but tightly coupled to HomeIQ: project root, scan units, prompts, and paths are hardcoded or HomeIQ-specific. This plan outlines how to generalize it into a **config-driven, reusable pipeline** that can run in any repo or be orchestrated across multiple repos, with optional **meta-repository** context and consistent use of **MCP** (TappsMCP, Context7) and **expert consultation** for quality and docs.

---

## 2. Research Synthesis (2026)

### 2.1 Cross-Repo and Pipeline Reuse

- **Cross-repo coordination:** ~68% of cross-repository deployments fail without explicit coordination; convention fragmentation and session amnesia are major costs (Augment Code, 2026).
- **Meta-repository pattern:** A dedicated “agents” repo as an AI knowledge base (AGENTS.md, repos.yaml, structure/, conventions/, workflows/) gives agents persistent orientation and eliminates re-exploration each session (Seylox/Anyline, 2026).
- **Config repo pattern:** Separating pipeline/agent configuration from application code supports independent updates, access control, and reuse across many services (Argo CD / GitOps, 2026).
- **Pipeline reuse maturity:** Progression from copy-paste → shared templates → managed inheritance so one change propagates across many projects (Harness, 2026).
- **MCP (Model Context Protocol):** Standardized tool interface; servers are reusable across Cursor, VS Code, GitHub Copilot. In HomeIQ, **TappsMCP** is provided by **MCP_DOCKER** (Docker MCP Toolkit), not a standalone server; tools appear as `mcp__MCP_DOCKER__tapps_*`. Context7 can be separate or used by TappsMCP for doc lookup (MCP spec 2025–11, VS Code/Copilot docs).

### 2.2 TappsMCP and Context7 in the Generalized Design

- **TappsMCP:** Use for quality gates (`tapps_quick_check`, `tapps_validate_changed`), security (`tapps_security_scan`), domain decisions (`tapps_consult_expert`), and doc-backed research (`tapps_lookup_docs` → Context7). In a generalized pipeline, **tool allowlists and presets should be configurable** so projects without TappsMCP can omit them or substitute other MCP tools.
- **Context7:** Use for up-to-date library docs before writing code; reduces hallucinated APIs. In a generalized pipeline, **docs lookup** can be optional and keyed by project tech stack (from config or project-profile).
- **Experts:** `tapps_consult_expert` (and equivalent patterns) for security, testing, API design, database, and architecture. The generalized pipeline should **invoke expert consultation when the fix phase touches sensitive domains** (configurable by file path patterns or labels).

---

## 3. Current Coupling Points (What to Generalize)

| Area | Current state | Generalization direction |
|------|----------------|---------------------------|
| **Project root** | Derived from script path (e.g. `Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)`) | Config or env: `project_root` / `WORKSPACE_ROOT`; support single-repo and multi-repo workspaces. |
| **Scan manifest** | `docs/scan-manifest.json` with HomeIQ-specific `units` (id, path, name, priority_weight, scan_hint, etc.) | **Scan manifest schema** as part of shared config; any project can define “scan units” (paths + hints + priority). |
| **Prompts** | Inline in PowerShell (find, retry, fix, refactor, test, feedback) with “HomeIQ”, “Python”, TappsMCP tool names | **Prompt templates** in config or separate files; placeholders for `{{project_name}}`, `{{languages}}`, `{{scope_hint}}`, `{{allowed_tools}}`, `{{bug_count}}`. |
| **MCP config** | `.mcp.json` at project root; TappsMCP via MCP_DOCKER (Docker MCP Toolkit); tool names in script | Config section: `mcp_config_path`, `tapps_mcp_server` (e.g. `MCP_DOCKER` or `tapps-mcp`), `scan_tools`, `fix_tools`, `optional_tools`; allow empty for no-MCP runs. |
| **Output format** | `<<<BUGS>>>` / `<<<END_BUGS>>>` + JSON schema (file, line, description, severity) | Keep as default; make **markers and schema** configurable (e.g. for non-Python or different taxonomies). |
| **Paths** | Dashboard, feedback, BUG_HISTORY, implementation/ saves | All path keys in config (e.g. `paths.dashboard_state`, `paths.feedback_dir`, `paths.history_file`, `paths.impl_dir`). |
| **Rotate logic** | Inline Python in PowerShell; score = f(priority_weight, days_since_scan, bugs_found, false_positives) | **Pluggable** “scan unit selector”: config points to script or CLI; default implementation stays same algorithm, other projects can override. |
| **CLI** | `claude`, `git`, `gh` | Remain as requirements; optionally allow **runner** override (e.g. different AI CLI or wrapper). |

---

## 4. Target Architecture

### 4.1 Single Config File (Pipeline “API”)

One primary config per project (or per meta-repo) that the runner reads. Suggested location: `.auto-fix/config.yaml` (or `auto-bugfix.config.yaml` at repo root).

```yaml
# Minimal example — all keys optional with sensible defaults
version: 1

project:
  name: "HomeIQ"
  languages: ["python"]   # for prompts and tool hints
  root: "."                # or env: WORKSPACE_ROOT

runner:
  cli: "claude"           # or path to wrapper
  model: "claude-sonnet-4-6"
  max_cost: 5.0
  budget_allocation:      # scan_ratio, fix_ratio, chain_ratio, feedback_ratio
    scan: 0.30
    fix: 0.40
    chain: 0.15
    feedback: 0.15

scan:
  manifest_path: "docs/scan-manifest.json"
  selector: "builtin"     # or path to script / "none" for full-repo
  output_format:
    markers: ["<<<BUGS>>>", "<<<END_BUGS>>>"]
    schema: { file: string, line: int, description: string, severity: string }
  retry_attempts: 2
  retry_fallback_tools: ["Read", "Grep", "Glob"]   # no MCP on retry

fix:
  chain_phases: ["fix", "refactor", "test"]   # optional phases
  validation_required: true

mcp:
  config_path: ".mcp.json"
  tapps_mcp_server: "MCP_DOCKER"   # or "tapps-mcp" if standalone
  scan_tools: "Read,Grep,Glob,mcp__MCP_DOCKER__tapps_security_scan,mcp__MCP_DOCKER__tapps_quick_check,..."
  fix_tools: "Read,Edit,Grep,Glob,mcp__MCP_DOCKER__tapps_validate_changed,..."
  expert_domains: ["security", "testing-strategies", "api-design-integration", "database-data-management"]
  docs_lookup: true        # use Context7 / tapps_lookup_docs when available

paths:
  dashboard_state: "scripts/.dashboard-state.json"
  dashboard_html: "scripts/dashboard.html"
  feedback_dir: "docs/tapps-feedback"
  history_file: "docs/BUG_HISTORY.json"
  impl_dir: "implementation"
  scan_failure_prefix: "auto-bugfix-scan-failure"

prompts:                   # optional overrides; else use built-in templates
  find: "docs/workflows/auto-bugfix-prompts/find.md"
  retry: "docs/workflows/auto-bugfix-prompts/retry.md"
  fix: "docs/workflows/auto-bugfix-prompts/fix.md"
  # refactor, test, feedback similarly
```

- **TappsMCP / Context7:** Controlled by `mcp.scan_tools`, `mcp.fix_tools`, `mcp.docs_lookup`, and prompt templates that reference “call expert when security/API/DB” and “look up docs before using library X”. If MCP config is missing or disabled, runner skips those tools.

### 4.2 Meta-Repository Option (Multi-Repo)

For **multiple repositories**, adopt the 2026 meta-repo pattern:

- **Agents meta-repo** (or “pipeline config repo”) contains:
  - **AGENTS.md** — entry point for agents (verify/update/suggest; link to workflows and conventions).
  - **repos.yaml** (or equivalent): list of repos with `path`, `languages`, `build_commands`, `purpose`.
  - **structure/** — dependency-graph, repo-purposes.
  - **conventions/** — commits, branching, release.
  - **workflows/** — cross-repo change order, release process, **and** the generalized auto-fix workflow (e.g. “run auto-fix per repo from this config”).
  - **.auto-fix/** or **auto-fix/** — shared or per-repo `config.yaml`; scan manifest can list “units” that are **repos** or **subpaths** of repos.

Runner can then:

- Run in **single-repo mode**: one workspace root, one config.
- Run in **multi-repo mode**: meta-repo is workspace root; config points to `repos.yaml`; runner iterates over repos (or a subset) and runs the same pipeline in each, with context from meta-repo (conventions, order).

Expert and docs usage stays the same: TappsMCP and Context7 are configured at the environment/IDE level; the pipeline only passes the right **allowed tools** and **prompt hints** from config.

### 4.3 Shared “Runner” and Template Repo

- **Runner:** A thin, generic entrypoint (e.g. `auto-fix.ps1` or `auto-fix.sh`) that:
  1. Loads `.auto-fix/config.yaml` (or env override).
  2. Resolves project root, paths, and MCP settings.
  3. Loads prompt templates (built-in or from config).
  4. Runs the same logical steps: branch → scan → fix → [chain] → commit → PR → feedback → bookkeeping.

- **Template repo** (e.g. `auto-fix-pipeline` or under a broader “agent-templates” org):
  - Default `config.yaml` and schema.
  - Default scan-manifest schema and built-in selector script.
  - Default prompt templates (parameterized for project name, languages, tools).
  - Optional dashboard and stream parser as generic assets.
  - Docs: how to add TappsMCP/Context7, how to use experts, how to customize prompts.

Projects that adopt the pipeline either:

- **Copy** the runner + default config into their repo and customize, or
- **Reference** the template repo (submodule or package) and override only what’s needed.

---

## 5. Integration with Context7 and TappsMCP

- **Context7 MCP:** Used for “look up docs before writing code” in fix/refactor/test phases. In the generalized design:
  - Config: `mcp.docs_lookup: true` and (optional) `mcp.docs_libraries: [ "fastapi", "pytest", "influxdb" ]` from project profile.
  - Prompts: “Before using an external library, call `tapps_lookup_docs` (or Context7 doc lookup) for that library.”
  - Runner does not implement doc lookup; it only enables the right tools and prompt text.

- **TappsMCP experts:** Used for security, testing, API, DB, and architecture decisions during fix/refactor.
  - Config: `mcp.expert_domains` and “call expert when touching security/API/DB” in fix/refactor prompts.
  - Runner: include expert tools in `fix_tools` / `chain_tools` when TappsMCP is configured.

- **Quality gates:** `tapps_quick_check`, `tapps_validate_changed`, `tapps_quality_gate` remain in fix/refactor prompts; config can disable validation or reduce to “run tests only” for repos without TappsMCP.

---

## 6. Phased Rollout

| Phase | Scope | Deliverables |
|-------|--------|---------------|
| **1. Extract config** | Single repo (HomeIQ) | Add `.auto-fix/config.yaml` (or equivalent); refactor `auto-bugfix.ps1` to read config for paths, manifest, budgets, model; keep behavior unchanged. |
| **2. Externalize prompts** | Single repo | Move find/retry/fix/refactor/test/feedback prompts to template files with placeholders; runner loads and substitutes from config. |
| **3. Generic runner** | Template repo | New repo or folder: generic runner script + default config schema + default prompts + minimal dashboard/stream logic; document TappsMCP and Context7 usage. |
| **4. Multi-repo support** | Optional | Runner can accept “meta-repo root” and `repos.yaml`; loop over repos and run pipeline per repo; optional scan manifest where “units” are repos. |
| **5. Shared template adoption** | Community/org | Document how to add the pipeline to a new project (copy or reference template); document how to use with TappsMCP and Context7 and experts. |

---

## 7. Success Criteria

- **Portability:** One config file (+ optional prompt overrides and scan manifest) is enough to run the pipeline in a new repo.
- **MCP-agnostic:** Pipeline runs with or without TappsMCP/Context7; config turns expert/docs tools on or off.
- **Multi-repo:** Same runner can run in single-repo mode or, with a meta-repo, across multiple repos with shared conventions.
- **Maintainability:** Prompt and scan-selector changes live in config or template repo, not inside runner code.
- **Expert/docs usage:** When TappsMCP and Context7 are available, the pipeline consistently uses experts for domain decisions and doc lookup for libraries, as in current HomeIQ practice.

---

## 8. References

- **Current pipeline:** `scripts/auto-bugfix.ps1`, `scripts/auto-bugfix-stream.ps1`, `docs/workflows/auto-bugfix-scan-format.md`, `docs/workflows/auto-bugfix-subagents.md`
- **Scan manifest:** `docs/scan-manifest.json`
- **TappsMCP / experts / docs:** `AGENTS.md`, `docs/TAPPS_TOOL_PRIORITY.md`, `.cursor/skills/tapps-research/SKILL.md`, `.cursor/MCP_SETUP_INSTRUCTIONS.md` (TappsMCP via MCP_DOCKER / Docker MCP Toolkit)
- **Context7:** `scripts/update-context7-versions.py`, `scripts/refresh-context7-docs.py`, `docs/kb/` (context7-cache)
- **2026 research:** Meta-repo pattern (Seylox), cross-repo AI workflows (Augment Code), config repo pattern (Argo CD / GitOps), pipeline reuse (Harness), MCP specification and VS Code/Copilot integration

---

*This plan is a high-level design. Implementation details (exact YAML schema, prompt variable names, and runner CLI) should be refined in follow-up stories or epics.*
