# Auto-Fix Pipeline and MCP Architecture

**Last Updated:** March 2026  
**Status:** Current  
**Purpose:** Architecture for the config-driven auto-fix pipeline and its integration with the Docker MCP Toolkit (MCP_DOCKER), including TappsMCP (quality/experts) and docs-mcp (documentation). This document is the single reference for pipeline design, MCP tooling, and generalization across projects/repos.

---

## 1. Overview

The **auto-fix pipeline** finds bugs, applies fixes, validates with quality tools, and opens pull requests. It is designed to run in a single repo (e.g. HomeIQ) or, in a generalized form, across multiple repos with a shared config and optional meta-repository. All MCP-based quality and documentation capabilities in this project are provided through **MCP_DOCKER** (Docker MCP Toolkit): a single gateway that exposes **TappsMCP** (code quality, security, experts, doc lookup) and **docs-mcp** (documentation retrieval and search). No standalone MCP server processes are required; one gateway process routes to the appropriate tools.

### 1.1 Design principles

- **Config-driven:** Pipeline behavior (paths, scan units, prompts, tool allowlists) is driven by configuration so the same runner can operate across projects.
- **MCP behind one gateway:** TappsMCP and docs-mcp are used via MCP_DOCKER; clients connect once to the gateway and get access to all tools.
- **Docs-aware pipeline:** Agents use **docs-mcp** to fetch project documentation (architecture, APIs, workflows) and **TappsMCP** (e.g. `tapps_lookup_docs`) for library documentation during scan, fix, and refactor phases.
- **Generalization-ready:** The current HomeIQ implementation is a concrete instance of a target design that supports single-repo and multi-repo modes with optional meta-repo context.

---

## 2. MCP Architecture

### 2.1 Gateway and servers

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                  MCP_DOCKER (Gateway)                    │
                    │              docker mcp gateway run                      │
                    │  ┌─────────────────────────┬─────────────────────────┐  │
                    │  │      TappsMCP           │       docs-mcp           │  │
                    │  │  • tapps_session_start  │  • Documentation        │  │
                    │  │  • tapps_quick_check    │    retrieval / search   │  │
                    │  │  • tapps_validate_*     │  • Project docs,        │  │
                    │  │  • tapps_consult_expert │    architecture,       │  │
                    │  │  • tapps_lookup_docs    │    API references       │  │
                    │  │  • tapps_security_scan  │                         │  │
                    │  │  • tapps_* (26 tools)   │                         │  │
                    │  └─────────────────────────┴─────────────────────────┘  │
                    └─────────────────────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
            ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
            │ Cursor / IDE  │         │ Claude CLI    │         │ Auto-bugfix    │
            │ .cursor/      │         │ (headless)    │         │ scripts       │
            │ mcp.json      │         │ .mcp.json    │         │ .mcp.json     │
            └───────────────┘         └───────────────┘         └───────────────┘
```

- **MCP_DOCKER:** Single MCP gateway process (Docker MCP Toolkit). Clients point to this gateway; they do not configure TappsMCP or docs-mcp as separate servers.
- **TappsMCP:** Quality scoring, security scanning, quality gates, dead-code detection, dependency scanning, **domain experts** (RAG-backed), and **documentation lookup** (Context7-backed when configured). Tools are exposed with the prefix `mcp__MCP_DOCKER__tapps_*` (e.g. `mcp__MCP_DOCKER__tapps_quick_check`).
- **docs-mcp:** Part of the same Docker MCP Toolkit. Provides documentation retrieval and search so agents can pull in project docs (e.g. architecture, API reference, deployment), pipeline docs (auto-bugfix workflow, scan format), or other curated content during pipeline phases. Use docs-mcp when the agent needs structured access to project or pipeline documentation; use TappsMCP’s `tapps_lookup_docs` for external library documentation.

### 2.2 Client configuration

| Context | Config file | Purpose |
|--------|-------------|---------|
| **Cursor / IDE** | `.cursor/mcp.json` | Single entry: `MCP_DOCKER` with `command: "docker"`, `args: ["mcp", "gateway", "run"]`. Enables TappsMCP and docs-mcp in the IDE. |
| **Headless / auto-bugfix** | `.mcp.json` (project root) | Same `MCP_DOCKER` entry so Claude CLI can call TappsMCP and docs-mcp during scan, fix, refactor, test, and feedback. |

Both configs must expose the same gateway; tool names are always prefixed by the server name (e.g. `mcp__MCP_DOCKER__...`). No separate `tapps-mcp` or `docs-mcp` server blocks are required. See [.cursor/MCP_SETUP_INSTRUCTIONS.md](../../.cursor/MCP_SETUP_INSTRUCTIONS.md).

### 2.3 When to use which tooling

| Need | Use |
|------|-----|
| Session start, project profile, quality gates, security scan, experts, validate changed files | **TappsMCP** (`mcp__MCP_DOCKER__tapps_*`) |
| Up-to-date **library** docs (FastAPI, pytest, InfluxDB, etc.) before writing code | **TappsMCP** `tapps_lookup_docs` (Context7-backed) |
| **Project** docs: architecture, API reference, deployment, auto-bugfix workflow, scan format | **docs-mcp** (MCP_DOCKER) |
| Checklist, feedback, impact analysis, dead code, dependency graph | **TappsMCP** |

During the auto-fix pipeline, prompts can instruct the agent to use **docs-mcp** to load this architecture doc, [auto-bugfix-scan-format](../../workflows/auto-bugfix-scan-format.md), [auto-bugfix-subagents](../../workflows/auto-bugfix-subagents.md), and [docs/architecture](.) as needed so behavior stays aligned with project and pipeline design.

---

## 3. Auto-Fix Pipeline Architecture

### 3.1 Phase flow

```
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │ 1. Branch   │────▶│ 2. Scan     │────▶│ 3. Fix      │────▶│ 4. Commit   │────▶│ 5. Feedback │
  │             │     │ (TappsMCP   │     │ (TappsMCP   │     │ & PR        │     │ (TappsMCP   │
  │             │     │  + docs-mcp │     │  + docs-mcp │     │             │     │  feedback)  │
  │             │     │  optional)  │     │  optional)  │     │             │     │             │
  └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                              │                   │
                              │    ┌───────────────┴───────────────┐
                              │    │ Chain (optional)              │
                              └────│ 4a. Refactor (TappsMCP)      │
                                   │ 4b. Test (TappsMCP quick_check)│
                                   └───────────────────────────────┘
```

- **Branch:** Create feature branch (or use worktree); ensure clean tree unless `-Worktree`.
- **Scan:** Claude finds N bugs using TappsMCP (`tapps_security_scan`, `tapps_quick_check` on sample files), code reading (Read/Grep/Glob), and optional **docs-mcp** for pipeline/architecture context. Output must be a JSON array between `<<<BUGS>>>` and `<<<END_BUGS>>>`. Retry once without MCP if parse fails.
- **Fix:** Claude fixes each bug; validates with TappsMCP (`tapps_quick_check`, `tapps_validate_changed`, `tapps_consult_expert` where needed). **docs-mcp** can be used to pull architecture or API docs when fixing cross-service or API-related bugs.
- **Commit & PR:** Stage, commit, push, create PR via `gh`.
- **Feedback:** Claude writes TappsMCP feedback to `docs/tapps-feedback/` and calls `tapps_feedback`; commit and push.
- **Chain (optional):** Refactor phase (impact analysis, dead code, validate_changed); Test phase (pytest generation, quick_check on test files).

### 3.2 Scan manifest and rotation

The pipeline can target the whole repo or **scan units** defined in a manifest (e.g. `docs/scan-manifest.json`). Each unit has:

- `id`, `name`, `path` (e.g. `domains/core-platform/`)
- `priority_weight`, `scan_hint` (for prompts)
- `last_scanned`, `total_bugs_found`, `false_positives` (for rotation)

A **selector** (built-in or configurable) picks the next unit by score (e.g. priority × days since scan × bug yield, with false-positive penalty). This spreads coverage across the codebase and avoids rescanning the same area every run. **docs-mcp** can be used to load scan-manifest semantics or pipeline docs so the agent understands how units and hints work.

### 3.3 Config model (target generalization)

The implementation plan defines a single config file (e.g. `.auto-fix/config.yaml`) that drives:

- **Project:** name, languages, root.
- **Runner:** CLI, model, max cost, budget allocation (scan / fix / chain / feedback).
- **Scan:** manifest path, selector, output format (markers + schema), retry attempts, retry fallback tools.
- **Fix:** chain phases, validation required.
- **MCP:** config path, **tapps_mcp_server** (e.g. `MCP_DOCKER` or `tapps-mcp` for standalone), scan_tools, fix_tools, expert_domains, docs_lookup. When using MCP_DOCKER, tool names use the `mcp__MCP_DOCKER__*` prefix; docs-mcp is available through the same gateway.
- **Paths:** dashboard state, feedback dir, history file, implementation dir, scan-failure prefix.
- **Prompts:** optional overrides (find, retry, fix, refactor, test, feedback).

Current HomeIQ behavior is equivalent to this model with defaults and a fixed `TappsMcpServer = "MCP_DOCKER"` in the script. See [implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md](../../implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md).

### 3.4 Streaming and dashboard

The runner uses **streaming** (e.g. `claude --print --output-format stream-json`) so that:

- Tool calls (including `mcp__MCP_DOCKER__tapps_*` and docs-mcp) are visible in real time.
- Token usage and cost can be tracked per phase.
- A live dashboard (e.g. `scripts/dashboard.html` + `.dashboard-state.json`) shows step, status, bugs found/fixed, and current tool.

Stream parsing is implemented in `scripts/auto-bugfix-stream.ps1`; it does not depend on which MCP server name is used as long as tool names match the configured prefix.

---

## 4. docs-mcp Integration

### 4.1 Role in the pipeline

**docs-mcp** (via MCP_DOCKER) is used to give the agent structured access to project and pipeline documentation:

- **Architecture:** This document, [service-groups](service-groups.md), [event-flow](event-flow-architecture.md), and related architecture docs so fixes respect system boundaries and data flow.
- **Pipeline:** [Auto-bugfix scan format](../../workflows/auto-bugfix-scan-format.md), [auto-bugfix subagents](../../workflows/auto-bugfix-subagents.md), and MCP setup so the agent follows output format and tool usage.
- **APIs and deployment:** [API reference](../api/API_REFERENCE.md), [deployment quick reference](../deployment/DEPLOYMENT_QUICK_REFERENCE.md) when fixes touch endpoints or deployment.

Prompts for scan, fix, and refactor can instruct the agent to “use docs-mcp to load relevant project docs (architecture, pipeline, API) when needed.” No change to the gateway config is required; docs-mcp is already available under MCP_DOCKER.

### 4.2 Relationship to TappsMCP and Context7

- **TappsMCP `tapps_lookup_docs`:** Best for **external library** documentation (e.g. FastAPI, pytest, aiohttp). Use before writing code that depends on those libraries.
- **docs-mcp:** Best for **this project’s** documentation (architecture, workflows, API reference, deployment). Use when reasoning about system design, pipeline behavior, or API contracts.
- **Context7:** Optional separate MCP server for direct doc lookups; TappsMCP can also use Context7 internally for `tapps_lookup_docs`. docs-mcp and Context7 are complementary (project vs library docs).

---

## 5. Multi-Repo and Meta-Repository (Target)

The generalization plan supports:

- **Single-repo mode:** One workspace root, one config, one manifest (current HomeIQ).
- **Multi-repo mode:** A meta-repo as workspace root with `repos.yaml` (or equivalent); the runner runs the same pipeline in each repo or a subset, with shared conventions and optional scan units defined per repo.
- **Meta-repo content:** AGENTS.md, repos.yaml, structure/, conventions/, workflows/, and optional `.auto-fix/` config so agents (and docs-mcp) have a single place for cross-repo orientation and pipeline docs.

In all modes, MCP_DOCKER remains the single gateway for TappsMCP and docs-mcp; only the project root and config paths change.

---

## 6. References

| Document | Description |
|----------|-------------|
| [.cursor/MCP_SETUP_INSTRUCTIONS.md](../../.cursor/MCP_SETUP_INSTRUCTIONS.md) | TappsMCP and docs-mcp via MCP_DOCKER; IDE and headless config. |
| [AGENTS.md](../../AGENTS.md) | TappsMCP tool list and MCP_DOCKER note. |
| [docs/TAPPS_TOOL_PRIORITY.md](../TAPPS_TOOL_PRIORITY.md) | Tool order and when to use TappsMCP. |
| [implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md](../../implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md) | Config-driven design, meta-repo, and rollout phases. |
| [workflows/auto-bugfix-scan-format.md](../workflows/auto-bugfix-scan-format.md) | Required scan output format (`<<<BUGS>>>` / `<<<END_BUGS>>>`). |
| [workflows/auto-bugfix-subagents.md](../workflows/auto-bugfix-subagents.md) | Subagent (bug-scanner) and MCP requirements. |
| [scripts/auto-bugfix.ps1](../../scripts/auto-bugfix.ps1) | Entrypoint; `-TappsMcpServer` default `MCP_DOCKER`. |

---

*This architecture document is maintained as the single reference for the auto-fix pipeline and MCP (MCP_DOCKER, TappsMCP, docs-mcp) design. Use **docs-mcp** to retrieve it during pipeline runs when agents need the full design context.*
